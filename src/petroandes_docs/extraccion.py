"""Extracción de PDF al modelo canónico: cabecera, secciones por tipografía y tablas como filas «columna: valor»."""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

import pdfplumber

from .modelos import DocumentoExtraido, Seccion
from .texto import normalizar_espacios

ETIQUETAS = ["Código", "Versión", "Fecha de emisión", "Tipo", "Área emisora", "Activo / alcance", "Reemplaza a"]
CLAVES = {"Código": "codigo", "Versión": "version", "Fecha de emisión": "fecha_emision", "Tipo": "tipo",
          "Área emisora": "area_emisora", "Activo / alcance": "activo", "Reemplaza a": "reemplaza_a"}
PIE = re.compile(r"^(Documento sintético de uso académico|Página \d+$)")
VINETA = re.compile(r"^(•|\(cid:127\)|-)\s*")
CLAUSULA = re.compile(r"^\d+\.\d+\s")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _limpiar(t: str) -> str:
    return normalizar_espacios(t.replace("(cid:127)", "•"))


def _es_negrita(fontname: str) -> bool:
    return "bold" in fontname.lower()


def _elementos(pdf: pdfplumber.PDF) -> list[dict]:
    """Líneas de texto y tablas en orden de lectura, con su tipografía."""
    elementos: list[dict] = []
    for npag, page in enumerate(pdf.pages, start=1):
        tablas = page.find_tables()
        cajas = [t.bbox for t in tablas]

        def fuera_de_tablas(obj, cajas=cajas):
            if obj.get("object_type") != "char":
                return True
            cx, cy = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
            return not any(x0 <= cx <= x1 and t0 <= cy <= t1 for x0, t0, x1, t1 in cajas)

        libre = page.filter(fuera_de_tablas)
        palabras = libre.extract_words(extra_attrs=["fontname", "size"], keep_blank_chars=False, use_text_flow=True)
        lineas: dict[int, list[dict]] = {}
        for w in palabras:
            clave = round(w["top"] / 3)
            lineas.setdefault(clave, []).append(w)
        for _, ws in sorted(lineas.items()):
            ws.sort(key=lambda w: w["x0"])
            texto = _limpiar(" ".join(w["text"] for w in ws))
            if not texto or PIE.match(texto):
                continue
            elementos.append({
                "tipo": "linea", "pagina": npag, "top": ws[0]["top"], "bottom": max(w["bottom"] for w in ws),
                "texto": texto, "negrita": all(_es_negrita(w["fontname"]) for w in ws),
                "tamano": round(max(w["size"] for w in ws), 1),
            })
        for t in tablas:
            filas = [[_limpiar(c or "") for c in fila] for fila in t.extract()]
            filas = [f for f in filas if any(f)]
            if filas:
                elementos.append({"tipo": "tabla", "pagina": npag, "top": t.bbox[1], "bottom": t.bbox[3], "filas": filas})
    elementos.sort(key=lambda e: (e["pagina"], e["top"]))
    return elementos


def _cabecera_desde_texto(texto: str) -> dict:
    """Cabecera sin tabla dibujada: separa los valores por las etiquetas conocidas."""
    posiciones = []
    for et in ETIQUETAS:
        m = re.search(re.escape(et) + r"\s", texto)
        if m:
            posiciones.append((m.start(), m.end(), et))
    posiciones.sort()
    meta = {}
    for i, (_, fin, et) in enumerate(posiciones):
        siguiente = posiciones[i + 1][0] if i + 1 < len(posiciones) else len(texto)
        meta[CLAVES[et]] = normalizar_espacios(texto[fin:siguiente])
    return meta


def _cabecera_desde_tabla(filas: list[list[str]]) -> dict:
    meta = {}
    for fila in filas:
        celdas = [c for c in fila]
        for i in range(0, len(celdas) - 1, 2):
            et, val = celdas[i], celdas[i + 1]
            if et in CLAVES:
                meta[CLAVES[et]] = val
    return meta


def _id_seccion(titulo: str) -> str:
    m = re.match(r"^(\d+)\.\s", titulo)
    if m:
        return m.group(1)
    m = re.match(r"^Art[íi]culo\s+(\d+)", titulo, re.IGNORECASE)
    if m:
        return f"Art. {m.group(1)}"
    return titulo.split(" — ")[0].strip()


def _filas_autocontenidas(filas: list[list[str]]) -> list[str]:
    """Cada fila de datos lleva consigo los nombres de columna."""
    if len(filas) < 2:
        return [" · ".join(c for c in filas[0] if c)] if filas else []
    cab = filas[0]
    salida = []
    for fila in filas[1:]:
        pares = [f"{cab[i]}: {v}" for i, v in enumerate(fila) if v and i < len(cab)]
        salida.append("; ".join(pares) + ".")
    return salida


