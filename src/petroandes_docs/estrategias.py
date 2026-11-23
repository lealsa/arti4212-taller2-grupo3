"""Estrategias de decisión de ADR-008 (A0, A0G, A1, A2r1, A2md, A2, A3) y la de operación (A2)."""
from __future__ import annotations

import logging
import os

from .composicion import Estrategia

INTERPRETE_POR_DEFECTO = "hf:Qwen/Qwen2.5-1.5B-Instruct"
DECISOR_POR_DEFECTO = "crossencoder:BAAI/bge-reranker-v2-m3"
UMBRAL_DECISOR = 0.5
NOMBRES = ("A0", "A0G", "A1", "A2r1", "A2md", "A2", "A3")


def fabrica(nombre: str, ix, interprete: str = INTERPRETE_POR_DEFECTO, decisor: str = DECISOR_POR_DEFECTO,
            umbral_decisor: float = UMBRAL_DECISOR):
    """Devuelve una función que construye la Estrategia. Los modelos se cargan solo al llamarla."""
    from . import decisores, interpretacion
    dec = lambda: decisores.crear(decisor, ix)  # noqa: E731
    itp = lambda: interpretacion.crear(interprete)  # noqa: E731
    tabla = {
        "A0": lambda: Estrategia("A0"),
        "A0G": lambda: Estrategia("A0G", guarda=True),
        "A1": lambda: Estrategia("A1", interprete=itp(), guarda=True),
        "A2r1": lambda: Estrategia("A2r1", decisor=dec(), umbral=umbral_decisor, guarda=True),
        "A2md": lambda: Estrategia("A2md", decisor=dec(), umbral=umbral_decisor, guarda=True, adicionales="mismo_documento"),
        "A2": lambda: Estrategia("A2", decisor=dec(), umbral=umbral_decisor, guarda=True, max_afirmaciones=1),
        "A3": lambda: Estrategia("A3", decisor=dec(), interprete=itp(), umbral=umbral_decisor, guarda=True, max_afirmaciones=1),
    }
    if nombre not in tabla:
        raise SystemExit(f"Estrategia desconocida: {nombre}. Opciones: {', '.join(NOMBRES)}")
    return tabla[nombre]


def por_defecto(ix) -> tuple[Estrategia, str | None]:
    """Estrategia de operación y, si se degradó, el aviso para el usuario."""
    nombre = os.environ.get("PETROANDES_ESTRATEGIA", "A2")
    try:
        return fabrica(nombre, ix, os.environ.get("PETROANDES_INTERPRETE", INTERPRETE_POR_DEFECTO),
                       os.environ.get("PETROANDES_DECISOR", DECISOR_POR_DEFECTO))(), None
    except Exception as e:  # modelo no descargable, sin memoria, etc.
        logging.getLogger(__name__).warning("Estrategia %s no disponible (%s); modo degradado A0G", nombre, e)
        return fabrica("A0G", ix)(), (f"Modo degradado: la estrategia {nombre} no está disponible; se decide con "
                                      "cobertura léxica y guarda de entidades (más negativas, misma garantía de no "
                                      "responder fuera del corpus).")
