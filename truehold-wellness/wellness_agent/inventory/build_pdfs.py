"""Build TrueHold Wellness information sheets for every live SKU.

Each sheet is written for the milligram vial in stock. Mix math is checked in
`protocol.verify_protocols()` before a file is written. Visuals are drawn in
ReportLab (syringe, size bars, incretin/mitochondria diagrams) so we do not
hotlink untrusted images.

https://www.reportlab.com/docs/reportlab-userguide.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from wellness_agent.inventory.protocol import HALF_ML_UNITS, PROTOCOLS, verify_protocols
from wellness_agent.inventory.sheet_specs import sheet_for

NAVY = Color(0.035294, 0.168627, 0.341176)
GOLD = Color(0.788235, 0.603922, 0.258824)
GRAY = Color(0.290196, 0.333333, 0.407843)
CREAM = HexColor("#F7F3E9")
ALERT = HexColor("#7A1F1F")
FOOTER = "TrueHold Wellness | Vial-specific sheet | Educational information only | Not medical advice"

ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "pdfs"
LOGO = ROOT / "assets" / "logo.jpeg"


def _styles():
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "THWBrand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=GOLD,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "THWTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=NAVY,
            spaceAfter=2,
        ),
        "kicker": ParagraphStyle(
            "THWKicker",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=GRAY,
            spaceAfter=10,
        ),
        "h": ParagraphStyle(
            "THWH",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=16,
            textColor=NAVY,
            spaceBefore=9,
            spaceAfter=4,
        ),
        "h_alert": ParagraphStyle(
            "THWAlertH",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=ALERT,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "THWBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.2,
            textColor=black,
            alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "THWBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=black,
        ),
        "dose": ParagraphStyle(
            "THWDose",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "dose_sub": ParagraphStyle(
            "THWDoseSub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "small": ParagraphStyle(
            "THWSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=GRAY,
        ),
        "th": ParagraphStyle(
            "THWTH",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=white,
        ),
        "td": ParagraphStyle(
            "THWTD",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=black,
        ),
    }


def _footer(canvas, doc):
    canvas.saveState()
    if LOGO.exists():
        canvas.drawImage(
            str(LOGO),
            0.55 * inch,
            0.16 * inch,
            width=0.48 * inch,
            height=0.62 * inch,
            preserveAspectRatio=True,
            mask="auto",
        )
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.6)
    canvas.line(0.55 * inch, 0.40 * inch, letter[0] - 0.55 * inch, 0.40 * inch)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(letter[0] / 2 + 0.12 * inch, 0.26 * inch, FOOTER)
    canvas.restoreState()


def _bullets(items: list[str], styles) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, styles["bullet"]), leftIndent=10) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=16,
        bulletFontName="Helvetica",
        bulletFontSize=9,
    )


def draw_syringe(units: float, caption: str = "") -> Drawing:
    """U-100 0.5 mL syringe: 50 units full. Mark the starting draw."""
    width, height = 460, 78
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=CREAM, strokeColor=NAVY, strokeWidth=0.6))
    barrel_x, barrel_y, barrel_w, barrel_h = 36, 28, 360, 22
    drawing.add(Rect(barrel_x, barrel_y, barrel_w, barrel_h, fillColor=white, strokeColor=NAVY, strokeWidth=1.2))
    drawing.add(Rect(barrel_x + barrel_w, barrel_y + 6, 28, 10, fillColor=NAVY, strokeColor=NAVY))
    drawing.add(String(8, 32, "0", fontName="Helvetica", fontSize=7, fillColor=NAVY))
    drawing.add(String(barrel_x + barrel_w - 10, 14, "50", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    drawing.add(String(barrel_x + barrel_w + 32, 32, "u", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    for tick in range(0, 51, 5):
        x = barrel_x + (tick / HALF_ML_UNITS) * barrel_w
        tall = 8 if tick % 10 == 0 else 4
        drawing.add(Line(x, barrel_y, x, barrel_y - tall, strokeColor=NAVY, strokeWidth=0.7))
        if tick in {0, 10, 20, 25, 40, 50}:
            drawing.add(String(x - 6, barrel_y - 16, str(tick), fontName="Helvetica", fontSize=6, fillColor=GRAY))
    mark = min(max(units, 0), HALF_ML_UNITS)
    mx = barrel_x + (mark / HALF_ML_UNITS) * barrel_w
    drawing.add(Line(mx, barrel_y - 2, mx, barrel_y + barrel_h + 8, strokeColor=GOLD, strokeWidth=2))
    drawing.add(Circle(mx, barrel_y + barrel_h + 12, 3, fillColor=GOLD, strokeColor=NAVY, strokeWidth=0.4))
    label = caption or f"Start: {units:g} units  =  {units / 100:.2f} mL on a 0.5 mL U-100 syringe"
    drawing.add(String(36, 58, label, fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    return drawing


def draw_size_bars(current: str) -> Drawing:
    sizes = [
        ("GHK-Cu", 404),
        ("NAD+", 663),
        ("SS-31", 749),
        ("Semax", 814),
        ("MOTS-c", 2175),
        ("Retatrutide", 4731),
        ("Tirzepatide", 4814),
    ]
    width, height = 460, 118
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=CREAM, strokeColor=NAVY, strokeWidth=0.6))
    drawing.add(String(10, 102, "How large is it?  (daltons, log-ish bars — bigger bar = bigger molecule)", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    max_mw = max(item[1] for item in sizes)
    for idx, (name, mw) in enumerate(sizes):
        y = 88 - idx * 12
        bar = 40 + (mw / max_mw) * 280
        fill = GOLD if name.split()[0] in current or current.startswith(name) or name in current else NAVY
        drawing.add(Rect(88, y, bar, 8, fillColor=fill, strokeColor=NAVY, strokeWidth=0.3))
        drawing.add(String(8, y, name, fontName="Helvetica", fontSize=7, fillColor=NAVY))
        drawing.add(String(88 + bar + 4, y, f"{mw} Da", fontName="Helvetica", fontSize=6.5, fillColor=GRAY))
    return drawing


def draw_incretin() -> Drawing:
    width, height = 460, 92
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=CREAM, strokeColor=NAVY, strokeWidth=0.6))
    drawing.add(String(10, 76, "How incretin shots talk to the body", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    boxes = [
        (18, 28, "GLP-1 receptor", "Appetite down\nStomach slower\nInsulin (if glucose high)"),
        (168, 28, "GIP receptor", "Insulin support\nFat-cell signaling"),
        (318, 28, "Glucagon receptor", "Energy burn\n(retatrutide only)"),
    ]
    for x, y, title, body in boxes:
        drawing.add(Rect(x, y, 128, 44, fillColor=white, strokeColor=NAVY, strokeWidth=0.8))
        drawing.add(String(x + 6, y + 30, title, fontName="Helvetica-Bold", fontSize=7, fillColor=NAVY))
        for i, line in enumerate(body.split("\n")):
            drawing.add(String(x + 6, y + 18 - i * 9, line, fontName="Helvetica", fontSize=6.5, fillColor=GRAY))
    return drawing


def draw_mito() -> Drawing:
    width, height = 460, 88
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=CREAM, strokeColor=NAVY, strokeWidth=0.6))
    drawing.add(String(10, 72, "Mitochondria — where NAD+, MOTS-c, and SS-31 work", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    drawing.add(Circle(70, 36, 28, fillColor=white, strokeColor=NAVY, strokeWidth=1.4))
    drawing.add(Circle(70, 36, 16, fillColor=None, strokeColor=GOLD, strokeWidth=1.2))
    drawing.add(String(48, 33, "matrix", fontName="Helvetica", fontSize=6, fillColor=GRAY))
    drawing.add(String(108, 48, "Inner membrane (cristae + cardiolipin) — SS-31 binds here", fontName="Helvetica", fontSize=7, fillColor=NAVY))
    drawing.add(String(108, 34, "NAD+ shuttles electrons for ATP", fontName="Helvetica", fontSize=7, fillColor=NAVY))
    drawing.add(String(108, 20, "MOTS-c is a 16-aa mitochondrial message to muscle / AMPK", fontName="Helvetica", fontSize=7, fillColor=NAVY))
    return drawing


def _dose_card(spec: dict, styles) -> Table:
    proto = spec["protocol"]
    start = proto["steps"][0]
    inner = [
        [Paragraph("THIS VIAL — STARTING DOSE (read this first)", styles["dose"])],
        [Paragraph(
            f"{spec['title']}  ·  {proto['vial_mg']:g} mg lyophilized  ·  mix with {proto['bac_ml']:g} mL bacteriostatic water  ·  "
            f"{proto['mg_per_ml']:g} mg/mL  ·  1 unit = {proto['mcg_per_unit']:g} mcg",
            styles["dose_sub"],
        )],
        [Paragraph(
            f"Start: draw <b>{start['units']:g} units</b> on a U-100 syringe "
            f"(<b>{start['ml']:.2f} mL</b> = <b>{start['mg']:g} mg</b>). {start['syringe']}",
            styles["dose_sub"],
        )],
        [Paragraph(f"Route: {proto['route']}<br/>Rhythm: {proto['cadence']}", styles["dose_sub"])],
    ]
    table = Table(inner, colWidths=[6.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                ("BOX", (0, 0), (-1, -1), 1.4, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("TOPPADDING", (0, 1), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 3),
            ]
        )
    )
    return table


def _schedule_table(proto: dict, styles) -> Table:
    header = [
        Paragraph("When", styles["th"]),
        Paragraph("Units (U-100)", styles["th"]),
        Paragraph("mg", styles["th"]),
        Paragraph("mL", styles["th"]),
        Paragraph("0.5 mL syringe", styles["th"]),
        Paragraph("How often", styles["th"]),
    ]
    rows = [header]
    for step in proto["steps"]:
        half = (
            f"Draw to {step['units']:g}"
            if step["half_ml"]
            else "Too big — 1 mL syringe or 50+ remainder"
        )
        rows.append(
            [
                Paragraph(step["when"], styles["td"]),
                Paragraph(f"{step['units']:g}", styles["td"]),
                Paragraph(f"{step['mg']:g}", styles["td"]),
                Paragraph(f"{step['ml']:.2f}", styles["td"]),
                Paragraph(half, styles["td"]),
                Paragraph(step["freq"], styles["td"]),
            ]
        )
    table = Table(rows, colWidths=[1.55 * inch, 0.85 * inch, 0.55 * inch, 0.5 * inch, 1.7 * inch, 1.35 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, -1), white),
                ("GRID", (0, 0), (-1, -1), 0.4, GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (0, 1), (-1, 1), HexColor("#E8F0E4")),
            ]
        )
    )
    return table


def _fda_box(text: str, styles) -> Table:
    inner = [[Paragraph(text, styles["body"])]]
    table = Table(inner, colWidths=[6.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8E8E8")),
                ("BOX", (0, 0), (-1, -1), 1.2, ALERT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def build_sheet(sku: str, dest: Path | None = None) -> Path:
    verify_protocols()
    spec = sheet_for(sku)
    proto = spec["protocol"]
    styles = _styles()
    dest = dest or (PDF_DIR / spec["filename"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(dest),
        pagesize=letter,
        leftMargin=0.58 * inch,
        rightMargin=0.58 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.78 * inch,
        title=f"{spec['title']} — TrueHold Wellness {proto['vial_mg']:g} mg vial",
        author="TrueHold Wellness",
        subject=f"Vial-specific information sheet for {proto['vial_mg']:g} mg {spec['title']}",
    )
    story = []
    story.append(Paragraph("TRUEHOLD WELLNESS", styles["brand"]))
    if LOGO.exists():
        img = Image(str(LOGO), width=0.95 * inch, height=1.22 * inch)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 4))
    story.append(Paragraph(spec["title"], styles["title"]))
    story.append(Paragraph(
        f"Information sheet written for the {proto['vial_mg']:g} mg vial TrueHold holds in stock. "
        "Not a generic internet protocol.",
        styles["kicker"],
    ))
    story.append(_dose_card(spec, styles))
    story.append(Spacer(1, 6))
    story.append(draw_syringe(proto["start_units"], f"Starting draw: {proto['start_units']:g} units  ({proto['start_mg']:g} mg = {proto['start_ml']:.2f} mL)"))
    story.append(Paragraph("1. What it is — the molecule, how large it is", styles["h"]))
    story.append(Paragraph(spec["what"], styles["body"]))
    visual = spec.get("visual")
    if visual == "incretin":
        story.append(Spacer(1, 4))
        story.append(draw_incretin())
    elif visual == "mito":
        story.append(Spacer(1, 4))
        story.append(draw_mito())
    story.append(Spacer(1, 4))
    story.append(draw_size_bars(spec["title"]))
    story.append(Paragraph("2. How it works in the body", styles["h"]))
    story.append(Paragraph(spec["works"], styles["body"]))
    story.append(Paragraph("3. Testing data — animal", styles["h"]))
    story.append(Paragraph(spec["animal"], styles["body"]))
    story.append(Paragraph("4. Testing data — human, what is expected, hopes", styles["h"]))
    story.append(Paragraph(spec["human"], styles["body"]))
    story.append(_bullets(spec["hopes"], styles))
    story.append(Paragraph("5. Have people hurt themselves? Risks", styles["h_alert"]))
    story.append(Paragraph(spec["harm"], styles["body"]))
    story.append(Paragraph("6. FDA — approved or not", styles["h_alert"]))
    story.append(_fda_box(spec["fda"], styles))
    story.append(Paragraph("7. Reconstitution for this exact vial", styles["h"]))
    story.append(Paragraph(
        f"Check the label: it must say {spec['title']} and {proto['vial_label']}. "
        f"You need bacteriostatic water (BAC), alcohol swabs, and U-100 insulin syringes "
        f"(0.5 mL / 50-unit for every starting draw on this sheet; 1 mL / 100-unit if a later step exceeds 50 units).",
        styles["body"],
    ))
    story.append(_bullets(
        [
            "Wash hands. Wipe the rubber top with an alcohol swab.",
            f"Draw <b>{proto['bac_ml']:g} mL</b> of BAC into a mixing syringe.",
            "Insert through the stopper. Inject slowly down the inside glass wall — not straight onto the powder.",
            "Gently roll or swirl until clear. Do not shake.",
            "Wipe the top again. Write today's date on the vial. Refrigerate 36–46°F. Use within 28 days.",
            "Mix and store in this vial only. Do not transfer.",
        ],
        styles,
    ))
    story.append(Paragraph("8. Loading the 0.5 mL syringe — schedule for this vial", styles["h"]))
    story.append(Paragraph(
        "U-100 math is the same on a 0.5 mL or 1 mL syringe: 100 units = 1.00 mL, so 50 units = 0.50 mL "
        "(a completely full 0.5 mL syringe). Starting draws on this sheet all fit 0.5 mL. "
        "The green row is the start.",
        styles["body"],
    ))
    story.append(Spacer(1, 4))
    story.append(_schedule_table(proto, styles))
    story.append(Spacer(1, 4))
    story.append(_bullets(proto["notes"], styles))
    story.append(Paragraph("Fulfillment", styles["h"]))
    story.append(_bullets(spec["fulfillment"], styles))
    story.append(Paragraph("Working with the team", styles["h"]))
    story.append(_bullets(spec["team"], styles))
    story.append(Paragraph("Sources", styles["h"]))
    story.append(_bullets(spec["sources"] + [proto["source"]], styles))
    story.append(Paragraph("Protocol note", styles["h"]))
    story.append(Paragraph(
        "TrueHold writes these sheets for the milligram vials we hold. Mix volume and unit marks were "
        "double-checked so milligrams, milliliters, and U-100 units agree. This is educational research "
        "information, not a prescription and not medical advice. The Telegram bot does not dose in chat — "
        "read this PDF. For an individualized plan, use /schedule. Research use only.",
        styles["body"],
    ))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return dest


def build_missing() -> list[Path]:
    verify_protocols()
    return [build_sheet(sku) for sku in PROTOCOLS]


def main() -> int:
    for path in build_missing():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
