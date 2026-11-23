"""Composición extractiva de la respuesta (ADR-003): cada afirmación es una unidad literal de un
fragmento recuperado, con su cita; si nada responde, la respuesta es «sin_respaldo».
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .guardas import conserva_entidades, cubre_entidades, entidades
from .indice import Indice
from .recuperacion import Resultado, buscar
from .seguridad import redactar_salida
from .texto import CODIGO_DOC, RESOLUCION_TEXTO, VERSION_TEXTO


@dataclass
class Afirmacion:
    texto: str
    cita: str
    codigo: str
    version: str
    seccion: str
    titulo_seccion: str
    estado_vigencia: str
    cobertura: float
    advertencia: str | None = None


@dataclass
class Respuesta:
    pregunta: str
    estado: str                         # respondida | sin_respaldo
    afirmaciones: list[Afirmacion] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    consultados: list[dict] = field(default_factory=list)
    consulta_efectiva: str = ""
    parametros: dict = field(default_factory=dict)
    interpretacion: dict | None = None

    def a_dict(self) -> dict:
        return asdict(self)

    def markdown(self) -> str:
        lineas = [f"**Pregunta:** {self.pregunta}", ""]
        if self.interpretacion and self.interpretacion.get("aceptada"):
            lineas += [f"_Interpreté su pregunta como: {self.interpretacion['reescritura']}_", ""]
        if self.estado == "sin_respaldo":
            lineas.append("**No encontré respaldo para esta pregunta en el corpus vigente.** No respondo con conocimiento externo.")
        else:
            lineas.append("**Respuesta (texto literal de las fuentes):**")
            for a in self.afirmaciones:
                adv = f" — _{a.advertencia}_" if a.advertencia else ""
                lineas.append(f"- {a.texto} [{a.cita}]{adv}")
        if self.advertencias:
            lineas += ["", "**Advertencias:**"] + [f"- {w}" for w in self.advertencias]
        if self.consultados:
            lineas += ["", "Fragmentos consultados: " + ", ".join(
                f"{c['cita']}{' (cuarentena)' if c['cuarentena'] else ''}" for c in self.consultados)]
        return "\n".join(lineas)


def _cita(p: dict) -> str:
    v = f" v{p['version']}" if p["version"] not in ("—", "") else ""
    return f"{p['codigo']}{v} §{p['seccion']}"


def _derogados_mencionados(indice: Indice, pregunta: str) -> list[tuple[str, object]]:
    """Códigos o resoluciones que la pregunta nombra y que el registro declara derogados."""
    reg = indice.registro()
    mencion = []
    for m in CODIGO_DOC.finditer(pregunta.upper()):
        cod = m.group(0)
        resto = pregunta[m.end(): m.end() + 15]
        mv = VERSION_TEXTO.match(resto.strip())
        for clave, v in reg.items():
            if v.codigo == cod and v.estado == "derogado" and (mv is None or v.version == mv.group(1)):
                mencion.append((m.group(0), v))
    for num, anio in RESOLUCION_TEXTO.findall(pregunta):
        for v in reg.values():
            if v.codigo.endswith(f"-{num}-{anio}") and v.estado == "derogado":
                mencion.append((f"Resolución {num} de {anio}", v))
    return mencion


def _reescribir(pregunta: str, menciones) -> str:
    """Translator: la referencia a un derogado se sustituye por su reemplazo antes de buscar."""
    q = pregunta
    for texto, v in menciones:
        if not v.reemplazado_por:
            continue
        reemplazo = v.reemplazado_por.split(" v")[0]
        if texto.lower().startswith("resolución"):
            m = re.search(r"-(\d{3,4})-(\d{4})$", reemplazo)
            reemplazo = f"Resolución {m.group(1)} de {m.group(2)}" if m else reemplazo
        q = re.sub(re.escape(texto) + r"(\s+v(ersi[oó]n)?\s*\d+)?", reemplazo, q, flags=re.IGNORECASE)
    return q


@dataclass
class Estrategia:
    """Cómo se decide responder (ADR-008).

    nombre       A0 | A1 | A2 (o libre)
    decisor      objeto con puntuar(pregunta, textos, extra) -> list[float]; None = cobertura léxica
    interprete   objeto con reescribir(pregunta) -> str; None = sin reinterpretación
    umbral       puntaje mínimo para responder; None = el de la configuración (cobertura)
    guarda       exigir que la frase nombre las entidades de la pregunta
    adicionales  qué frases acompañan a la mejor: «cercanas» (puntaje ≥ 0,85 del mejor, ADR-003) o
                 «mismo_documento» (además, del mismo documento y versión que la mejor).
    max_afirmaciones  tope de frases; None = el de `componer` (3). La estrategia elegida usa 1.
    """
    nombre: str = "A0"
    decisor: object | None = None
    interprete: object | None = None
    umbral: float | None = None
    guarda: bool = False
    adicionales: str = "cercanas"
    max_afirmaciones: int | None = None


def componer(indice: Indice, pregunta: str, k: int = 6, modo: str = "hibrido", fecha_referencia: str | None = None,
             umbral: float | None = None, max_afirmaciones: int = 3, estrategia: Estrategia | None = None) -> Respuesta:
    est = estrategia or Estrategia()
    if est.max_afirmaciones is not None:
        max_afirmaciones = est.max_afirmaciones
    if umbral is None:
        umbral = est.umbral if est.umbral is not None else indice.cfg.umbral_cobertura
    advertencias: list[str] = []
    menciones = [] if fecha_referencia else _derogados_mencionados(indice, pregunta)
    for texto, v in menciones:
        hasta = f" desde el {v.vigente_hasta}" if v.vigente_hasta else ""
        advertencias.append(f"{texto} está derogado{hasta} ({v.regla}; certifica {v.certificado_por}). "
                            f"Se responde con el documento vigente: {v.reemplazado_por}.")
    consulta = _reescribir(pregunta, menciones)
    if fecha_referencia:
        advertencias.append(f"Respuesta según los documentos que regían el {fecha_referencia}, no según los vigentes hoy.")

    interpretacion, reescritura = None, None
    if est.interprete is not None:
        r_ = est.interprete.reescribir(consulta)
        ok, motivo = conserva_entidades(consulta, r_)
        interpretacion = {"reescritura": r_, "aceptada": ok, "motivo": motivo, "interprete": est.interprete.nombre}
        reescritura = r_ if ok else None
    consulta_busqueda = f"{consulta} {reescritura}" if reescritura else consulta

    resultados: list[Resultado] = buscar(indice, consulta_busqueda, k=k, modo=modo, fecha_referencia=fecha_referencia)
    consultados = [{"id": r.id, "cita": _cita(r.payload), "estado_vigencia": r.payload["estado_vigencia"],
                    "cuarentena": r.payload["cuarentena"], "rango": r.rango} for r in resultados]
    if any(r.payload["cuarentena"] for r in resultados):
        cits = ", ".join(_cita(r.payload) for r in resultados if r.payload["cuarentena"])
        advertencias.append(f"Se recuperó contenido en cuarentena ({cits}): contiene instrucciones dirigidas a sistemas "
                            "automáticos y no se usó para componer la respuesta.")

    ents = entidades(consulta) if est.guarda else set()
    brutos, descartadas = [], 0
    for r in resultados:
        p = r.payload
        if p["cuarentena"]:
            continue
        contexto = f"{p['codigo']} {p['titulo_documento']} {p['titulo_seccion']}"
        for u in p["unidades"]:
            if ents and not cubre_entidades(ents, contexto + " " + u):
                descartadas += 1
                continue
            brutos.append((r.rango, contexto, u, p))
    decisor = est.decisor
    if decisor is None:
        puntajes = [max([indice.lexico.cobertura(q, c + " " + u) for q in (consulta, reescritura) if q])
                    for _, c, u, _ in brutos]
    else:
        puntajes = decisor.puntuar(consulta, [f"{c}: {u}" for _, c, u, _ in brutos],
                                   extra=[reescritura] if reescritura else None)
    candidatos = [(s_ + 0.05 / rg, s_, u, p) for s_, (rg, _, u, p) in zip(puntajes, brutos)]
    candidatos.sort(key=lambda c: -c[0])
    params = {"k": k, "modo": modo, "fecha_referencia": fecha_referencia, "umbral_cobertura": umbral,
              "huella_modelo": indice.embedder.huella, "estrategia": est.nombre,
              "decisor": getattr(decisor, "nombre", "cobertura"), "max_afirmaciones": max_afirmaciones, "guarda_entidades": sorted(ents) if est.guarda else None,
              "unidades_descartadas_por_guarda": descartadas}
    if not candidatos or candidatos[0][1] < umbral:
        return Respuesta(pregunta, "sin_respaldo", [], advertencias, consultados, consulta_busqueda, params, interpretacion)

    # Preferir la norma sobre el antecedente cuando cubren la pregunta casi igual.
    mejor = candidatos[0][0]
    cerca = [c for c in candidatos if c[0] >= 0.85 * mejor and c[1] >= umbral]
    cerca.sort(key=lambda c: (c[3]["naturaleza"] != "normativo", -c[0]))
    elegidas, por_frag = [], {}
    for puntaje, cob, u, p in cerca:
        if len(elegidas) >= max_afirmaciones:
            break
        if est.adicionales == "mismo_documento" and elegidas and (p["codigo"], p["version"]) != (elegidas[0].codigo, elegidas[0].version):
            continue
        if por_frag.get(p["id"], 0) >= 2:
            continue
        por_frag[p["id"]] = por_frag.get(p["id"], 0) + 1
        texto, n = redactar_salida(u)
        if n:
            advertencias.append(f"Se retiraron {n} dirección(es) de correo o URL de la respuesta.")
        elegidas.append(Afirmacion(texto=texto, cita=_cita(p), codigo=p["codigo"], version=p["version"],
                                   seccion=p["seccion"], titulo_seccion=p["titulo_seccion"],
                                   estado_vigencia=p["estado_vigencia"], cobertura=round(cob, 3),
                                   advertencia=p.get("advertencia_vigencia")))
    return Respuesta(pregunta, "respondida", elegidas, advertencias, consultados, consulta_busqueda, params, interpretacion)
