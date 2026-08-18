"""Build TrueHold Wellness locked information sheets.

Visual language matches the existing Tirzepatide/NAD ReportLab sheets:
navy headings, gold footer rule, Helvetica, letter size, logo watermark.
New sheets are educational only — no reconstitution or dosing schedules.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import Color, black
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

NAVY = Color(0.035294, 0.168627, 0.341176)
GOLD = Color(0.788235, 0.603922, 0.258824)
GRAY = Color(0.290196, 0.333333, 0.407843)
FOOTER = "TrueHold Wellness | Educational information only | Protocol details reviewed case by case"

ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "pdfs"
LOGO = ROOT / "assets" / "logo.jpeg"

SHEETS = {
    "klow": {
        "title": "KLOW",
        "filename": "klow.pdf",
        "short": (
            "KLOW is TrueHold Wellness's 80 mg regenerative research formula. "
            "It is discussed in tissue-remodeling, recovery, and skin-and-connective-tissue "
            "research contexts. The shop listing is a lyophilized laboratory research vial."
        ),
        "works": (
            "KLOW is framed as a regenerative research blend. Community discussion often "
            "groups copper-peptide, tissue-repair, and recovery themes under this name. "
            "TrueHold supplies it as an 80 mg lyophilized research compound for laboratory "
            "and scientific research applications only."
        ),
        "themes": [
            "Regenerative research",
            "Tissue-remodeling discussions",
            "Recovery and resilience themes",
            "Skin and connective-tissue research",
            "Multi-compound regenerative formulas",
        ],
        "who": [
            "People tracking regenerative research",
            "Members focused on recovery protocols with the team",
            "People asking about tissue-remodeling compounds",
            "Labs comparing regenerative research formulas",
        ],
        "track": [
            "Recovery quality",
            "Skin and tissue notes",
            "Training consistency",
            "Comfort and irritation",
            "Overall wellness markers with the team",
        ],
        "vial": "80 mg lyophilized vial",
        "shop": "https://trueholdwellness.com/ols/products/klow-premium-research-formula-80-mg",
        "category": "Regenerative research compounds",
    },
    "mots-c": {
        "title": "MOTS-c",
        "filename": "mots-c.pdf",
        "short": (
            "MOTS-c is a mitochondrial-encoded peptide commonly discussed in metabolic "
            "signaling, exercise-adaptation, and cellular-energy research. TrueHold lists "
            "it as a 20 mg lyophilized premium research formula."
        ),
        "works": (
            "MOTS-c is researched as a mitochondrial-derived peptide involved in metabolic "
            "regulation discussions. Themes include AMPK-related signaling, exercise-mimetic "
            "research, and cellular energy adaptation. It is not a GLP-1 or GIP agonist."
        ),
        "themes": [
            "Mitochondrial signaling",
            "Metabolic regulation research",
            "Exercise-adaptation discussions",
            "Cellular energy",
            "Healthy-aging research themes",
        ],
        "who": [
            "People tracking metabolic health",
            "Athletes and active members focused on energy",
            "Members interested in mitochondrial peptides",
            "Labs studying metabolic signaling compounds",
        ],
        "track": [
            "Energy",
            "Exercise tolerance",
            "Recovery",
            "Body-composition notes",
            "Training consistency",
        ],
        "vial": "20 mg lyophilized vial",
        "shop": "https://trueholdwellness.com/ols/products/mots-c-premium-research-formula-20-mg",
        "category": "Metabolic signaling peptides",
    },
    "ss-31": {
        "title": "SS-31",
        "filename": "ss-31.pdf",
        "short": (
            "SS-31 (also discussed as elamipretide) is a mitochondria-targeted peptide "
            "studied in relation to mitochondrial membranes, cardiolipin, and cellular "
            "energy. TrueHold lists it as a 10 mg lyophilized premium research formula."
        ),
        "works": (
            "SS-31 is researched for interaction with the inner mitochondrial membrane "
            "and cardiolipin. Community and published discussion often focuses on "
            "mitochondrial efficiency, oxidative-stress themes, and energy-production biology. "
            "It is not an incretin (GLP-1/GIP) compound."
        ),
        "themes": [
            "Mitochondrial membrane research",
            "Cellular energy",
            "Cardiolipin-related discussions",
            "Recovery and resilience",
            "Healthy-aging research themes",
        ],
        "who": [
            "People focused on energy and mitochondrial research",
            "Members tracking recovery and resilience",
            "People comparing mitochondrial compounds with NAD+",
            "Labs studying mitochondria-targeted peptides",
        ],
        "track": [
            "Energy",
            "Exercise tolerance",
            "Recovery",
            "Focus",
            "Overall stamina notes",
        ],
        "vial": "10 mg lyophilized vial",
        "shop": "https://trueholdwellness.com/ols/products/ss-31-premium-research-formula-10-mg",
        "category": "Mitochondrial research compounds",
    },
    "ghk-cu": {
        "title": "GHK-Cu",
        "filename": "ghk-cu.pdf",
        "short": (
            "GHK-Cu is a copper-binding tripeptide widely discussed in skin, tissue-remodeling, "
            "and regenerative-research contexts. TrueHold lists it as a 100 mg lyophilized "
            "premium research formula."
        ),
        "works": (
            "GHK-Cu is researched as a naturally occurring copper peptide associated with "
            "extracellular-matrix remodeling, skin-appearance discussions, and tissue-repair "
            "themes. It is not a GLP-1, GIP, or glucagon receptor agonist."
        ),
        "themes": [
            "Skin and tissue-remodeling research",
            "Copper-peptide biology",
            "Regenerative discussions",
            "Extracellular-matrix themes",
            "Cosmetic-research interest",
        ],
        "who": [
            "People focused on skin and tissue research",
            "Members asking about copper peptides",
            "People tracking regenerative formulas",
            "Labs studying GHK-Cu research applications",
        ],
        "track": [
            "Skin notes",
            "Tissue comfort",
            "Recovery",
            "Irritation or sensitivity",
            "Overall appearance goals with the team",
        ],
        "vial": "100 mg lyophilized vial",
        "shop": "https://trueholdwellness.com/ols/products/ghk-cu-premium-research-formula-100-mg",
        "category": "Regenerative research compounds",
    },
}


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "THWTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=NAVY,
            spaceAfter=2,
            alignment=TA_LEFT,
        ),
        "kicker": ParagraphStyle(
            "THWKicker",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=GRAY,
            spaceAfter=14,
        ),
        "h": ParagraphStyle(
            "THWH",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "THWBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=black,
            alignment=TA_LEFT,
        ),
        "bullet": ParagraphStyle(
            "THWBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=black,
        ),
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
    }


def _footer(canvas, doc):
    canvas.saveState()
    if LOGO.exists():
        canvas.drawImage(
            str(LOGO),
            0.55 * inch,
            0.18 * inch,
            width=0.55 * inch,
            height=0.70 * inch,
            preserveAspectRatio=True,
            mask="auto",
        )
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.5)
    canvas.line(0.55 * inch, 0.42 * inch, letter[0] - 0.55 * inch, 0.42 * inch)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(letter[0] / 2 + 0.15 * inch, 0.28 * inch, FOOTER)
    canvas.restoreState()


def build_sheet(key: str, dest: Path | None = None) -> Path:
    spec = SHEETS[key]
    styles = _styles()
    dest = dest or (PDF_DIR / spec["filename"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(dest),
        pagesize=letter,
        leftMargin=0.63 * inch,
        rightMargin=0.63 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.85 * inch,
        title=spec["title"],
        author="TrueHold Wellness",
        subject="Locked peptide information sheet",
    )
    story = []
    story.append(Paragraph("TRUEHOLD WELLNESS", styles["brand"]))
    if LOGO.exists():
        img = Image(str(LOGO), width=1.7 * inch, height=2.18 * inch)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 8))
    story.append(Paragraph(spec["title"], styles["title"]))
    story.append(Paragraph("Locked peptide information sheet", styles["kicker"]))
    story.append(Paragraph("Short Description", styles["h"]))
    story.append(Paragraph(spec["short"], styles["body"]))
    story.append(Paragraph("How It Works", styles["h"]))
    story.append(Paragraph(spec["works"], styles["body"]))
    story.append(Paragraph("Key Research Themes", styles["h"]))
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["bullet"]), leftIndent=12) for item in spec["themes"]],
            bulletType="bullet",
            start="•",
            leftIndent=18,
            bulletFontName="Helvetica",
            bulletFontSize=9.5,
        )
    )
    story.append(Paragraph("Who Commonly Asks About It", styles["h"]))
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["bullet"]), leftIndent=12) for item in spec["who"]],
            bulletType="bullet",
            start="•",
            leftIndent=18,
            bulletFontName="Helvetica",
            bulletFontSize=9.5,
        )
    )
    story.append(Paragraph("What To Track", styles["h"]))
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, styles["bullet"]), leftIndent=12) for item in spec["track"]],
            bulletType="bullet",
            start="•",
            leftIndent=18,
            bulletFontName="Helvetica",
            bulletFontSize=9.5,
        )
    )
    story.append(Paragraph("Shop Listing", styles["h"]))
    rows = [
        ["Product", spec["title"]],
        ["Category", spec["category"]],
        ["Vial", spec["vial"]],
        ["Shop", spec["shop"]],
    ]
    table = Table(rows, colWidths=[1.3 * inch, 5.2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(table)
    story.append(Paragraph("Protocol Note", styles["h"]))
    story.append(
        Paragraph(
            "TrueHold shares locked information sheets for general education only. "
            "Protocol details are reviewed by the TrueHold team case by case. "
            "The bot does not provide dosing, reconstitution, or administration instructions in chat. "
            "For individualized plans, use /schedule to book with the team. "
            "Research use only.",
            styles["body"],
        )
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return dest


def build_missing() -> list[Path]:
    return [build_sheet(key) for key in SHEETS]


if __name__ == "__main__":
    for path in build_missing():
        print(path)
