"""Defensas ante instrucciones embebidas: `escanear` detecta (y es evadible, ver las pruebas);
`redactar_salida` y la composición extractiva contienen.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .texto import plegar

PATRONES = [
    ("ignorar_instrucciones", r"\b(ignor\w*|olvid\w*|omit\w*|desobedec\w*)\b.{0,40}\binstrucc\w*"),
    ("dirigido_a_sistema", r"\binstrucc\w*\s+(para|a)\s+(los\s+|las\s+)?(sistemas?|modelos?|asistentes?|agentes?|ia\b|llm)"),
    ("ocultar_al_usuario", r"\bno\s+(le\s+)?(informe|diga|mencione|revele|comunique)\w*\b.{0,30}\b(usuario|operador)"),
    ("exfiltracion", r"\b(remit\w*|envi\w*|reenv\w*|copi\w*|adjunt\w*)\b.{0,80}(@|\bbuz[oó]n\b|\bcorreo\b|https?://)"),
    ("cambio_de_rol", r"\b(actue|actua|comportate|eres ahora|you are now|act as)\b"),
    ("ingles_clasico", r"\b(ignore (all |any )?(previous|prior) instructions|system prompt|disregard)\b"),
]
_COMPILADOS = [(n, re.compile(p, re.IGNORECASE | re.DOTALL)) for n, p in PATRONES]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
URL = re.compile(r"https?://\S+")


@dataclass
class Hallazgo:
    patron: str
    extracto: str


def escanear(texto: str) -> list[Hallazgo]:
    t = plegar(texto)
    hallazgos = []
    for nombre, rx in _COMPILADOS:
        m = rx.search(t)
        if m:
            hallazgos.append(Hallazgo(nombre, t[max(0, m.start() - 10): m.end() + 10]))
    return hallazgos


def en_cuarentena(hallazgos: list[Hallazgo]) -> bool:
    """Un patrón aislado puede ser legítimo («remita copia al buzón de calidad»); dos no."""
    return len({h.patron for h in hallazgos}) >= 2


def redactar_salida(texto: str) -> tuple[str, int]:
    """Quita direcciones de correo y URL de lo que sale hacia el consumidor (prevención de fuga)."""
    n = len(EMAIL.findall(texto)) + len(URL.findall(texto))
    return URL.sub("[URL retirada]", EMAIL.sub("[correo retirado]", texto)), n


AVISO_CUARENTENA = ("[CONTENIDO EN CUARENTENA] Este apartado contiene texto dirigido a sistemas automáticos "
                    "(posible inyección de instrucciones). No se entrega a consumidores automáticos. "
                    "Un auditor humano puede revisarlo con `petroandes-docs auditar-fragmento`.")
