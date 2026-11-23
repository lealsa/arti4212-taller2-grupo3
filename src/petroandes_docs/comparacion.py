"""Comparación de las estrategias de decisión de ADR-008 con el mismo conjunto y el mismo juez."""
from __future__ import annotations

import gc
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .composicion import Estrategia, componer
from .evaluacion import _fid, fallas_del_caso

DESCRIPCION = {
    "A0": "Cobertura léxica (sin modelo en la decisión)",
    "A0G": "Ablación: A0 + guarda de entidades (sin modelo)",
    "A1": "LLM local interpreta la pregunta + cobertura léxica + guarda de entidades",
    "A2r1": "Decisor local (cross-encoder) + guarda; hasta 3 frases cercanas (ronda 1)",
    "A2md": "Decisor local + guarda; frases adicionales solo del mismo documento (ronda 2)",
    "A2": "Decisor local + guarda + una sola frase (ronda 3, elegida)",
    "A3": "Cadena: LLM amplía la búsqueda + decisor local + guarda + una sola frase",
}


def _categoria(fallas: list[str]) -> str:
    if not fallas:
        return "correcta"
    t = " ".join(fallas)
    if "respondió una pregunta que no está" in t or "valores prohibidos" in t:
        return "indebida"
    if "se negó" in t:
        return "negativa_de_mas"
    return "errada"


def evaluar(ix, casos: list[dict], est: Estrategia, juez=None) -> list[dict]:
    salida = []
    for caso in casos:
        fecha = caso.get("fecha_referencia")
        esperados = [_fid(f) for f in caso.get("fuentes", [])]
        t0 = time.perf_counter()
        r = componer(ix, caso["pregunta"], fecha_referencia=fecha, estrategia=est)
        lat = (time.perf_counter() - t0) * 1000
        fallas = fallas_del_caso(caso, r, esperados)
        fila = {"id": caso["id"], "tipo": caso["tipo"], "pregunta": caso["pregunta"], "estado": r.estado,
                "afirmaciones": [{"texto": a.texto, "cita": a.cita, "puntaje": a.cobertura} for a in r.afirmaciones],
                "fallas": fallas, "categoria": _categoria(fallas), "latencia_ms": round(lat, 1),
                "interpretacion": r.interpretacion,
                "rango_esperado": next((c["rango"] for c in r.consultados if c["id"] in esperados), None),
                "descartadas_por_guarda": r.parametros.get("unidades_descartadas_por_guarda", 0)}
        if juez is not None:
            fila["anclaje"] = [juez.anclaje(a.texto, (ix.fragmento(a.codigo, a.version, a.seccion) or {}).get("texto", ""))
                               for a in r.afirmaciones]
            if r.afirmaciones:
                fila["responde"] = juez.responde(caso["pregunta"], " ".join(a.texto for a in r.afirmaciones))
            if r.interpretacion:
                fila["fidelidad"] = juez.equivalente(caso["pregunta"], r.interpretacion["reescritura"])
        salida.append(fila)
    return salida


