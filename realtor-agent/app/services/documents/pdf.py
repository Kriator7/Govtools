"""Create and fill AcroForm PDFs without modifying the original template."""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfgen.canvas import Canvas


SAMPLE_FIELDS = {
    "BuyerFullName": (72, 640),
    "PropertyAddress": (72, 600),
    "PurchasePrice": (72, 560),
    "EarnestDeposit": (72, 520),
    "ClosingDate": (72, 480),
    "FinancingType": (72, 440),
}


def ensure_sample_template(path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle("Sample Nevada Purchase Agreement Placeholder")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "SAMPLE PURCHASE AGREEMENT PLACEHOLDER")
    c.setFont("Helvetica", 10)
    c.drawString(72, 700, "Not a legal form. For software demonstration only.")
    c.drawString(72, 684, "Do not use for a real Nevada real-estate transaction.")
    labels = [
        (72, 655, "Buyer legal name"),
        (72, 615, "Property address"),
        (72, 575, "Purchase price"),
        (72, 535, "Earnest money"),
        (72, 495, "Closing date"),
        (72, 455, "Financing type"),
    ]
    for x, y, label in labels:
        c.drawString(x, y, label)
    _add_text_fields(c)
    c.showPage()
    c.save()
    path.write_bytes(buffer.getvalue())
    return path


def _add_text_fields(c: Canvas) -> None:
    try:
        from reportlab.lib.colors import black
        from reportlab.pdfbase.pdfform import textFieldRelative
    except Exception:
        return
    form = c.acroForm
    for name, (x, y) in SAMPLE_FIELDS.items():
        form.textfield(
            name=name,
            tooltip=name,
            x=x,
            y=y,
            width=420,
            height=18,
            borderWidth=1,
            borderColor=black,
            fillColor=None,
            textColor=black,
            forceBorder=True,
        )
    _ = textFieldRelative


def fill_pdf(template_path: Path, field_values: dict[str, str]) -> bytes:
    reader = PdfReader(str(template_path))
    writer = PdfWriter()
    writer.append(reader)
    if writer.get_fields():
        writer.update_page_form_field_values(writer.pages[0], field_values)
    else:
        packet = BytesIO()
        overlay = canvas.Canvas(packet, pagesize=letter)
        overlay.setFont("Helvetica", 11)
        y = 640
        for key, value in field_values.items():
            overlay.drawString(72, y, f"{key}: {value}")
            y -= 24
        overlay.save()
        packet.seek(0)
        overlay_reader = PdfReader(packet)
        writer.pages[0].merge_page(overlay_reader.pages[0])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
