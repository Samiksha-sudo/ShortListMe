"""Apply accepted edits to the original CV DOCX and render the result."""
import io

from docx import Document

from app.schemas.cv import ParsedCV
from app.services.parsing.locator import locate


class ExportError(Exception):
    pass


def resolve_edits(cv: ParsedCV, edits: dict[str, str]) -> dict[str, str]:
    """Validate every requested edit against the parsed CV. Raises ExportError on the first problem."""
    blocks = {b.id: b for b in cv.blocks}
    out: dict[str, str] = {}
    for block_id, text in edits.items():
        block = blocks.get(block_id)
        if block is None:
            raise ExportError(f"Unknown block {block_id}.")
        if not block.editable:
            raise ExportError("One of the changes targets a part of your CV that can't be edited.")
        text = text.strip()
        if not text:
            raise ExportError("A change is empty.")
        out[block_id] = text
    return out


def apply_edits(original: bytes, cv: ParsedCV, edits: dict[str, str]) -> bytes:
    """Write each edit into the first run of its paragraph (keeping that run's formatting)."""
    doc = Document(io.BytesIO(original))
    blocks = {b.id: b for b in cv.blocks}
    for block_id, text in edits.items():
        loc = blocks[block_id].locator
        try:
            par = locate(doc, loc)
        except (IndexError, ValueError):
            raise ExportError("Your CV file no longer matches the parsed version.") from None
        runs = par.runs
        full = loc.prefix + text
        if runs:
            runs[0].text = full
            for extra in runs[1:]:
                extra._r.getparent().remove(extra._r)
        else:
            par.add_run(full)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def final_lines(cv: ParsedCV, edits: dict[str, str]) -> list[tuple[str, str]]:
    """(block type, text) for every non-empty block, edits applied. Used by the PDF renderer."""
    return [(b.type.value, b.locator.prefix + edits.get(b.id, b.text)) for b in cv.blocks
            if b.locator.part == "body"]


def render_pdf(cv: ParsedCV, edits: dict[str, str]) -> bytes:
    """Clean one-column PDF of the final text. Shrinks the font (down to 8pt) to fit one page where possible."""
    from xml.sax.saxutils import escape

    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    lines = final_lines(cv, edits)

    def build(size: float) -> tuple[bytes, int]:
        base = ParagraphStyle("base", fontName="Helvetica", fontSize=size, leading=size * 1.3)
        styles = {
            "name": ParagraphStyle("n", parent=base, fontName="Helvetica-Bold", fontSize=size * 2, leading=size * 2.3, alignment=TA_CENTER),
            "contact": ParagraphStyle("c", parent=base, alignment=TA_CENTER, textColor=HexColor("#444444")),
            "headline": ParagraphStyle("h", parent=base, fontSize=size * 1.15, alignment=TA_CENTER, spaceAfter=size * 0.4),
            "heading": ParagraphStyle("s", parent=base, fontName="Helvetica-Bold", fontSize=size * 1.1, spaceBefore=size * 0.9, spaceAfter=2),
            "role_title": ParagraphStyle("r", parent=base, fontName="Helvetica-Bold", spaceBefore=size * 0.4),
            "bullet": ParagraphStyle("b", parent=base, leftIndent=12, firstLineIndent=-8),
        }
        story = []
        for typ, text in lines:
            if typ == "bullet":
                text = "• " + text.lstrip("•●▪◦‣∙·*-–— ")
            story.append(Paragraph(escape(text), styles.get(typ, base)))
            if typ == "heading":
                story.append(HRFlowable(width="100%", thickness=0.6, color=HexColor("#999999"), spaceAfter=3))
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                                title=cv.filename)
        doc.build(story or [Spacer(1, 1)])
        return buf.getvalue(), doc.page

    size = 10.5
    while True:
        data, pages = build(size)
        if pages <= 1 or size <= 8:
            return data
        size -= 0.5
