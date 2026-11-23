"""Genera el BPMN 2.0 del Escenario B (.bpmn con diagrama y .svg con la frontera determinista en color).

Uso: python herramientas/generar_bpmn.py
"""
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

SALIDA = Path(__file__).resolve().parents[1] / "docs" / "escenario_b"

LANES = [
    ("L1", "Sistema de balance volumétrico"),
    ("L2", "Orquestador de conciliación (copiloto)"),
    ("L3", "Analista de medición del tramo"),
    ("L4", "Gerencia de Medición"),
    ("L5", "Gerencia de Seguridad Física"),
    ("L6", "Gerencia de Cumplimiento"),
]
X0, COL, LANE_H, POOL_LBL, Y0, ETQ = 150, 132, 124, 30, 40, 112
TAM = {"task": (112, 72), "sub": (124, 84), "event": (36, 36), "gw": (50, 50)}

# id, tipo bpmn, carril, columna, nombre, frontera (D determinista, A agéntico, H humano, -)
NODOS = [
    ("inicio", "timerStartEvent", "L1", 0, "Corte semanal o mensual", "-"),
    ("calcular", "serviceTask", "L1", 1, "Calcular diferencia del tramo [PRO-MED-007 §2]", "D"),
    ("gw_tol", "exclusiveGateway", "L1", 2, "¿|diferencia| ≤ 0,5 %?", "D"),
    ("archivar", "serviceTask", "L1", 3, "Archivar sin investigación [§3.1]", "D"),
    ("fin_archivo", "endEvent", "L1", 4, "Archivado", "-"),
    ("correlacionar", "businessRuleTask", "L2", 3, "Correlacionar con anomalías de presión [PRO-OPE-012 §3.2]", "D"),
    ("gw_sust", "exclusiveGateway", "L2", 4, "¿Sospecha de sustracción?", "D"),
    ("hurto", "callActivity", "L5", 4, "Atender evento de hurto [PRO-SEG-015]", "H"),
    ("fin_hurto", "endEvent", "L5", 5, "Caso trasladado a Seguridad Física", "-"),
    ("gw_esc", "exclusiveGateway", "L2", 5, "¿|diferencia| > 1 %?", "D"),
    ("gw_par", "parallelGateway", "L2", 6, "", "D"),
    ("escalar", "userTask", "L5", 7, "Atender escalamiento el mismo día [§3.3]", "H"),
    ("fin_esc", "endEvent", "L5", 8, "Escalamiento atendido", "-"),
    ("gw_merge", "exclusiveGateway", "L2", 7, "", "D"),
    ("investigar", "subProcess", "L2", 8, "Investigar causas, redactar y validar borrador", "A"),
    ("manual", "userTask", "L3", 9, "Investigar y elaborar acta manualmente", "H"),
    ("revisar", "userTask", "L3", 10, "Revisar y decidir sobre el borrador (≤ 2 min)", "H"),
    ("gw_dec", "exclusiveGateway", "L3", 11, "¿Decisión?", "H"),
    ("registrar", "serviceTask", "L1", 12, "Registrar acta de conciliación (idempotente)", "D"),
    ("cierre", "userTask", "L4", 13, "Aprobar cierre del período [§4]", "H"),
    ("consolidar", "userTask", "L6", 14, "Consolidar reporte mensual de pérdidas [RES-ANH-0471 Art. 3]", "H"),
    ("enviar", "sendTask", "L6", 15, "Enviar reporte al regulador (≤ 15 días)", "H"),
    ("fin", "endEvent", "L6", 16, "Período cerrado y reportado", "-"),
    ("fin_incidente", "endEvent", "L2", 1, "Incidente a plataforma; corte reprogramado", "-"),
]
# bordes: id, carril del borde (adjunto a), nombre, tipo de definición
BORDES = [
    ("b_plazo", "investigar", "3 días hábiles sin borrador aprobado", "timer", 0.30),
    ("b_presupuesto", "investigar", "Presupuesto agotado o evidencia insuficiente", "error", 0.72),
    ("b_balance", "calcular", "Balance no disponible", "error", 0.5),
]
FLUJOS = [
    ("f1", "inicio", "calcular", ""), ("f2", "calcular", "gw_tol", ""),
    ("f3", "gw_tol", "archivar", "sí"), ("f4", "archivar", "fin_archivo", ""),
    ("f5", "gw_tol", "correlacionar", "no"), ("f6", "correlacionar", "gw_sust", ""),
    ("f7", "gw_sust", "hurto", "sí"), ("f8", "hurto", "fin_hurto", ""),
    ("f9", "gw_sust", "gw_esc", "no"),
    ("f10", "gw_esc", "gw_par", "sí"), ("f11", "gw_par", "escalar", ""), ("f12", "escalar", "fin_esc", ""),
    ("f13", "gw_par", "gw_merge", ""), ("f14", "gw_esc", "gw_merge", "no"),
    ("f15", "gw_merge", "investigar", ""), ("f16", "investigar", "revisar", "borrador validado"),
    ("f17", "gw_dec", "registrar", "aprobar"), ("f18", "gw_dec", "gw_merge", "devolver con observaciones"),
    ("f19", "gw_dec", "manual", "rechazar"), ("f20", "revisar", "gw_dec", ""),
    ("f21", "b_plazo", "manual", ""), ("f22", "b_presupuesto", "manual", ""),
    ("f23", "manual", "registrar", "acta firmada por el analista"),
    ("f24", "registrar", "cierre", ""), ("f25", "cierre", "consolidar", ""),
    ("f26", "consolidar", "enviar", ""), ("f27", "enviar", "fin", ""),
    ("f28", "b_balance", "fin_incidente", "reintentos agotados"),
]


