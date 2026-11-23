"""Decisores: puntúan cuánto responde una frase candidata a la pregunta (ADR-008)."""
from __future__ import annotations

import math


class DecisorCobertura:
    nombre = "cobertura"

    def __init__(self, lexico):
        self.lexico = lexico

    def puntuar(self, pregunta: str, textos: list[str], extra: list[str] | None = None) -> list[float]:
        consultas = [pregunta] + [e for e in (extra or []) if e]
        return [max(self.lexico.cobertura(q, t) for q in consultas) for t in textos]


class DecisorCrossEncoder:
    def __init__(self, modelo: str = "BAAI/bge-reranker-v2-m3", lote: int = 16, max_len: int = 512,
                 revision: str | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        from .revisiones import resolver
        self._torch = torch
        self._tok = AutoTokenizer.from_pretrained(modelo, revision=revision)
        self._m = AutoModelForSequenceClassification.from_pretrained(modelo, revision=revision)
        self._m.eval()
        self.lote, self.max_len = lote, max_len
        self.revision = resolver(modelo, revision)
        self.nombre = f"crossencoder:{modelo}@{self.revision}"
        self._cache: dict[tuple[str, str], float] = {}

    def puntuar(self, pregunta: str, textos: list[str], extra: list[str] | None = None) -> list[float]:
        faltan = [t for t in dict.fromkeys(textos) if (pregunta, t) not in self._cache]
        for i in range(0, len(faltan), self.lote):
            bloque = faltan[i:i + self.lote]
            enc = self._tok([pregunta] * len(bloque), bloque, padding=True, truncation=True,
                            max_length=self.max_len, return_tensors="pt")
            with self._torch.no_grad():
                logits = self._m(**enc).logits.view(-1).float().tolist()
            for t, z in zip(bloque, logits):
                self._cache[(pregunta, t)] = 1 / (1 + math.exp(-z))
        return [self._cache[(pregunta, t)] for t in textos]


class DecisorFijo:
    """Para pruebas: puntaje por subcadena."""
    nombre = "fijo"

    def __init__(self, reglas: dict[str, float], defecto: float = 0.0):
        self.reglas, self.defecto = reglas, defecto

    def puntuar(self, pregunta: str, textos: list[str], extra=None) -> list[float]:
        return [max([v for k, v in self.reglas.items() if k in t] or [self.defecto]) for t in textos]


def crear(spec: str, indice):
    if spec == "cobertura":
        return DecisorCobertura(indice.lexico)
    proveedor, _, modelo = spec.partition(":")
    if proveedor == "crossencoder":
        from .revisiones import separar
        nombre, revision = separar(modelo or "BAAI/bge-reranker-v2-m3")
        return DecisorCrossEncoder(nombre, revision=revision)
    raise ValueError(f"Decisor desconocido: {spec}")
