"""Configuración por variables de entorno, con valores por defecto relativos a la raíz del repositorio."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _raiz() -> Path:
    if os.environ.get("PETROANDES_RAIZ"):
        return Path(os.environ["PETROANDES_RAIZ"]).resolve()
    aqui = Path(__file__).resolve()
    for p in [Path.cwd(), *aqui.parents]:
        if (p / "config" / "contrato_corpus.yaml").exists():
            return p
    return Path.cwd()


@dataclass(frozen=True)
class Config:
    raiz: Path
    corpus_pdf: Path
    contrato: Path
    registro: Path
    datos: Path
    embeddings: str
    qdrant_url: str | None
    umbral_cobertura: float
    k_por_defecto: int

    @property
    def manifiesto(self) -> Path:
        return self.datos / "manifiesto.json"

    @property
    def auditoria(self) -> Path:
        return self.datos / "auditoria.jsonl"

    @property
    def qdrant_path(self) -> Path:
        return self.datos / "qdrant"


def cargar() -> Config:
    raiz = _raiz()
    return Config(
        raiz=raiz,
        corpus_pdf=Path(os.environ.get("PETROANDES_CORPUS", raiz / "corpus" / "pdf")),
        contrato=Path(os.environ.get("PETROANDES_CONTRATO", raiz / "config" / "contrato_corpus.yaml")),
        registro=Path(os.environ.get("PETROANDES_REGISTRO", raiz / "config" / "registro_vigencia.yaml")),
        datos=Path(os.environ.get("PETROANDES_DATOS", raiz / "data")),
        embeddings=os.environ.get("PETROANDES_EMBEDDINGS", "st:intfloat/multilingual-e5-small"),
        qdrant_url=os.environ.get("QDRANT_URL") or None,
        umbral_cobertura=float(os.environ.get("PETROANDES_UMBRAL_COBERTURA", "0.6")),
        k_por_defecto=int(os.environ.get("PETROANDES_K", "5")),
    )
