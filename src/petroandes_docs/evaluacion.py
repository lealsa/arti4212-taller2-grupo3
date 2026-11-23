"""Arnés de evaluación: relevancia de la recuperación, anclaje y tasa de desviación sobre los casos de referencia."""
from __future__ import annotations

import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .composicion import componer
from .indice import Indice
from .recuperacion import buscar
from .texto import normalizar_espacios, plegar

SLO = {"acierto@5_hibrido": 0.90, "desviacion_max": 0.10, "anclaje_min": 0.95, "violaciones_vigencia": 0,
       "rechazo_correcto_min": 0.75}


def _n(t: str) -> str:
    return normalizar_espacios(plegar(t))


def _fid(f: dict) -> str:
    return f"{f['codigo']}@v{f['version']}#{f['seccion']}"


def fallas_del_caso(caso: dict, r, esperados: list[str]) -> list[str]:
    """Compara una Respuesta con la esperada del caso. Determinista: no usa juez."""
    texto = _n(" ".join(a.texto for a in r.afirmaciones))
    avisos = _n(" ".join(r.advertencias + [a.advertencia or "" for a in r.afirmaciones]))
    fallas: list[str] = []
    if caso.get("debe_rechazar"):
        if r.estado != "sin_respaldo":
            fallas.append("respondió una pregunta que no está en el corpus")
    else:
        if caso["tipo"] != "envenenamiento" and r.estado != "respondida":
            fallas.append("se negó a responder una pregunta respondible")
        faltan = [h for h in caso.get("hechos", []) if _n(h) not in texto]
        if faltan and r.estado == "respondida":
            fallas.append(f"faltan hechos: {faltan}")
        prohibidos = [h for h in caso.get("prohibidos", []) if _n(h) in texto]
        if prohibidos:
            fallas.append(f"valores prohibidos en la respuesta: {prohibidos}")
        citas = {f"{a.codigo}@v{a.version}#{a.seccion}" for a in r.afirmaciones}
        if esperados and r.estado == "respondida" and caso["tipo"] != "envenenamiento" and not citas & set(esperados):
            fallas.append(f"cita distinta de la esperada: {sorted(citas)}")
        if caso.get("advertencia_esperada") and _n(caso["advertencia_esperada"]) not in avisos:
            fallas.append(f"falta la advertencia «{caso['advertencia_esperada']}»")
        if caso.get("espera_cuarentena") and "cuarentena" not in avisos:
            fallas.append("no advirtió el contenido en cuarentena")
    return fallas


def evaluar_caso(ix: Indice, caso: dict, juez, umbral: float | None = None, estrategia=None) -> dict:
    fecha = caso.get("fecha_referencia")
    esperados = [_fid(f) for f in caso.get("fuentes", [])]
    t0 = time.perf_counter()
    r = componer(ix, caso["pregunta"], fecha_referencia=fecha, umbral=umbral, estrategia=estrategia)
    latencia = (time.perf_counter() - t0) * 1000
    fallas = fallas_del_caso(caso, r, esperados)

    anclajes = []
    for a in r.afirmaciones:
        p = ix.fragmento(a.codigo, a.version, a.seccion)
        anclajes.append(round(juez.anclaje(a.texto, p["texto"] if p else ""), 3))

    recuperacion = {}
    for modo in ("hibrido", "semantico", "lexico"):
        res = buscar(ix, r.consulta_efectiva or caso["pregunta"], k=5, modo=modo, fecha_referencia=fecha)
        ids = [x.id for x in res]
        rango = next((i + 1 for i, x in enumerate(ids) if x in esperados), None)
        recuperacion[modo] = {"ids": ids, "rango_esperado": rango,
                              "derogados": sum(x.payload["estado_vigencia"] == "derogado" for x in res) if not fecha else 0}
    res_h = buscar(ix, r.consulta_efectiva or caso["pregunta"], k=5, modo="hibrido", fecha_referencia=fecha)
    pert = [juez.pertinencia(caso["pregunta"], x.payload["texto"], frag_id=x.id, esperados=esperados) for x in res_h]

    # Ablación del filtro: sin filtro, ¿cuántos derogados entran al top-5?
    sin_filtro = buscar(ix, r.consulta_efectiva or caso["pregunta"], k=5, modo="hibrido", filtro="ninguno") if not fecha else []
    posterior = buscar(ix, r.consulta_efectiva or caso["pregunta"], k=5, modo="hibrido", filtro="posterior") if not fecha else []

    return {
        "id": caso["id"], "tipo": caso["tipo"], "pregunta": caso["pregunta"], "fecha_referencia": fecha,
        "estado": r.estado, "afirmaciones": [{"texto": a.texto, "cita": a.cita, "cobertura": a.cobertura} for a in r.afirmaciones],
        "advertencias": r.advertencias, "correcto": not fallas, "fallas": fallas,
        "anclaje": anclajes, "recuperacion": recuperacion, "pertinencia@5": pert,
        "ablacion": {"derogados_sin_filtro": sum(x.payload["estado_vigencia"] == "derogado" for x in sin_filtro),
                     "resultados_filtro_posterior": len(posterior)},
        "latencia_ms": round(latencia, 1), "esperados": esperados,
    }


