"""Recuperación híbrida (densa + BM25, fusionadas con RRF) con el filtro de vigencia dentro de cada consulta.

El filtro «posterior» existe solo para la ablación de la evaluación.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from qdrant_client import models

from .indice import Indice

ESTADOS_CONSULTABLES = ["vigente", "pendiente_certificacion", "no_normativo"]


@dataclass
class Resultado:
    payload: dict
    puntaje: float
    rango: int

    @property
    def id(self) -> str:
        return self.payload["id"]


def filtro_vigencia(fecha_referencia: str | None = None, clase: str | None = None, codigo: str | None = None) -> models.Filter:
    must: list = []
    if fecha_referencia:
        f = int(date.fromisoformat(fecha_referencia).strftime("%Y%m%d"))
        must.append(models.FieldCondition(key="vigente_desde", range=models.Range(lte=f)))
        must.append(models.Filter(should=[
            models.IsNullCondition(is_null=models.PayloadField(key="vigente_hasta")),
            models.FieldCondition(key="vigente_hasta", range=models.Range(gt=f)),
        ]))
    else:
        must.append(models.FieldCondition(key="estado_vigencia", match=models.MatchAny(any=ESTADOS_CONSULTABLES)))
    if clase:
        must.append(models.FieldCondition(key="clase", match=models.MatchValue(value=clase)))
    if codigo:
        must.append(models.FieldCondition(key="codigo", match=models.MatchValue(value=codigo)))
    return models.Filter(must=must)


def _extra(clase: str | None, codigo: str | None) -> models.Filter | None:
    must = []
    if clase:
        must.append(models.FieldCondition(key="clase", match=models.MatchValue(value=clase)))
    if codigo:
        must.append(models.FieldCondition(key="codigo", match=models.MatchValue(value=codigo)))
    return models.Filter(must=must) if must else None


def buscar(indice: Indice, consulta: str, k: int = 5, modo: str = "hibrido", clase: str | None = None,
           codigo: str | None = None, fecha_referencia: str | None = None, filtro: str = "previo",
           prefetch: int = 25) -> list[Resultado]:
    if modo not in ("hibrido", "semantico", "lexico"):
        raise ValueError(f"modo desconocido: {modo}")
    if filtro == "previo":
        flt = filtro_vigencia(fecha_referencia, clase, codigo)
    else:
        flt = _extra(clase, codigo)
    denso = indice.embedder.consulta(consulta)
    idx, val = indice.lexico.vector_consulta(consulta)
    disperso = models.SparseVector(indices=idx, values=val)
    c, col = indice.cliente, indice.coleccion
    if modo == "semantico":
        r = c.query_points(col, query=denso, using="denso", query_filter=flt, limit=k, with_payload=True)
    elif modo == "lexico":
        if not idx:
            return []
        r = c.query_points(col, query=disperso, using="lexico", query_filter=flt, limit=k, with_payload=True)
    else:
        pre = [models.Prefetch(query=denso, using="denso", filter=flt, limit=prefetch)]
        if idx:
            pre.append(models.Prefetch(query=disperso, using="lexico", filter=flt, limit=prefetch))
        r = c.query_points(col, prefetch=pre, query=models.FusionQuery(fusion=models.Fusion.RRF),
                           limit=k, with_payload=True)
    puntos = r.points
    if filtro == "posterior":
        puntos = [p for p in puntos if p.payload["estado_vigencia"] in ESTADOS_CONSULTABLES]
    return [Resultado(p.payload, float(p.score), i + 1) for i, p in enumerate(puntos)]