def extraer_pdf(path: Path) -> DocumentoExtraido:
    with pdfplumber.open(path) as pdf:
        elems = _elementos(pdf)

    # 1. Cabecera: lo que precede a la tabla de metadatos (emisor + título) y la tabla misma.
    idx_tabla = next((i for i, e in enumerate(elems) if e["tipo"] == "tabla"
                      and any("Código" in c for f in e["filas"] for c in f)), None)
    if idx_tabla is not None:
        previas = [e["texto"] for e in elems[:idx_tabla] if e["tipo"] == "linea"]
        meta = _cabecera_desde_tabla(elems[idx_tabla]["filas"])
        cuerpo = elems[idx_tabla + 1:]
        texto_titulo = " ".join(previas)
    else:  # PDF sin tabla dibujada: la cabecera es texto plano hasta «Activo / alcance» o «Reemplaza a»
        lineas = [e for e in elems if e["tipo"] == "linea"]
        i_cod = next(i for i, e in enumerate(lineas) if e["texto"].startswith("Código"))
        i_fin = i_cod
        for j in range(i_cod, min(i_cod + 8, len(lineas))):
            if re.match(r"^(Código|Fecha de emisión|Área emisora|Reemplaza a)", lineas[j]["texto"]) or (
                    j > i_cod and not lineas[j]["negrita"] and j == i_fin + 1 and not re.match(r"^\d+\.", lineas[j]["texto"])
                    and lineas[j - 1]["texto"].startswith("Área emisora")):
                i_fin = j
        meta = _cabecera_desde_texto(" ".join(l["texto"] for l in lineas[i_cod:i_fin + 1]))
        texto_titulo = " ".join(l["texto"] for l in lineas[:i_cod])
        tope = lineas[i_fin]
        cuerpo = [e for e in elems if (e["pagina"], e["top"]) > (tope["pagina"], tope["top"])]

    palabras = texto_titulo.split()
    k = 0
    while k < len(palabras) and palabras[k] == palabras[k].upper() and re.search(r"[A-ZÁÉÍÓÚÑ]", palabras[k]):
        k += 1
    emisor, titulo = " ".join(palabras[:k]), " ".join(palabras[k:])

    # 2. Cuerpo: títulos de sección = líneas en negrita con tamaño mayor o igual al del cuerpo.
    tam_cuerpo = Counter(e["tamano"] for e in cuerpo if e["tipo"] == "linea" and not e["negrita"]).most_common(1)
    tam_cuerpo = tam_cuerpo[0][0] if tam_cuerpo else 0
    secciones: list[Seccion] = []
    actual: Seccion | None = None
    parrafo: list[str] = []
    ultimo_bottom = None

    def cerrar_parrafo():
        nonlocal parrafo
        if actual is not None and parrafo:
            actual.unidades.append(normalizar_espacios(" ".join(parrafo)))
        parrafo = []

    for e in cuerpo:
        if e["tipo"] == "linea" and e["negrita"] and e["tamano"] >= tam_cuerpo:
            cerrar_parrafo()
            actual = Seccion(id=_id_seccion(e["texto"]), titulo=e["texto"], texto="", pagina=e["pagina"])
            secciones.append(actual)
            ultimo_bottom = e["bottom"]
            continue
        if actual is None:
            continue
        if e["tipo"] == "tabla":
            cerrar_parrafo()
            actual.unidades.extend(_filas_autocontenidas(e["filas"]))
            ultimo_bottom = e["bottom"]
            continue
        txt = e["texto"]
        nuevo = (VINETA.match(txt) or CLAUSULA.match(txt)
                 or (ultimo_bottom is not None and e["top"] - ultimo_bottom > 0.6 * e["tamano"]))
        if nuevo:
            cerrar_parrafo()
        parrafo.append(VINETA.sub("", txt) if VINETA.match(txt) else txt)
        ultimo_bottom = e["bottom"]
    cerrar_parrafo()
    for s in secciones:
        s.texto = "\n".join(s.unidades)

    version = meta.get("version", "—").strip() or "—"
    return DocumentoExtraido(
        codigo=meta.get("codigo", "").strip(), version=version, titulo=titulo, emisor=emisor,
        fecha_emision=meta.get("fecha_emision", "").strip(), tipo=meta.get("tipo", "").strip(),
        area_emisora=meta.get("area_emisora", "").strip(), activo=meta.get("activo", "").strip(),
        reemplaza_a=meta.get("reemplaza_a", "—").strip() or "—",
        archivo=str(path), sha256=sha256(path), secciones=secciones,
    )
