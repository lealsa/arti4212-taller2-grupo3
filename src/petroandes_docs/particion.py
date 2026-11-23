"""Splitter + Content Enricher: de documento extraído a fragmentos con metadatos de gobierno."""
from __future__ import annotations

import hashlib

from .modelos import DocumentoExtraido, Fragmento, Vigencia
from .seguridad import escanear, en_cuarentena
from .vigencia import clase_de


def _fecha_int(f: str | None) -> int | None:
    return int(f.replace("-", "")) if f else None


def fragmentar(doc: DocumentoExtraido, vig: Vigencia, contrato: dict) -> list[Fragmento]:
    clase = clase_de(doc, contrato)
    regla_clase = contrato["clases"][clase]
    limite = int(regla_clase.get("tamano_maximo_caracteres", 2500))
    fragmentos: list[Fragmento] = []
    for s in doc.secciones:
        # Una sección es la unidad de partición. Solo si excede el límite se divide por unidades
        # completas (cláusula, viñeta o fila), nunca a mitad de una.
        grupos, actual, largo = [], [], 0
        for u in s.unidades:
            if actual and largo + len(u) > limite:
                grupos.append(actual)
                actual, largo = [], 0
            actual.append(u)
            largo += len(u)
        if actual:
            grupos.append(actual)
        for i, unidades in enumerate(grupos, start=1):
            texto = "\n".join(unidades)
            sufijo = "" if len(grupos) == 1 else f"-{i}"
            hallazgos = escanear(texto)
            cuarentena = en_cuarentena(hallazgos)
            fragmentos.append(Fragmento(
                id=f"{doc.codigo}@v{doc.version}#{s.id}{sufijo}",
                codigo=doc.codigo, version=doc.version, titulo_documento=doc.titulo,
                clase=clase, naturaleza=regla_clase["naturaleza"], origen=regla_clase["origen"],
                area_emisora=doc.area_emisora, emisor=doc.emisor, fecha_emision=doc.fecha_emision,
                seccion=s.id, titulo_seccion=s.titulo, texto=texto, unidades=unidades, pagina=s.pagina,
                archivo=doc.archivo, sha256_documento=doc.sha256,
                sha256_fragmento=hashlib.sha256(texto.encode()).hexdigest(),
                estado_vigencia=vig.estado, vigente_desde=_fecha_int(vig.vigente_desde),
                vigente_hasta=_fecha_int(vig.vigente_hasta), regla_vigencia=vig.regla,
                certificado_por=vig.certificado_por, reemplazado_por=vig.reemplazado_por,
                cuarentena=cuarentena,
                motivo_cuarentena=", ".join(sorted({h.patron for h in hallazgos})) if cuarentena else None,
                advertencia_vigencia=vig.advertencia,
            ))
    return fragmentos


def texto_para_indexar(f: Fragmento) -> str:
    """Cabecera de contexto + cuerpo: el fragmento lleva consigo de qué documento y sección es."""
    v = f" versión {f.version}" if f.version not in ("—", "") else ""
    return f"{f.titulo_documento} ({f.codigo}{v}). {f.titulo_seccion}.\n{f.texto}"
