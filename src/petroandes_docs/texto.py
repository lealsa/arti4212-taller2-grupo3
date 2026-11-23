"""Normalización y tokenización léxica; los códigos y cifras se conservan enteros y por partes."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import snowballstemmer

_STEM = snowballstemmer.stemmer("spanish")

# Palabras vacías del español más palabras interrogativas y de relleno de consulta.
STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes aquel aquella aquellas aquellos aqui asi aun
cada como con contra cual cuales cualquier cuando cuanta cuantas cuanto cuantos de del desde donde dos
el ella ellas ello ellos en entre era eran es esa esas ese eso esos esta estas este esto estos fue fueron
ha hace hacer han hasta hay la las le les lo los mas me mi mis mucho muy nada ni no nos o otra otras otro
otros para pero poco por porque que quien quienes se segun ser si sin sobre son su sus tal tambien tan
tanto te tiene tienen todo todos tras tu tus un una unas uno unos usted ustedes y ya
debe deben dice dicen hoy actual actualmente cuál cuáles qué quién cómo dónde cuándo cuánto cuánta
puede pueden podria seria sea esten este estan estar tiempo vez veces caso casos
""".split())


def plegar(texto: str) -> str:
    """Minúsculas y sin tildes (la ñ se conserva como n)."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def normalizar_espacios(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


# Un token es una palabra o un identificador compuesto con guiones, puntos, comas, barras o '+'.
_TOKEN = re.compile(r"[a-z0-9]+(?:[-.,/+][a-z0-9]+)*")


@lru_cache(maxsize=50_000)
def _raiz(palabra: str) -> str:
    return _STEM.stemWord(palabra)


def tokens(texto: str, quitar_vacias: bool = True) -> list[str]:
    """Tokens léxicos para BM25: palabras con raíz, e identificadores enteros y por partes."""
    salida: list[str] = []
    for m in _TOKEN.finditer(plegar(texto)):
        tok = m.group(0).strip(".,")
        if not tok:
            continue
        compuesto = bool(re.search(r"[-.,/+]", tok))
        tiene_digito = any(c.isdigit() for c in tok)
        if compuesto or tiene_digito:
            salida.append(tok)  # identificador o cifra exacta: sin raíz
            if compuesto:
                for parte in re.split(r"[-.,/+]", tok):
                    if parte and not (quitar_vacias and parte in STOPWORDS):
                        salida.append(parte if any(c.isdigit() for c in parte) else _raiz(parte))
            continue
        if quitar_vacias and (tok in STOPWORDS or len(tok) < 2):
            continue
        salida.append(_raiz(tok))
    return salida


CODIGO_DOC = re.compile(r"\b(MAN|PRO|RES|ACTA|COM|FIC)-[A-Z]{2,5}-[A-Z0-9]{2,5}(?:-\d{4})?(?:-\d{2})?\b")
RESOLUCION_TEXTO = re.compile(r"resoluci[oó]n\s+(\d{3,4})\s+de\s+(\d{4})", re.IGNORECASE)
VERSION_TEXTO = re.compile(r"\bv(?:ersi[oó]n)?\s*(\d+)\b", re.IGNORECASE)