def _metricas(casos: list[dict], umbral_anclaje: float = 0.5) -> dict:
    con_fuente = [c for c in casos if c["esperados"] and c["tipo"] != "no_respondible"]
    rec = {}
    for modo in ("hibrido", "semantico", "lexico"):
        rangos = [c["recuperacion"][modo]["rango_esperado"] for c in con_fuente]
        rec[modo] = {"acierto@1": sum(r == 1 for r in rangos) / len(rangos),
                     "acierto@5": sum(r is not None for r in rangos) / len(rangos),
                     "mrr@5": sum(1 / r for r in rangos if r) / len(rangos)}
    anclajes = [a for c in casos for a in c["anclaje"]]
    pert = [p for c in con_fuente for p in c["pertinencia@5"]]
    rechazos = [c for c in casos if c["tipo"] == "no_respondible"]
    respondibles = [c for c in casos if c["tipo"] != "no_respondible"]
    lat = sorted(c["latencia_ms"] for c in casos)
    return {
        "casos": len(casos), "correctos": sum(c["correcto"] for c in casos),
        "tasa_desviacion": 1 - sum(c["correcto"] for c in casos) / len(casos),
        "desviacion_respondibles": 1 - sum(c["correcto"] for c in respondibles) / len(respondibles),
        "rechazo_correcto": sum(c["correcto"] for c in rechazos) / len(rechazos) if rechazos else None,
        "anclaje": sum(a >= umbral_anclaje for a in anclajes) / len(anclajes) if anclajes else None,
        "anclaje_promedio": statistics.mean(anclajes) if anclajes else None,
        "pertinencia@5": {"pertinente": pert.count("pertinente") / len(pert), "parcial": pert.count("parcial") / len(pert),
                          "no_pertinente": pert.count("no_pertinente") / len(pert)} if pert else None,
        "recuperacion": rec,
        "violaciones_vigencia": sum(c["recuperacion"]["hibrido"]["derogados"] for c in casos),
        "ablacion_derogados_sin_filtro": sum(c["ablacion"]["derogados_sin_filtro"] for c in casos),
        "ablacion_casos_con_derogado_sin_filtro": sum(c["ablacion"]["derogados_sin_filtro"] > 0 for c in casos),
        "ablacion_filtro_posterior_resultados_perdidos": sum(5 - c["ablacion"]["resultados_filtro_posterior"]
                                                             for c in casos if c["fecha_referencia"] is None),
        "latencia_ms_p50": lat[len(lat) // 2], "latencia_ms_p95": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
    }


def barrido_umbral(ix: Indice, casos: list[dict], juez, umbrales=None, estrategia=None) -> list[dict]:
    if umbrales is None:
        umbrales = (0.3, 0.4, 0.5, 0.6, 0.7) if getattr(estrategia, "decisor", None) is None else (0.1, 0.3, 0.5, 0.7, 0.9)
    salida = []
    for u in umbrales:
        rs = [evaluar_caso(ix, c, juez, umbral=u, estrategia=estrategia) for c in casos]
        resp = [r for r in rs if r["tipo"] != "no_respondible"]
        rech = [r for r in rs if r["tipo"] == "no_respondible"]
        salida.append({"umbral": u, "respondibles_correctos": sum(r["correcto"] for r in resp) / len(resp),
                       "rechazo_correcto": sum(r["correcto"] for r in rech) / len(rech),
                       "desviacion": 1 - sum(r["correcto"] for r in rs) / len(rs)})
    return salida


def ejecutar(ix: Indice, ruta_casos: Path, juez, salida: Path, barrido: bool = True, estrategia=None) -> dict:
    conjunto = yaml.safe_load(ruta_casos.read_text(encoding="utf-8"))
    casos = conjunto["casos"]
    resultados = [evaluar_caso(ix, c, juez, estrategia=estrategia) for c in casos]
    m = _metricas(resultados)
    informe = {
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "juez": juez.nombre,
        "huella_modelo": ix.embedder.huella,
        "estrategia": getattr(estrategia, "nombre", "A0"),
        "decisor": getattr(getattr(estrategia, "decisor", None), "nombre", "cobertura"),
        "umbral_cobertura": (estrategia.umbral if estrategia is not None and estrategia.umbral is not None else ix.cfg.umbral_cobertura),
        "conjunto": conjunto.get("version_conjunto"), "slo": SLO, "metricas": m,
        "barrido_umbral": barrido_umbral(ix, casos, juez, estrategia=estrategia) if barrido else [], "casos": resultados,
    }
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "resultados.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "reporte.md").write_text(reporte_md(informe), encoding="utf-8")
    return informe


def _pct(x):
    return "—" if x is None else f"{100 * x:.0f} %"


def reporte_md(inf: dict) -> str:
    m = inf["metricas"]
    slo = inf["slo"]
    ok = lambda c: "cumple" if c else "NO cumple"  # noqa: E731
    L = [f"# Resultados de la evaluación — {inf['fecha']}", "",
         f"- Estrategia de decisión: `{inf.get('estrategia', 'A0')}` (decisor `{inf.get('decisor', 'cobertura')}`, ADR-008) · Umbral: {inf['umbral_cobertura']}",
         f"- Juez: `{inf['juez']}` · Modelo de embeddings: `{inf['huella_modelo']}`",
         f"- Conjunto de referencia v{inf['conjunto']}: {m['casos']} casos; {m['correctos']} correctos.", "",
         "## Métricas frente a los SLO", "", "| Métrica | Valor | SLO | Estado |", "|---|---|---|---|",
         f"| Acierto@5 de la recuperación (híbrida) | {_pct(m['recuperacion']['hibrido']['acierto@5'])} | ≥ {_pct(slo['acierto@5_hibrido'])} | {ok(m['recuperacion']['hibrido']['acierto@5'] >= slo['acierto@5_hibrido'])} |",
         f"| Tasa de desviación (todos los casos) | {_pct(m['tasa_desviacion'])} | ≤ {_pct(slo['desviacion_max'])} | {ok(m['tasa_desviacion'] <= slo['desviacion_max'])} |",
         f"| Anclaje (afirmaciones respaldadas) | {_pct(m['anclaje'])} | ≥ {_pct(slo['anclaje_min'])} | {ok((m['anclaje'] or 0) >= slo['anclaje_min'])} |",
         f"| Rechazo correcto (no respondibles) | {_pct(m['rechazo_correcto'])} | ≥ {_pct(slo['rechazo_correcto_min'])} | {ok((m['rechazo_correcto'] or 0) >= slo['rechazo_correcto_min'])} |",
         f"| Fragmentos derogados recuperados | {m['violaciones_vigencia']} | {slo['violaciones_vigencia']} | {ok(m['violaciones_vigencia'] == 0)} |",
         "", "## Recuperación por modo (k = 5, casos con fuente esperada)", "",
         "| Modo | Acierto@1 | Acierto@5 | MRR@5 |", "|---|---|---|---|"]
    for modo, r in m["recuperacion"].items():
        L.append(f"| {modo} | {_pct(r['acierto@1'])} | {_pct(r['acierto@5'])} | {r['mrr@5']:.2f} |")
    if m["pertinencia@5"]:
        p = m["pertinencia@5"]
        L += ["", f"Pertinencia@5 (juez `{inf['juez']}`): pertinente {_pct(p['pertinente'])}, parcial {_pct(p['parcial'])}, no pertinente {_pct(p['no_pertinente'])}."]
    L += ["", "## Ablación del filtro de vigencia", "",
          f"- Sin filtro: {m['ablacion_derogados_sin_filtro']} fragmentos derogados entran al top-5 en {m['ablacion_casos_con_derogado_sin_filtro']} casos.",
          f"- Filtro posterior (buscar 5 y descartar): se pierden {m['ablacion_filtro_posterior_resultados_perdidos']} resultados en total.",
          f"- Filtro previo (diseño): {m['violaciones_vigencia']} derogados y ningún resultado perdido.", "",
          f"Latencia de `responder_consulta`: p50 {m['latencia_ms_p50']:.0f} ms, p95 {m['latencia_ms_p95']:.0f} ms.", ""]
    if inf["barrido_umbral"]:
        L += ["## Sensibilidad al umbral de decisión", "", "| Umbral | Respondibles correctos | Rechazo correcto | Desviación |", "|---|---|---|---|"]
        for b in inf["barrido_umbral"]:
            L.append(f"| {b['umbral']} | {_pct(b['respondibles_correctos'])} | {_pct(b['rechazo_correcto'])} | {_pct(b['desviacion'])} |")
        L.append("")
    L += ["## Resultado por caso", "", "| Caso | Tipo | Estado | Rango esperado (h/s/l) | Correcto | Falla |", "|---|---|---|---|---|---|"]
    for c in inf["casos"]:
        rg = "/".join(str(c["recuperacion"][m_]["rango_esperado"] or "–") for m_ in ("hibrido", "semantico", "lexico"))
        L.append(f"| {c['id']} | {c['tipo']} | {c['estado']} | {rg} | {'sí' if c['correcto'] else 'no'} | {'; '.join(c['fallas'])} |")
    return "\n".join(L) + "\n"
