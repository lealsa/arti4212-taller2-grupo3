"""Commit exacto de un modelo de Hugging Face, para la huella del índice (ADR-004)."""
from __future__ import annotations

from pathlib import Path


def separar(modelo: str) -> tuple[str, str | None]:
    """«intfloat/multilingual-e5-small@abc123» → («intfloat/multilingual-e5-small», «abc123»)."""
    nombre, sep, rev = modelo.partition("@")
    return nombre, (rev or None) if sep else None


def resolver(modelo: str, revision: str | None = None) -> str:
    """Commit de la copia local del modelo; si no se puede averiguar, la revisión pedida o «main»."""
    try:
        from huggingface_hub import snapshot_download
        ruta = snapshot_download(modelo, revision=revision, local_files_only=True)
        return Path(ruta).name
    except Exception:
        return revision or "main"
