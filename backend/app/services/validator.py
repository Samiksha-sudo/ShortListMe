import re

from app.schemas.cv import Block, BlockType, ParsedCV
from app.services.parsing.docx_parser import _NUMBER_RE, _SENIORITY, _TOKEN_RE

MAX_GROWTH = 0.15  # new text may be at most 15% longer than the original
MAX_SHRINK = 0.40  # ...and up to 40% shorter (trimming less relevant material)
MAX_HEADLINE_GROWTH = 1.0  # a headline may gain keywords, up to twice its length


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER_RE.findall(text)}


def _tokens(text: str) -> set[str]:
    return {t.lower().strip(".,") for t in _TOKEN_RE.findall(text)}


def _names(text: str) -> set[str]:
    """Company- and tool-like tokens: capitalised or containing . + # or digits, ignoring the first word."""
    words = _TOKEN_RE.findall(text)
    return {t.lower().strip(".,") for t in words[1:] if t[0].isupper() or any(c in t for c in ".+#0123456789")}


def _seniority(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w in _SENIORITY}


def check_edit(cv: ParsedCV, block: Block | None, new_text: str) -> list[str]:
    """Return the reasons an edit is rejected; an empty list means it is safe to propose."""
    if block is None:
        return ["Not a block in this CV."]
    if not block.editable:
        return ["This block is locked and cannot be edited."]
    old, new = block.text.strip(), new_text.strip()
    errors: list[str] = []

    growth = MAX_HEADLINE_GROWTH if block.type == BlockType.HEADLINE else MAX_GROWTH
    if len(new) > len(old) * (1 + growth):
        errors.append(f"Longer than the original by more than {round(growth * 100)}%.")
    elif len(new) < len(old) * (1 - MAX_SHRINK):
        errors.append("Shorter than the original by more than 40%.")

    added_numbers = _numbers(new) - _numbers(old)
    if added_numbers:
        errors.append(f"New numbers that are not in the original: {', '.join(sorted(added_numbers))}.")

    known = {e.lower() for e in cv.facts.entities} | _tokens(" ".join(b.text for b in cv.blocks))
    unknown = _names(new) - known
    if unknown:
        errors.append(f"Names that appear nowhere in the CV (companies or tools): {', '.join(sorted(unknown))}.")

    if block.type == BlockType.HEADLINE:
        if not new.startswith(old):
            errors.append("The headline must start from the original.")
        if _seniority(new) != _seniority(old):
            errors.append("The headline's seniority must not change.")
    return errors
