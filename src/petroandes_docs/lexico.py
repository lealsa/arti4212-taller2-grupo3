"""BM25 como vector disperso de Qdrant, para que el filtro de vigencia se aplique en la misma consulta."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from .texto import tokens


@dataclass
class ModeloLexico:
    vocabulario: dict[str, int] = field(default_factory=dict)
    idf: dict[str, float] = field(default_factory=dict)
    largo_promedio: float = 1.0
    k1: float = 1.2
    b: float = 0.75

    @classmethod
    def ajustar(cls, textos: list[str]) -> "ModeloLexico":
        docs = [tokens(t) for t in textos]
        df = Counter()
        for d in docs:
            df.update(set(d))
        n = len(docs)
        vocab = {t: i for i, t in enumerate(sorted(df))}
        idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        return cls(vocab, idf, sum(map(len, docs)) / max(n, 1))

    def idf_desconocido(self) -> float:
        return max(self.idf.values()) if self.idf else 1.0

    def vector_documento(self, texto: str) -> tuple[list[int], list[float]]:
        toks = tokens(texto)
        tf = Counter(t for t in toks if t in self.vocabulario)
        dl = len(toks)
        idx, val = [], []
        for t, f in tf.items():
            w = self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.largo_promedio))
            idx.append(self.vocabulario[t])
            val.append(round(w, 6))
        return idx, val

    def vector_consulta(self, texto: str) -> tuple[list[int], list[float]]:
        terms = sorted({t for t in tokens(texto) if t in self.vocabulario})
        return [self.vocabulario[t] for t in terms], [1.0] * len(terms)

    def cobertura(self, consulta: str, texto: str) -> float:
        """Fracción del IDF de la consulta que aparece en el texto.

        Los términos de la consulta que no existen en el corpus pesan el IDF máximo: si la pregunta
        habla de algo que el corpus no menciona («Brent»), la cobertura baja y el sistema se niega.
        """
        q = set(tokens(consulta))
        if not q:
            return 0.0
        presentes = set(tokens(texto))
        total = sum(self.idf.get(t, self.idf_desconocido()) for t in q)
        dentro = sum(self.idf.get(t, self.idf_desconocido()) for t in q if t in presentes)
        return dentro / total if total else 0.0

    def a_dict(self) -> dict:
        return {"vocabulario": self.vocabulario, "idf": self.idf, "largo_promedio": self.largo_promedio,
                "k1": self.k1, "b": self.b}

    @classmethod
    def desde_dict(cls, d: dict) -> "ModeloLexico":
        return cls(d["vocabulario"], d["idf"], d["largo_promedio"], d["k1"], d["b"])
