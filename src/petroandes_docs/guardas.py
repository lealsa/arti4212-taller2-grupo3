"""Guardas deterministas alrededor de los pasos con modelo (ADR-008).

`conserva_entidades`: la reescritura del intérprete no puede perder ni cambiar códigos, equipos, tramos o cifras.
`cubre_entidades`: una frase solo puede responder si nombra las entidades de la pregunta.
"""
from __future__ import annotations

import re

from .texto import plegar

_TRAMO = re.compile(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*[–—-]\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b")
_CODIGO = re.compile(r"\b[A-Z]{1,5}(?:-[A-Z0-9]+)+\b")
_PK = re.compile(r"\bK\s?\d{3}\+\d{3}\b")
_PROPIO = re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:[A-Z][a-záéíóúñ]+)*\b")
_CIFRA = re.compile(r"\d+(?:[.,]\d+)*")
_INICIO = re.compile(r"(^|[¿¡.!?:;]\s*|[«\"(]\s*)$")


def _norm(t: str) -> str:
    return re.sub(r"\s*[–—-]\s*", "-", plegar(t)).strip()


def entidades(texto: str) -> set[str]:
    ents: set[str] = set()
    ocupado: list[tuple[int, int]] = []
    for m in _TRAMO.finditer(texto):
        if any(ch.isdigit() for ch in m.group(0)):
            continue
        ents.add(_norm(m.group(0)))
        ocupado.append(m.span())
    for rx in (_CODIGO, _PK):
        for m in rx.finditer(texto):
            if rx is _CODIGO and not any(ch.isdigit() for ch in m.group(0)):
                continue
            ents.add(_norm(m.group(0)))
            ocupado.append(m.span())
    for m in _PROPIO.finditer(texto):
        if any(a <= m.start() < b for a, b in ocupado):
            continue
        if _INICIO.search(texto[: m.start()]):
            continue
        if len(m.group(0)) < 4:
            continue
        ents.add(_norm(m.group(0)))
    return ents


def cifras(texto: str) -> set[str]:
    return {c.replace(".", "").replace(",", "") for c in _CIFRA.findall(texto)}


def conserva_entidades(original: str, reescrita: str) -> tuple[bool, str]:
    if not reescrita or not reescrita.strip():
        return False, "reescritura vacía"
    faltan = [e for e in entidades(original) if e not in _norm(reescrita)]
    if faltan:
        return False, f"perdió entidades: {sorted(faltan)}"
    nuevas = cifras(reescrita) - cifras(original)
    if nuevas:
        return False, f"agregó cifras: {sorted(nuevas)}"
    return True, "ok"


def cubre_entidades(ents: set[str], texto: str) -> bool:
    t = _norm(texto)
    return all(e in t for e in ents)
