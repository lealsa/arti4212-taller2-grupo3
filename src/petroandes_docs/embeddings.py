"""Modelo de embeddings con huella (ADR-004): proveedor, modelo, commit y dimensión.

Si la huella del modelo cargado no coincide con la del índice, el índice se niega a buscar.
Proveedores: `st:<modelo>[@commit]` (sentence-transformers) y `spacy:<modelo>` (alterno sin Hugging Face).
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    huella: str
    dimension: int

    def documentos(self, textos: list[str]) -> list[list[float]]: ...
    def consulta(self, texto: str) -> list[float]: ...


def _normalizar(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


class SentenceTransformerEmbedder:
    def __init__(self, modelo: str = "intfloat/multilingual-e5-small", revision: str | None = None):
        from sentence_transformers import SentenceTransformer  # extra opcional
        from .revisiones import resolver
        self._m = SentenceTransformer(modelo, revision=revision)
        dim = getattr(self._m, "get_embedding_dimension", None) or self._m.get_sentence_embedding_dimension
        self.dimension = dim()
        self._e5 = "e5" in modelo.lower()
        # La huella lleva el commit cargado, no la rama: si el modelo cambia, el índice deja de coincidir.
        self.revision = resolver(modelo, revision)
        self.huella = f"st:{modelo}@{self.revision}:{self.dimension}"

    def documentos(self, textos):
        pre = [("passage: " + t) if self._e5 else t for t in textos]
        return self._m.encode(pre, normalize_embeddings=True).tolist()

    def consulta(self, texto):
        pre = ("query: " + texto) if self._e5 else texto
        return self._m.encode([pre], normalize_embeddings=True)[0].tolist()


class SpacyIdfEmbedder:
    """Promedio ponderado por IDF de los vectores de palabra (sin palabras vacías).

    El IDF se ajusta con el corpus en la carga inicial y queda congelado en el manifiesto; forma parte
    de la huella, porque cambiarlo cambia todos los vectores.
    """

    def __init__(self, modelo: str = "es_core_news_md", idf: dict[str, float] | None = None):
        import spacy
        self._nlp = spacy.load(modelo, disable=["parser", "ner", "lemmatizer", "morphologizer", "attribute_ruler"])
        self.modelo = modelo
        self.version_modelo = self._nlp.meta.get("version", "?")
        self.dimension = int(self._nlp.vocab.vectors_length)
        self.idf = idf or {}
        self._actualizar_huella()

    def _actualizar_huella(self):
        h = hashlib.sha256(json.dumps(self.idf, sort_keys=True).encode()).hexdigest()[:12]
        self.huella = f"spacy:{self.modelo}@{self.version_modelo}:{self.dimension}:idf-{h}"

    def _palabras(self, texto: str):
        return [w for w in self._nlp(texto) if w.has_vector and not w.is_stop and not w.is_punct and not w.like_num]

    def ajustar_idf(self, textos: list[str]) -> None:
        df = Counter()
        for t in textos:
            df.update({w.lower_ for w in self._palabras(t)})
        n = len(textos)
        self.idf = {w: math.log((n + 1) / (c + 0.5)) for w, c in df.items()}
        self._actualizar_huella()

    def _vec(self, texto: str) -> list[float]:
        ws = self._palabras(texto)
        if not ws:
            return [0.0] * self.dimension
        maximo = max(self.idf.values()) if self.idf else 1.0
        v = sum(w.vector * self.idf.get(w.lower_, maximo) for w in ws)
        return _normalizar(np.asarray(v, dtype=float)).tolist()

    def documentos(self, textos):
        return [self._vec(t) for t in textos]

    def consulta(self, texto):
        return self._vec(texto)


def crear(especificacion: str, estado: dict | None = None) -> Embedder:
    proveedor, _, modelo = especificacion.partition(":")
    if proveedor == "st":
        from .revisiones import separar
        nombre, revision = separar(modelo or "intfloat/multilingual-e5-small")
        return SentenceTransformerEmbedder(nombre, revision=revision)
    if proveedor == "spacy":
        return SpacyIdfEmbedder(modelo or "es_core_news_md", idf=(estado or {}).get("idf"))
    raise ValueError(f"Proveedor de embeddings desconocido: {especificacion}")


def estado_de(emb: Embedder) -> dict:
    """Lo que hay que guardar en el manifiesto para reconstruir exactamente el mismo modelo."""
    return {"idf": emb.idf} if isinstance(emb, SpacyIdfEmbedder) else {}
