import io
import re

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.schemas.cv import Block, BlockType, Facts, Locator, ParsedCV
from app.services.docx_validation import InvalidCV

_SECTION_TITLES = {
    "summary": ["summary", "professional summary", "profile", "professional profile", "about", "about me",
                "objective", "career objective", "personal statement"],
    "experience": ["experience", "work experience", "professional experience", "employment",
                   "employment history", "work history", "career history"],
    "projects": ["projects", "personal projects", "key projects"],
    "skills": ["skills", "technical skills", "key skills", "core skills", "core competencies", "technologies"],
    "education": ["education", "education and training", "academic background", "qualifications"],
    "locked": ["certifications", "certificates", "languages", "interests", "hobbies", "references",
               "awards", "publications", "achievements"],
}
_TITLE_KIND = {t: kind for kind, titles in _SECTION_TITLES.items() for t in titles}

_SENIORITY = {"senior", "lead", "principal", "staff", "head", "director", "manager", "junior",
              "graduate", "intern", "chief", "vp"}
_ROLE_WORDS = {"engineer", "developer", "manager", "designer", "analyst", "consultant", "architect",
               "scientist", "lead", "director", "specialist", "officer", "administrator", "intern",
               "programmer", "tester", "devops", "sre"}

# Bullet glyphs written as escapes so the source stays ASCII-safe.
_BULLET_RE = re.compile("^([•●▪◦‣∙·*\\-–—])\\s+")
_CONTACT_RE = re.compile(r"@|https?://|www\.|linkedin|github|\+?\d[\d\s().-]{7,}\d", re.I)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.+#_-]*")


def _title_kind(text: str) -> str | None:
    if len(text) > 40:
        return None
    norm = re.sub(r"[^a-z& ]", "", text.lower()).replace("&", "and")
    return _TITLE_KIND.get(re.sub(r"\s+", " ", norm).strip())


def _is_list_paragraph(par: Paragraph) -> bool:
    ppr = par._p.pPr
    if ppr is not None and ppr.numPr is not None:
        return True
    style = par.style.name if par.style is not None else ""
    return "list" in style.lower()


def _looks_like_headline(text: str) -> bool:
    if len(text) > 90:
        return False
    if any(w in _ROLE_WORDS for w in re.findall(r"[a-z]+", text.lower())):
        return True
    return "," not in text and len(text.split()) >= 2


class _Walker:
    def __init__(self) -> None:
        self.blocks: list[Block] = []
        self.sections: list[str] = ["Header"]
        self.section = "Header"
        self.kind = "header"
        self.seen_name = False
        self.seen_headline = False
        self.last_role: str | None = None

    def add(self, typ: BlockType, text: str, loc: Locator, editable: bool, section: str | None = None) -> str:
        bid = f"b_{len(self.blocks) + 1:03d}"
        parent = self.last_role if typ == BlockType.BULLET else None
        self.blocks.append(Block(id=bid, type=typ, section=section or self.section, text=text,
                                 locator=loc, editable=editable, parent_id=parent))
        return bid

    def paragraph(self, par: Paragraph, part: str, table: list[int] | None, p_idx: int) -> None:
        text = par.text.strip()
        if not text:
            return
        loc = Locator(part=part, table=table, p=p_idx, runs=len(par.runs))
        if part != "body":
            self.add(BlockType.OTHER, text, loc, False, section=part.split(":")[0].title())
            return

        kind = _title_kind(text)
        if kind:
            self.section, self.kind, self.last_role = text, kind, None
            if text not in self.sections:
                self.sections.append(text)
            self.add(BlockType.HEADING, text, loc, False)
            return

        is_bullet = _is_list_paragraph(par)
        m = _BULLET_RE.match(text)
        if m:
            is_bullet = True
            loc.prefix, text = m.group(1) + " ", text[m.end():].strip()

        if self.kind == "header":
            self._header_line(text, loc)
        elif self.kind == "summary":
            self.add(BlockType.SUMMARY, text, loc, True)
        elif self.kind in ("experience", "projects"):
            if is_bullet or len(text) > 100:
                self.add(BlockType.BULLET, text, loc, True)
            else:
                self.last_role = self.add(BlockType.ROLE_TITLE, text, loc, False)
        elif self.kind == "skills":
            self.add(BlockType.SKILL_LINE, text, loc, True)
        else:  # education and locked sections stay untouched
            self.add(BlockType.OTHER, text, loc, False)

    def _header_line(self, text: str, loc: Locator) -> None:
        if not self.seen_name:
            self.seen_name = True
            self.add(BlockType.NAME, text, loc, False)
        elif _CONTACT_RE.search(text):
            self.add(BlockType.CONTACT, text, loc, False)
        elif not self.seen_headline and _looks_like_headline(text):
            self.seen_headline = True
            self.add(BlockType.HEADLINE, text, loc, True)
        elif len(text) > 100:
            if "Summary" not in self.sections:
                self.sections.append("Summary")
            self.add(BlockType.SUMMARY, text, loc, True, section="Summary")
        else:
            self.add(BlockType.OTHER, text, loc, False)


def _build_facts(blocks: list[Block]) -> Facts:
    numbers: set[str] = set()
    entities: set[str] = set()
    skills: list[str] = []
    for b in blocks:
        numbers.update(n.replace(",", "") for n in _NUMBER_RE.findall(b.text))
        for tok in _TOKEN_RE.findall(b.text):
            if tok[0].isupper() or any(c in tok for c in ".+#0123456789"):
                entities.add(tok.lower().strip(".,"))
        if b.type == BlockType.SKILL_LINE:
            line = b.text.split(":", 1)[-1]
            skills += [s.strip() for s in re.split(r"[,;|•·]", line) if s.strip()]
    headline = next((b.text for b in blocks if b.type == BlockType.HEADLINE), "")
    seniority = sorted(w for w in re.findall(r"[a-z]+", headline.lower()) if w in _SENIORITY)
    return Facts(numbers=sorted(numbers), entities=sorted(entities), skills=skills,
                 headline_seniority=seniority)


def parse_docx(data: bytes, cv_id: str, filename: str) -> ParsedCV:
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        raise InvalidCV("Could not read this DOCX file.") from None

    w = _Walker()
    p_idx = t_idx = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            w.paragraph(Paragraph(child, doc), "body", None, p_idx)
            p_idx += 1
        elif tag == "tbl":
            table = Table(child, doc)
            for r, row in enumerate(table.rows):
                seen = set()
                for c, cell in enumerate(row.cells):
                    if cell._tc in seen:  # merged cells repeat
                        continue
                    seen.add(cell._tc)
                    for pi, par in enumerate(cell.paragraphs):
                        w.paragraph(par, "body", [t_idx, r, c], pi)
            t_idx += 1

    for si, section in enumerate(doc.sections):
        for kind, part in (("header", section.header), ("footer", section.footer)):
            if si > 0 and part.is_linked_to_previous:
                continue
            for pi, par in enumerate(part.paragraphs):
                w.paragraph(par, f"{kind}:{si}", None, pi)

    return ParsedCV(cv_id=cv_id, filename=filename, sections=w.sections, blocks=w.blocks,
                    facts=_build_facts(w.blocks))
