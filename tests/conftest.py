import importlib.util
import os
import shutil
import stat
from dataclasses import replace
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
os.environ.setdefault("PETROANDES_RAIZ", str(RAIZ))


def _embeddings_por_defecto() -> str:
    """Sin variable, el alterno de spaCy si está instalado; si no (instalación con `.[st]`), e5."""
    if importlib.util.find_spec("spacy") and importlib.util.find_spec("es_core_news_md"):
        return "spacy:es_core_news_md"
    return "st:intfloat/multilingual-e5-small"


os.environ.setdefault("PETROANDES_EMBEDDINGS", _embeddings_por_defecto())
# Las pruebas no descargan el decisor: usan la línea base (los modelos se prueban con `comparar`).
os.environ.setdefault("PETROANDES_ESTRATEGIA", "A0")


@pytest.fixture(scope="session")
def cfg(tmp_path_factory):
    from petroandes_docs.config import cargar
    return replace(cargar(), datos=tmp_path_factory.mktemp("datos"))


@pytest.fixture(scope="session")
def indice(cfg):
    from petroandes_docs.indice import Indice
    return Indice.construir(cfg, log=lambda *_: None)


@pytest.fixture()
def cfg_aislado(tmp_path, cfg):
    """Copia del corpus y del registro para pruebas que los modifican."""
    shutil.copytree(cfg.corpus_pdf, tmp_path / "pdf")
    shutil.copy(cfg.registro, tmp_path / "registro.yaml")
    # En Windows los PDF del corpus pueden venir con atributo de solo lectura y la copia lo conserva;
    # sin esto, las pruebas que retiran un documento fallan con «Acceso denegado».
    for ruta in [tmp_path / "registro.yaml", *(tmp_path / "pdf").rglob("*")]:
        os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IWRITE)
    return replace(cfg, corpus_pdf=tmp_path / "pdf", registro=tmp_path / "registro.yaml", datos=tmp_path / "datos")
