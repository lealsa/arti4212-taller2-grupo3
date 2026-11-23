"""Registro de auditoría de cada consulta (Wire Tap)."""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def nueva_traza() -> str:
    return uuid.uuid4().hex[:16]


def registrar(path: Path, evento: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    evento = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), **evento}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


@contextmanager
def cronometro():
    t = {"inicio": time.perf_counter(), "ms": None}
    yield t
    t["ms"] = round((time.perf_counter() - t["inicio"]) * 1000, 1)
