"""Vigencia documental: las reglas R1–R5 proponen y el registro certificado decide."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

from .modelos import DocumentoExtraido, Vigencia
from .texto import RESOLUCION_TEXTO


class ConflictoVigencia(Exception):
    """El registro certificado contradice la evidencia del corpus."""


@dataclass
class Propuesta:
    estado: str
    regla: str
    evidencia: list[str]
    reemplazado_por: str | None = None
    vigente_hasta: str | None = None


def cargar_contrato(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def clase_de(doc: DocumentoExtraido, contrato: dict) -> str:
    try:
        return contrato["clasificacion"][doc.tipo]
    except KeyError as e:
        raise ValueError(f"{doc.clave}: el tipo «{doc.tipo}» no está en el contrato del corpus") from e


def _ver(v: str) -> int:
    return int(v) if v.isdigit() else 0


def proponer(docs: Iterable[DocumentoExtraido], contrato: dict) -> dict[str, Propuesta]:
    docs = list(docs)
    prop: dict[str, Propuesta] = {}
    por_codigo: dict[str, list[DocumentoExtraido]] = {}
    for d in docs:
        por_codigo.setdefault(d.codigo, []).append(d)
        clase = clase_de(d, contrato)
        if clase in ("acta", "comunicacion_proveedor"):
            prop[d.clave] = Propuesta("no_normativo", "R4", [f"{d.codigo}: clase {clase}, sin vigencia normativa"])
        elif clase == "manual":
            prop[d.clave] = Propuesta("pendiente_certificacion", "R5",
                                      [f"{d.codigo} v{d.version}: los manuales requieren certificación del área emisora"])
        else:
            prop[d.clave] = Propuesta("vigente", "sin evidencia de derogación", [])

    # R1: sucesión de versiones del mismo código
    for codigo, lista in por_codigo.items():
        lista.sort(key=lambda d: _ver(d.version))
        for anterior, siguiente in zip(lista, lista[1:]):
            prop[anterior.clave] = Propuesta(
                "derogado", "R1", [f"{siguiente.codigo} v{siguiente.version} (emitida {siguiente.fecha_emision}) sucede a la v{anterior.version}"],
                reemplazado_por=f"{siguiente.codigo} v{siguiente.version}", vigente_hasta=siguiente.fecha_emision)

    # R2: «Reemplaza a» con un código distinto
    for d in docs:
        m = re.match(r"^([A-Z]+-[A-Z]+-[A-Z0-9]+)\s+v(\d+)", d.reemplaza_a)
        if m and m.group(1) != d.codigo:
            clave = f"{m.group(1)}@v{m.group(2)}"
            if clave in prop:
                prop[clave] = Propuesta("derogado", "R2", [f"{d.codigo} v{d.version}, «Reemplaza a»: {d.reemplaza_a}"],
                                        reemplazado_por=f"{d.codigo} v{d.version}", vigente_hasta=d.fecha_emision)

    # R3: derogatoria expresa en el articulado de una resolución
    resoluciones = {d.codigo: d for d in docs if clase_de(d, contrato) == "normativa"}
    for d in resoluciones.values():
        for s in d.secciones:
            if "deroga" not in s.texto.lower():
                continue
            for num, anio in RESOLUCION_TEXTO.findall(s.texto[s.texto.lower().index("deroga"):]):
                for cod, objetivo in resoluciones.items():
                    if cod != d.codigo and cod.endswith(f"-{num}-{anio}"):
                        prop[objetivo.clave] = Propuesta(
                            "derogado", "R3", [f"{d.codigo} §{s.id}: «{s.texto.strip()}»"],
                            reemplazado_por=d.codigo, vigente_hasta=d.fecha_emision)
    return prop


def cargar_registro(path: Path) -> dict[str, Vigencia]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    reg = {}
    for e in data["documentos"]:
        v = Vigencia(codigo=e["codigo"], version=str(e["version"]), estado=e["estado"],
                     vigente_desde=str(e["vigente_desde"]), vigente_hasta=e.get("vigente_hasta") and str(e["vigente_hasta"]),
                     regla=e["regla"], evidencia=list(e.get("evidencia", [])), certificado_por=e["certificado_por"],
                     fecha_certificacion=e.get("fecha_certificacion") and str(e["fecha_certificacion"]),
                     reemplazado_por=e.get("reemplazado_por"), advertencia=e.get("advertencia"),
                     modo_certificacion=e.get("modo_certificacion", "simulada-prototipo"))
        reg[f"{v.codigo}@v{v.version}"] = v
    return reg


def conciliar(docs: Iterable[DocumentoExtraido], contrato: dict, registro: dict[str, Vigencia]) -> tuple[dict[str, Vigencia], list[str]]:
    """Devuelve la vigencia final de cada documento y los avisos de gobierno.

    - Documento sin entrada en el registro: estado por defecto de su clase (nunca «vigente»), con aviso.
    - Registro «vigente» contra evidencia de derogación: ConflictoVigencia (la ingesta se detiene).
    - Registro «derogado» sin evidencia en el corpus: se respeta el registro (puede saber más que el corpus), con aviso.
    """
    docs = list(docs)
    propuestas = proponer(docs, contrato)
    final: dict[str, Vigencia] = {}
    avisos: list[str] = []
    for d in docs:
        p = propuestas[d.clave]
        r = registro.get(d.clave)
        if r is None:
            estado = contrato["clases"][clase_de(d, contrato)]["estado_sin_certificacion"]
            if p.estado == "derogado":
                estado = "derogado"
            final[d.clave] = Vigencia(d.codigo, d.version, estado, d.fecha_emision, p.vigente_hasta, p.regla,
                                      p.evidencia, "sin certificar", None, p.reemplazado_por,
                                      advertencia="Documento sin entrada en el registro de vigencia.")
            avisos.append(f"{d.clave}: no está en el registro de vigencia; se indexa como «{estado}».")
            continue
        if r.estado in ("vigente", "pendiente_certificacion") and p.estado == "derogado":
            raise ConflictoVigencia(
                f"{d.clave}: el registro lo declara «{r.estado}» pero la regla {p.regla} encontró evidencia de derogación: "
                f"{'; '.join(p.evidencia)}. Corrija el registro o documente la excepción antes de indexar.")
        if r.estado == "derogado" and p.estado != "derogado":
            avisos.append(f"{d.clave}: el registro lo declara derogado sin evidencia en el corpus; prevalece el registro.")
        final[d.clave] = r
    claves_docs = {d.clave for d in docs}
    for clave in registro:
        if clave not in claves_docs:
            avisos.append(f"{clave}: está en el registro pero no en el corpus.")
    return final, avisos