def _lane_y(lane: str) -> int:
    i = [l for l, _ in LANES].index(lane)
    return Y0 + i * LANE_H


def _tam(tipo: str):
    if tipo.endswith("Event"):
        return TAM["event"]
    if tipo.endswith("Gateway"):
        return TAM["gw"]
    if tipo == "subProcess":
        return TAM["sub"]
    return TAM["task"]


def geometria():
    g = {}
    for nid, tipo, lane, col, nombre, fr in NODOS:
        w, h = _tam(tipo)
        cx = X0 + POOL_LBL + ETQ + col * COL + COL // 2
        cy = _lane_y(lane) + LANE_H // 2
        g[nid] = {"x": cx - w // 2, "y": cy - h // 2, "w": w, "h": h, "cx": cx, "cy": cy, "tipo": tipo, "nombre": nombre, "fr": fr, "lane": lane}
    for bid, ref, nombre, tdef, frac in BORDES:
        r = g[ref]
        cx = r["x"] + int(r["w"] * frac)
        cy = r["y"] + r["h"]
        g[bid] = {"x": cx - 18, "y": cy - 18, "w": 36, "h": 36, "cx": cx, "cy": cy, "tipo": "boundaryEvent", "nombre": nombre,
                  "fr": "-", "lane": r["lane"], "ref": ref, "tdef": tdef}
    return g


def _puertos(a, b):
    """Ruta ortogonal simple entre dos nodos."""
    if a["tipo"] == "boundaryEvent":
        sx, sy = a["cx"], a["y"] + a["h"]
        return [(sx, sy), (sx, b["cy"]), (b["x"], b["cy"])] if b["cx"] > sx + 10 else [(sx, sy), (sx, b["cy"] - b["h"] // 2), (b["cx"], b["y"])]
    ax2, ay = a["x"] + a["w"], a["cy"]
    if abs(a["cy"] - b["cy"]) < 2:
        if b["cx"] > a["cx"]:
            return [(ax2, ay), (b["x"], b["cy"])]
        # retorno hacia atrás en el mismo carril: por debajo
        yb = _lane_y(a["lane"]) + LANE_H - 10
        return [(a["cx"], a["y"] + a["h"]), (a["cx"], yb), (b["cx"], yb), (b["cx"], b["y"] + b["h"])]
    if b["cx"] > a["cx"] + 5:
        if a["tipo"].endswith("Gateway"):
            sy = a["y"] + a["h"] if b["cy"] > a["cy"] else a["y"]
            return [(a["cx"], sy), (a["cx"], b["cy"]), (b["x"], b["cy"])]
        tx = b["cx"]
        ty = b["y"] if b["cy"] > a["cy"] else b["y"] + b["h"]
        return [(ax2, ay), (tx, ay), (tx, ty)]
    if abs(b["cx"] - a["cx"]) <= 5:
        return [(a["cx"], a["y"] + a["h"] if b["cy"] > a["cy"] else a["y"]), (b["cx"], b["y"] if b["cy"] > a["cy"] else b["y"] + b["h"])]
    # hacia atrás y a otro carril: sale por abajo o arriba y entra por abajo o arriba del destino
    if b["cy"] < a["cy"]:
        ymid = _lane_y(a["lane"]) + 14
        return [(a["cx"], a["y"]), (a["cx"], ymid), (b["cx"] + 6, ymid), (b["cx"] + 6, b["y"] + b["h"])]
    yb = _lane_y(a["lane"]) + LANE_H - 10
    return [(a["cx"], a["y"] + a["h"]), (a["cx"], yb), (b["cx"], yb), (b["cx"], b["y"] + b["h"])]


RUTAS_ESPECIALES = {
    # gw_esc «no» por encima de gw_par hasta la compuerta de unión
    "f14": lambda g: [(g["gw_esc"]["cx"], g["gw_esc"]["y"]), (g["gw_esc"]["cx"], _lane_y("L2") + 16),
                      (g["gw_merge"]["cx"], _lane_y("L2") + 16), (g["gw_merge"]["cx"], g["gw_merge"]["y"])],
    # devolver: desde la decisión por debajo del carril del analista hasta la unión
    # devolver: por la parte alta del carril del analista hasta la unión
    "f18": lambda g: [(g["gw_dec"]["cx"], g["gw_dec"]["y"]), (g["gw_dec"]["cx"], _lane_y("L3") + 12),
                      (g["gw_merge"]["cx"], _lane_y("L3") + 12), (g["gw_merge"]["cx"], g["gw_merge"]["y"] + g["gw_merge"]["h"])],
    "f19": lambda g: [(g["gw_dec"]["cx"], g["gw_dec"]["y"] + g["gw_dec"]["h"]), (g["gw_dec"]["cx"], _lane_y("L3") + LANE_H - 10),
                      (g["manual"]["cx"] - 25, _lane_y("L3") + LANE_H - 10), (g["manual"]["cx"] - 25, g["manual"]["y"] + g["manual"]["h"])],
    "f23": lambda g: [(g["manual"]["cx"] + 25, g["manual"]["y"] + g["manual"]["h"]), (g["manual"]["cx"] + 25, _lane_y("L3") + LANE_H - 26),
                      (g["registrar"]["cx"] - 22, _lane_y("L3") + LANE_H - 26), (g["registrar"]["cx"] - 22, g["registrar"]["y"] + g["registrar"]["h"])],
    "f17": lambda g: [(g["gw_dec"]["x"] + g["gw_dec"]["w"], g["gw_dec"]["cy"]), (g["registrar"]["cx"] + 10, g["gw_dec"]["cy"]),
                      (g["registrar"]["cx"] + 10, g["registrar"]["y"] + g["registrar"]["h"])],
    "f28": lambda g: [(g["b_balance"]["cx"], g["b_balance"]["y"] + 36), (g["b_balance"]["cx"], g["fin_incidente"]["y"])],
    "f21": lambda g: [(g["b_plazo"]["cx"], g["b_plazo"]["y"] + 36), (g["b_plazo"]["cx"], g["manual"]["cy"] - 14), (g["manual"]["x"], g["manual"]["cy"] - 14)],
    "f22": lambda g: [(g["b_presupuesto"]["cx"], g["b_presupuesto"]["y"] + 36), (g["b_presupuesto"]["cx"], g["manual"]["cy"] + 14), (g["manual"]["x"], g["manual"]["cy"] + 14)],
}


def rutas(g):
    r = {}
    for fid, a, b, _ in FLUJOS:
        r[fid] = RUTAS_ESPECIALES[fid](g) if fid in RUTAS_ESPECIALES else _puertos(g[a], g[b])
    return r


def bpmn_xml(g, rt) -> str:
    ancho = X0 + POOL_LBL + ETQ + 17 * COL + 20
    alto_pool = len(LANES) * LANE_H
    pool2_y = Y0 + alto_pool + 40
    inc = {n: [] for n in g}
    sal = {n: [] for n in g}
    for fid, a, b, _ in FLUJOS:
        sal[a].append(fid)
        inc[b].append(fid)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
           'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
           'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'id="Def_conciliacion" targetNamespace="https://petroandes.ejemplo/bpmn/conciliacion" exporter="generar_bpmn.py" exporterVersion="1.0">',
           '  <bpmn:collaboration id="Colab_conciliacion">',
           '    <bpmn:documentation>Gestión de una diferencia de balance volumétrico — Taller 2, Escenario B. Frontera: D determinista, A agéntico, H humano (ver documentation de cada nodo).</bpmn:documentation>',
           '    <bpmn:participant id="P_andes" name="AndesTransporte — conciliación volumétrica del tramo" processRef="Proc_conciliacion"/>',
           '    <bpmn:participant id="P_regulador" name="Regulador sectorial"/>',
           '    <bpmn:messageFlow id="mf_reporte" name="Reporte mensual consolidado" sourceRef="enviar" targetRef="P_regulador"/>',
           '  </bpmn:collaboration>',
           '  <bpmn:message id="Msg_reporte" name="Reporte mensual de pérdidas"/>',
           '  <bpmn:error id="Err_presupuesto" name="Presupuesto agotado" errorCode="PRESUPUESTO_AGOTADO"/>',
           '  <bpmn:error id="Err_balance" name="Balance no disponible" errorCode="BALANCE_NO_DISPONIBLE"/>',
           '  <bpmn:process id="Proc_conciliacion" name="Gestión de una diferencia de balance volumétrico" isExecutable="false">',
           '    <bpmn:laneSet id="LaneSet_1">']
    for lid, nombre in LANES:
        out.append(f'      <bpmn:lane id="{lid}" name="{escape(nombre)}">')
        for nid, d in g.items():
            if d["lane"] == lid:
                out.append(f'        <bpmn:flowNodeRef>{nid}</bpmn:flowNodeRef>')
        out.append('      </bpmn:lane>')
    out.append('    </bpmn:laneSet>')
    fr_txt = {"D": "Frontera: DETERMINISTA", "A": "Frontera: AGÉNTICO", "H": "Frontera: HUMANO", "-": "Evento"}
    for nid, d in g.items():
        t = d["tipo"]
        nombre = escape(d["nombre"])
        hijos = [f'      <bpmn:documentation>{fr_txt[d["fr"]]}</bpmn:documentation>']
        hijos += [f'      <bpmn:incoming>{f}</bpmn:incoming>' for f in inc[nid]]
        hijos += [f'      <bpmn:outgoing>{f}</bpmn:outgoing>' for f in sal[nid]]
        if t == "timerStartEvent":
            out.append(f'    <bpmn:startEvent id="{nid}" name="{nombre}">')
            out += hijos + ['      <bpmn:timerEventDefinition id="td_inicio"><bpmn:timeCycle xsi:type="bpmn:tFormalExpression">R/P1W</bpmn:timeCycle></bpmn:timerEventDefinition>', '    </bpmn:startEvent>']
        elif t == "boundaryEvent":
            cancel = "true"
            out.append(f'    <bpmn:boundaryEvent id="{nid}" name="{nombre}" attachedToRef="{d["ref"]}" cancelActivity="{cancel}">')
            out += hijos
            if d["tdef"] == "timer":
                out.append(f'      <bpmn:timerEventDefinition id="td_{nid}"><bpmn:timeDuration xsi:type="bpmn:tFormalExpression">P3D</bpmn:timeDuration></bpmn:timerEventDefinition>')
            else:
                ref = "Err_presupuesto" if "presupuesto" in nid else "Err_balance"
                out.append(f'      <bpmn:errorEventDefinition id="ed_{nid}" errorRef="{ref}"/>')
            out.append('    </bpmn:boundaryEvent>')
        elif t == "sendTask":
            out.append(f'    <bpmn:sendTask id="{nid}" name="{nombre}" messageRef="Msg_reporte">')
            out += hijos + ['    </bpmn:sendTask>']
        elif t == "subProcess":
            out.append(f'    <bpmn:subProcess id="{nid}" name="{nombre}">')
            out += hijos
            out += ['      <bpmn:startEvent id="sp_inicio"><bpmn:outgoing>sf1</bpmn:outgoing></bpmn:startEvent>',
                    '      <bpmn:serviceTask id="sp_contexto" name="Cargar contexto del caso (balance, mediciones, OT, procedimientos vigentes)"><bpmn:documentation>Frontera: DETERMINISTA</bpmn:documentation><bpmn:incoming>sf1</bpmn:incoming><bpmn:outgoing>sf2</bpmn:outgoing></bpmn:serviceTask>',
                    '      <bpmn:task id="sp_investigar" name="Investigar causas plausibles (bucle con herramientas de lectura)"><bpmn:documentation>Frontera: AGÉNTICO</bpmn:documentation><bpmn:incoming>sf2</bpmn:incoming><bpmn:incoming>sf6</bpmn:incoming><bpmn:outgoing>sf3</bpmn:outgoing></bpmn:task>',
                    '      <bpmn:task id="sp_redactar" name="Redactar borrador con citas"><bpmn:documentation>Frontera: AGÉNTICO</bpmn:documentation><bpmn:incoming>sf3</bpmn:incoming><bpmn:outgoing>sf4</bpmn:outgoing></bpmn:task>',
                    '      <bpmn:serviceTask id="sp_validar" name="Validar cifras y citas del borrador"><bpmn:documentation>Frontera: DETERMINISTA</bpmn:documentation><bpmn:incoming>sf4</bpmn:incoming><bpmn:outgoing>sf5</bpmn:outgoing></bpmn:serviceTask>',
                    '      <bpmn:exclusiveGateway id="sp_gw" name="¿Válido?"><bpmn:incoming>sf5</bpmn:incoming><bpmn:outgoing>sf6</bpmn:outgoing><bpmn:outgoing>sf7</bpmn:outgoing></bpmn:exclusiveGateway>',
                    '      <bpmn:endEvent id="sp_fin" name="Borrador validado"><bpmn:incoming>sf7</bpmn:incoming></bpmn:endEvent>',
                    '      <bpmn:sequenceFlow id="sf1" sourceRef="sp_inicio" targetRef="sp_contexto"/>',
                    '      <bpmn:sequenceFlow id="sf2" sourceRef="sp_contexto" targetRef="sp_investigar"/>',
                    '      <bpmn:sequenceFlow id="sf3" sourceRef="sp_investigar" targetRef="sp_redactar"/>',
                    '      <bpmn:sequenceFlow id="sf4" sourceRef="sp_redactar" targetRef="sp_validar"/>',
                    '      <bpmn:sequenceFlow id="sf5" sourceRef="sp_validar" targetRef="sp_gw"/>',
                    '      <bpmn:sequenceFlow id="sf6" name="no (máx. 2 reintentos)" sourceRef="sp_gw" targetRef="sp_investigar"/>',
                    '      <bpmn:sequenceFlow id="sf7" name="sí" sourceRef="sp_gw" targetRef="sp_fin"/>',
                    '    </bpmn:subProcess>']
        else:
            out.append(f'    <bpmn:{t} id="{nid}" name="{nombre}">')
            out += hijos + [f'    </bpmn:{t}>']
    for fid, a, b, nombre in FLUJOS:
        n = f' name="{escape(nombre)}"' if nombre else ""
        out.append(f'    <bpmn:sequenceFlow id="{fid}"{n} sourceRef="{a}" targetRef="{b}"/>')
    out.append('  </bpmn:process>')
    out += ['  <bpmndi:BPMNDiagram id="Diag_1">', '    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Colab_conciliacion">',
            f'      <bpmndi:BPMNShape id="P_andes_di" bpmnElement="P_andes" isHorizontal="true"><dc:Bounds x="{X0}" y="{Y0}" width="{ancho - X0}" height="{alto_pool}"/></bpmndi:BPMNShape>']
    for lid, _ in LANES:
        out.append(f'      <bpmndi:BPMNShape id="{lid}_di" bpmnElement="{lid}" isHorizontal="true"><dc:Bounds x="{X0 + POOL_LBL}" y="{_lane_y(lid)}" width="{ancho - X0 - POOL_LBL}" height="{LANE_H}"/></bpmndi:BPMNShape>')
    out.append(f'      <bpmndi:BPMNShape id="P_regulador_di" bpmnElement="P_regulador" isHorizontal="true"><dc:Bounds x="{X0}" y="{pool2_y}" width="{ancho - X0}" height="70"/></bpmndi:BPMNShape>')
    for nid, d in g.items():
        extra = ' isMarkerVisible="true"' if d["tipo"] == "exclusiveGateway" else ""
        exp = ' isExpanded="false"' if d["tipo"] == "subProcess" else ""
        out.append(f'      <bpmndi:BPMNShape id="{nid}_di" bpmnElement="{nid}"{extra}{exp}><dc:Bounds x="{d["x"]}" y="{d["y"]}" width="{d["w"]}" height="{d["h"]}"/></bpmndi:BPMNShape>')
    for fid, pts in rt.items():
        wps = "".join(f'<di:waypoint x="{x}" y="{y}"/>' for x, y in pts)
        out.append(f'      <bpmndi:BPMNEdge id="{fid}_di" bpmnElement="{fid}">{wps}</bpmndi:BPMNEdge>')
    e = g["enviar"]
    out.append(f'      <bpmndi:BPMNEdge id="mf_reporte_di" bpmnElement="mf_reporte"><di:waypoint x="{e["cx"]}" y="{e["y"] + e["h"]}"/><di:waypoint x="{e["cx"]}" y="{pool2_y}"/></bpmndi:BPMNEdge>')
    out += ['    </bpmndi:BPMNPlane>', '  </bpmndi:BPMNDiagram>', '</bpmn:definitions>']
    return "\n".join(out) + "\n"


COLOR = {"D": ("#DCE9F7", "#2F6DB5"), "A": ("#FCE6D2", "#C8641E"), "H": ("#DFF0DD", "#3C8A3A"), "-": ("#FFFFFF", "#333333")}


def _texto(cx, cy, txt, ancho_max=100, tam=10.5, peso="normal", color="#1E1E1E"):
    palabras, lineas, actual = txt.split(), [], ""
    for p in palabras:
        if len(actual + " " + p) * tam * 0.52 > ancho_max and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = (actual + " " + p).strip()
    if actual:
        lineas.append(actual)
    y0 = cy - (len(lineas) - 1) * tam * 0.6
    return "".join(f'<text x="{cx}" y="{y0 + i * tam * 1.2:.1f}" font-size="{tam}" font-weight="{peso}" fill="{color}" text-anchor="middle" dominant-baseline="middle">{escape(l)}</text>' for i, l in enumerate(lineas))


def svg(g, rt) -> str:
    ancho = X0 + POOL_LBL + ETQ + 17 * COL + 20
    alto_pool = len(LANES) * LANE_H
    pool2_y = Y0 + alto_pool + 40
    W, H = ancho + 20, pool2_y + 70 + 70
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Liberation Sans, Arial, sans-serif">',
         '<defs><marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker>'
         '<marker id="flecha_m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#fff" stroke="#333"/></marker></defs>',
         f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>',
         f'<text x="{X0}" y="24" font-size="16" font-weight="bold">Gestión de una diferencia de balance volumétrico — BPMN 2.0 (Escenario B)</text>',
         f'<rect x="{X0}" y="{Y0}" width="{ancho - X0}" height="{alto_pool}" fill="none" stroke="#333" stroke-width="1.5"/>',
         f'<line x1="{X0 + POOL_LBL}" y1="{Y0}" x2="{X0 + POOL_LBL}" y2="{Y0 + alto_pool}" stroke="#333"/>',
         f'<text transform="translate({X0 + 19},{Y0 + alto_pool / 2}) rotate(-90)" font-size="12" font-weight="bold" text-anchor="middle">AndesTransporte — conciliación del tramo</text>']
    for i, (lid, nombre) in enumerate(LANES):
        y = _lane_y(lid)
        if i:
            s.append(f'<line x1="{X0 + POOL_LBL}" y1="{y}" x2="{ancho}" y2="{y}" stroke="#888"/>')
        s.append(f'<rect x="{X0 + POOL_LBL}" y="{y}" width="110" height="{LANE_H}" fill="#F6F6F6" stroke="none"/>')
        s.append(_texto(X0 + POOL_LBL + 55, y + LANE_H / 2, nombre, 100, 10.5, "bold"))
        s.append(f'<line x1="{X0 + POOL_LBL + 110}" y1="{y}" x2="{X0 + POOL_LBL + 110}" y2="{y + LANE_H}" stroke="#CCC"/>')
    s.append(f'<rect x="{X0}" y="{pool2_y}" width="{ancho - X0}" height="70" fill="#F6F6F6" stroke="#333" stroke-width="1.5"/>')
    s.append(f'<text x="{X0 + (ancho - X0) / 2}" y="{pool2_y + 38}" font-size="13" font-weight="bold" text-anchor="middle">Regulador sectorial (participante externo)</text>')
    etiquetas = {fid: n for fid, _, _, n in FLUJOS}
    for fid, pts in rt.items():
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        s.append(f'<path d="{d}" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#flecha)"/>')
        if etiquetas[fid]:
            (x1, y1), (x2, y2) = pts[0], pts[1]
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            if len(pts) > 2 and abs(x1 - x2) < 2:
                (x1, y1), (x2, y2) = pts[1], pts[2]
                lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            s.append(f'<rect x="{lx - len(etiquetas[fid]) * 2.7 - 3}" y="{ly - 16}" width="{len(etiquetas[fid]) * 5.4 + 6}" height="13" fill="#FFFFFF" opacity="0.9"/>')
            s.append(f'<text x="{lx}" y="{ly - 6}" font-size="9.5" fill="#444" text-anchor="middle">{escape(etiquetas[fid])}</text>')
    e = g["enviar"]
    s.append(f'<path d="M{e["cx"]},{e["y"] + e["h"]} L{e["cx"]},{pool2_y}" fill="none" stroke="#333" stroke-dasharray="6,4" marker-end="url(#flecha_m)"/>')
    s.append(f'<circle cx="{e["cx"]}" cy="{e["y"] + e["h"] + 6}" r="4" fill="#fff" stroke="#333"/>')
    s.append(f'<text x="{e["cx"] + 8}" y="{pool2_y - 12}" font-size="9.5" fill="#444">Reporte mensual consolidado</text>')
    for nid, d in g.items():
        fill, stroke = COLOR[d["fr"]]
        t = d["tipo"]
        if t.endswith("Event") or t == "boundaryEvent":
            r = 18
            sw = 3.5 if t == "endEvent" else 1.6
            s.append(f'<circle cx="{d["cx"]}" cy="{d["cy"]}" r="{r}" fill="#FFF" stroke="#333" stroke-width="{sw}"/>')
            if t == "boundaryEvent":
                s.append(f'<circle cx="{d["cx"]}" cy="{d["cy"]}" r="{r - 3}" fill="none" stroke="#333" stroke-width="1"/>')
            if t == "timerStartEvent" or d.get("tdef") == "timer":
                s.append(f'<circle cx="{d["cx"]}" cy="{d["cy"]}" r="10" fill="none" stroke="#333"/><path d="M{d["cx"]},{d["cy"]} L{d["cx"]},{d["cy"] - 7} M{d["cx"]},{d["cy"]} L{d["cx"] + 5},{d["cy"]}" stroke="#333"/>')
            if d.get("tdef") == "error":
                s.append(f'<path d="M{d["cx"] - 7},{d["cy"] + 7} L{d["cx"] - 3},{d["cy"] - 6} L{d["cx"] + 2},{d["cy"] + 2} L{d["cx"] + 7},{d["cy"] - 7}" fill="none" stroke="#333" stroke-width="1.5"/>')
            ly, lx = d["cy"] + 36, d["cx"]
            if t == "boundaryEvent":
                lx, ly = {"b_plazo": (d["cx"] - 70, d["cy"] + 8), "b_presupuesto": (d["cx"] + 92, d["cy"] - 4),
                          "b_balance": (d["cx"] - 80, d["cy"] + 4)}[nid]
            s.append(_texto(lx, ly, d["nombre"], 110, 9.5, color="#333"))
        elif t.endswith("Gateway"):
            cx, cy = d["cx"], d["cy"]
            s.append(f'<polygon points="{cx},{cy - 25} {cx + 25},{cy} {cx},{cy + 25} {cx - 25},{cy}" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
            if t == "parallelGateway":
                s.append(f'<path d="M{cx - 11},{cy} L{cx + 11},{cy} M{cx},{cy - 11} L{cx},{cy + 11}" stroke="#333" stroke-width="3"/>')
            else:
                s.append(f'<path d="M{cx - 8},{cy - 8} L{cx + 8},{cy + 8} M{cx + 8},{cy - 8} L{cx - 8},{cy + 8}" stroke="#333" stroke-width="3"/>')
            if d["nombre"]:
                s.append(_texto(cx, cy - 38, d["nombre"], 120, 9.5, color="#333"))
        else:
            sw = 2.6 if t == "callActivity" else 1.6
            s.append(f'<rect x="{d["x"]}" y="{d["y"]}" width="{d["w"]}" height="{d["h"]}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            s.append(_texto(d["cx"], d["cy"], d["nombre"], d["w"] - 12, 9.8))
            ico = {"serviceTask": "⚙", "userTask": "👤", "businessRuleTask": "▦", "sendTask": "✉"}.get(t)
            if ico:
                s.append(f'<text x="{d["x"] + 6}" y="{d["y"] + 14}" font-size="11" fill="{stroke}">{ico}</text>')
            if t == "subProcess":
                s.append(f'<rect x="{d["cx"] - 7}" y="{d["y"] + d["h"] - 15}" width="14" height="13" fill="#FFF" stroke="#333"/><path d="M{d["cx"] - 4},{d["y"] + d["h"] - 8.5} L{d["cx"] + 4},{d["y"] + d["h"] - 8.5} M{d["cx"]},{d["y"] + d["h"] - 12.5} L{d["cx"]},{d["y"] + d["h"] - 4.5}" stroke="#333"/>')
    ly = pool2_y + 92
    s.append(f'<text x="{X0}" y="{ly}" font-size="11" font-weight="bold">Frontera:</text>')
    for i, (k, txt) in enumerate([("D", "determinista (código)"), ("A", "agéntico (modelo con herramientas de lectura)"), ("H", "humano")]):
        fill, stroke = COLOR[k]
        x = X0 + 70 + i * 290
        s.append(f'<rect x="{x}" y="{ly - 11}" width="26" height="14" rx="3" fill="{fill}" stroke="{stroke}"/><text x="{x + 34}" y="{ly}" font-size="11">{txt}</text>')
    s.append("</svg>")
    return "".join(s)


def main():
    g = geometria()
    rt = rutas(g)
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "conciliacion_volumetrica.bpmn").write_text(bpmn_xml(g, rt), encoding="utf-8")
    (SALIDA / "conciliacion_volumetrica.svg").write_text(svg(g, rt), encoding="utf-8")
    print("BPMN y SVG generados en", SALIDA)


if __name__ == "__main__":
    main()