def _media(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def metricas(filas: list[dict]) -> dict:
    n = len(filas)
    cat = [f["categoria"] for f in filas]
    resp = [f for f in filas if f["tipo"] != "no_respondible"]
    rech = [f for f in filas if f["tipo"] == "no_respondible"]
    lat = sorted(f["latencia_ms"] for f in filas)
    anc = [a for f in filas for a in f.get("anclaje", []) if a is not None]
    res = [f["responde"] for f in filas if f.get("responde") is not None]
    fid = [f["fidelidad"] for f in filas if f.get("fidelidad") is not None]
    interp = [f["interpretacion"] for f in filas if f["interpretacion"]]
    return {
        "casos": n, "correctos": cat.count("correcta"), "desviacion": 1 - cat.count("correcta") / n,
        "negativas_de_mas": cat.count("negativa_de_mas"), "indebidas": cat.count("indebida"), "erradas": cat.count("errada"),
        "respondibles_correctos": sum(f["categoria"] == "correcta" for f in resp) / len(resp) if resp else None,
        "rechazo_correcto": sum(f["categoria"] == "correcta" for f in rech) / len(rech) if rech else None,
        "anclaje": sum(a >= 0.5 for a in anc) / len(anc) if anc else None, "anclaje_promedio": _media(anc),
        "responde": sum(r >= 0.5 for r in res) / len(res) if res else None,
        "fidelidad": sum(x >= 0.5 for x in fid) / len(fid) if fid else None,
        "reescrituras": len(interp), "reescrituras_descartadas": sum(not i["aceptada"] for i in interp),
        "latencia_ms_p50": lat[n // 2], "latencia_ms_p95": lat[min(n - 1, int(0.95 * n))],
    }


def barrido(ix, casos: list[dict], est: Estrategia, umbrales) -> list[dict]:
    """Sensibilidad al umbral, sin juez (los modelos de A1 y A2 tienen caché: no se recalculan)."""
    out = []
    for u in umbrales:
        e = Estrategia(est.nombre, est.decisor, est.interprete, u, est.guarda, est.adicionales, est.max_afirmaciones)
        m = metricas(evaluar(ix, casos, e))
        out.append({"umbral": u, **{k: m[k] for k in ("desviacion", "negativas_de_mas", "indebidas", "erradas",
                                                      "respondibles_correctos", "rechazo_correcto")}})
    return out


def ejecutar(ix, conjuntos: dict[str, Path], fabricas: dict[str, callable], juez, salida: Path) -> dict:
    """`fabricas`: nombre -> función que construye la Estrategia (los modelos se cargan uno a la vez)."""
    datos = {nombre: yaml.safe_load(p.read_text(encoding="utf-8"))["casos"] for nombre, p in conjuntos.items()}
    informe = {"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "juez": getattr(juez, "nombre", None), "huella_modelo": ix.embedder.huella,
               "estrategias": {}}
    for nombre, fabrica in fabricas.items():
        t0 = time.perf_counter()
        est = fabrica()
        carga = time.perf_counter() - t0
        bloque = {"descripcion": DESCRIPCION.get(nombre, nombre), "umbral": est.umbral if est.umbral is not None else ix.cfg.umbral_cobertura,
                  "decisor": getattr(est.decisor, "nombre", "cobertura"),
                  "interprete": getattr(est.interprete, "nombre", None), "guarda": est.guarda,
                  "adicionales": est.adicionales,
                  "carga_modelos_s": round(carga, 1), "conjuntos": {}}
        for cj, casos in datos.items():
            filas = evaluar(ix, casos, est, juez)
            umbrales = (0.3, 0.4, 0.5, 0.6, 0.7) if est.decisor is None else (0.1, 0.2, 0.3, 0.5, 0.7, 0.9)
            bloque["conjuntos"][cj] = {"metricas": metricas(filas), "barrido": barrido(ix, casos, est, umbrales),
                                       "casos": filas}
        informe["estrategias"][nombre] = bloque
        del est
        gc.collect()
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "comparacion.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1), encoding="utf-8")
    (salida / "comparacion.md").write_text(reporte_md(informe), encoding="utf-8")
    return informe


def _p(x):
    return "—" if x is None else f"{100 * x:.0f} %"


def reporte_md(inf: dict) -> str:
    E = inf["estrategias"]
    conjuntos = list(next(iter(E.values()))["conjuntos"])
    L = [f"# Comparación de estrategias de decisión — {inf['fecha']}", "",
         f"- Juez: `{inf['juez']}` · Embeddings: `{inf['huella_modelo']}`", ""]
    L += ["| Estrategia | Descripción | Decisor | Intérprete | Umbral | Carga de modelos |", "|---|---|---|---|---|---|"]
    for n, b in E.items():
        L.append(f"| {n} | {b['descripcion']} | `{b['decisor']}` | `{b['interprete'] or '—'}` | {b['umbral']} | {b['carga_modelos_s']} s |")
    for cj in conjuntos:
        L += ["", f"## Conjunto «{cj}»", "",
              "| Métrica | " + " | ".join(E) + " |", "|---|" + "---|" * len(E)]
        filas = [("Correctos", lambda m: f"{m['correctos']} de {m['casos']}"),
                 ("Desviación", lambda m: _p(m["desviacion"])),
                 ("Negativas de más (error seguro)", lambda m: str(m["negativas_de_mas"])),
                 ("Respuestas indebidas: fuera del corpus o valor prohibido (error peligroso)", lambda m: str(m["indebidas"])),
                 ("Respuestas erradas: otro dato u otra cita", lambda m: str(m["erradas"])),
                 ("Rechazo correcto (no respondibles)", lambda m: _p(m["rechazo_correcto"])),
                 ("Anclaje (juez)", lambda m: _p(m["anclaje"])),
                 ("Responde la pregunta (juez)", lambda m: _p(m["responde"])),
                 ("Fidelidad de la reescritura (juez)", lambda m: _p(m["fidelidad"])),
                 ("Reescrituras descartadas por la guarda", lambda m: f"{m['reescrituras_descartadas']} de {m['reescrituras']}" if m["reescrituras"] else "—"),
                 ("Latencia p50 / p95", lambda m: f"{m['latencia_ms_p50']:.0f} / {m['latencia_ms_p95']:.0f} ms")]
        for etiqueta, f in filas:
            L.append(f"| {etiqueta} | " + " | ".join(f(b["conjuntos"][cj]["metricas"]) for b in E.values()) + " |")
        L += ["", "Por caso (✓ correcta · N negativa de más · ! indebida · ✗ errada):", "",
              "| Caso | Tipo | " + " | ".join(E) + " |", "|---|---|" + "---|" * len(E)]
        simb = {"correcta": "✓", "negativa_de_mas": "N", "indebida": "!", "errada": "✗"}
        ids = [c["id"] for c in next(iter(E.values()))["conjuntos"][cj]["casos"]]
        for i, cid in enumerate(ids):
            tipo = next(iter(E.values()))["conjuntos"][cj]["casos"][i]["tipo"]
            L.append(f"| {cid} | {tipo} | " + " | ".join(simb[b["conjuntos"][cj]["casos"][i]["categoria"]] for b in E.values()) + " |")
        for n, b in E.items():
            L += ["", f"Sensibilidad al umbral — {n} ({cj}):", "", "| Umbral | Desviación | Negativas de más | Indebidas | Erradas |", "|---|---|---|---|---|"]
            for x in b["conjuntos"][cj]["barrido"]:
                L.append(f"| {x['umbral']} | {_p(x['desviacion'])} | {x['negativas_de_mas']} | {x['indebidas']} | {x['erradas']} |")
    interp = [(cj, c) for cj in conjuntos for c in E.get("A1", {}).get("conjuntos", {}).get(cj, {}).get("casos", []) if c["interpretacion"]]
    if interp:
        L += ["", "## Reescrituras de A1", "", "| Caso | Pregunta | Reescritura | Guarda |", "|---|---|---|---|"]
        for cj, c in interp:
            i = c["interpretacion"]
            L.append(f"| {c['id']} | {c['pregunta']} | {i['reescritura']} | {'aceptada' if i['aceptada'] else i['motivo']} |")
    return "\n".join(L) + "\n"
