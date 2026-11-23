"""Regenera los PDF del corpus desde los Markdown, con la maquetación de los originales.

La usa la prueba de envenenamiento para construir el documento con la paráfrasis del ataque.
Uso: python herramientas/regenerar_pdf.py <carpeta_md> <carpeta_salida>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def _fuentes() -> tuple[str, str]:
    """Usa Liberation Sans (Unicode completo) si está instalada; si no, Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    base = Path("/usr/share/fonts/truetype/liberation")
    reg, bold = base / "LiberationSans-Regular.ttf", base / "LiberationSans-Bold.ttf"
    if reg.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("Sans", str(reg)))
        pdfmetrics.registerFont(TTFont("Sans-Bold", str(bold)))
        return "Sans", "Sans-Bold"
    return "Helvetica", "Helvetica-Bold"


F, FB = _fuentes()

AVISO = ("Documento sintético de uso académico — ARTI 4212, Universidad de los Andes. "
         "Empresas y entidades ficticias; sin validez operativa ni regulatoria.")

BODY = ParagraphStyle("body", fontName=F, fontSize=9.5, leading=12.5, spaceAfter=5)
HEAD = ParagraphStyle("head", fontName=FB, fontSize=11.5, leading=14, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("title", fontName=F, fontSize=13, leading=16, spaceAfter=8)
CELL = ParagraphStyle("cell", fontName=F, fontSize=8.5, leading=10.5)
CELL_B = ParagraphStyle("cellb", fontName=FB, fontSize=8.5, leading=10.5)


def esc(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def parse_md(path: Path):
    raw = path.read_text(encoding="utf-8")
    _, fm, body = raw.split("---", 2)
    meta = yaml.safe_load(fm)
    lines = body.strip().splitlines()
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln or ln.startswith("# ") or ln.startswith("**"):
            i += 1
            continue
        if ln.startswith("## "):
            blocks.append(("h", ln[3:].strip()))
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("t", rows))
            continue
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:].strip())
                i += 1
            blocks.append(("ul", items))
            continue
        else:
            blocks.append(("p", ln))
        i += 1
    return meta, blocks


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont(F, 7)
    canvas.drawString(2 * cm, 1.4 * cm, AVISO)
    canvas.drawRightString(letter[0] - 2 * cm, 1.0 * cm, f"Página {doc.page}")
    canvas.restoreState()


def render(md: Path, out: Path) -> None:
    meta, blocks = parse_md(md)
    story = [Paragraph(f"<b>{esc(str(meta['emisor']).upper())}</b> {esc(meta['titulo'])}", TITLE)]
    rows = [
        [Paragraph("Código", CELL_B), Paragraph(esc(str(meta["codigo"])), CELL),
         Paragraph("Versión", CELL_B), Paragraph(esc(str(meta["version"])), CELL)],
        [Paragraph("Fecha de emisión", CELL_B), Paragraph(str(meta["fecha_emision"]), CELL),
         Paragraph("Tipo", CELL_B), Paragraph(esc(meta["tipo"]), CELL)],
        [Paragraph("Área emisora", CELL_B), Paragraph(esc(meta["area_emisora"]), CELL),
         Paragraph("Activo / alcance", CELL_B), Paragraph(esc(meta["activo"]), CELL)],
    ]
    if str(meta.get("reemplaza_a", "—")).strip() not in ("—", "", "None"):
        rows.append([Paragraph("Reemplaza a", CELL_B), Paragraph(esc(meta["reemplaza_a"]), CELL), "", ""])
    t = Table(rows, colWidths=[3.2 * cm, 5.4 * cm, 3.2 * cm, 5.4 * cm])
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if len(rows) == 4:
        style.append(("SPAN", (1, 3), (3, 3)))
    t.setStyle(TableStyle(style))
    story += [t, Spacer(1, 10)]
    for kind, val in blocks:
        if kind == "h":
            story.append(Paragraph(esc(val), HEAD))
        elif kind == "p":
            story.append(Paragraph(esc(val), BODY))
        elif kind == "ul":
            for it in val:
                story.append(Paragraph("• " + esc(it), BODY))
        elif kind == "t":
            data = [[Paragraph(esc(c), CELL_B if r == 0 else CELL) for c in row] for r, row in enumerate(val)]
            tb = Table(data, repeatRows=1)
            tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [tb, Spacer(1, 6)]
    out.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(out), pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=2 * cm, bottomMargin=2.2 * cm, title=meta["titulo"]).build(
        story, onFirstPage=pie, onLaterPages=pie)


def main(src: str, dst: str) -> None:
    n = 0
    for md in sorted(Path(src).rglob("*.md")):
        render(md, Path(dst) / md.relative_to(src).with_suffix(".pdf"))
        n += 1
    print(f"{n} PDF regenerados en {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
