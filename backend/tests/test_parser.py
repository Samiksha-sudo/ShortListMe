import io

import pytest
from docx import Document

from app.schemas.cv import BlockType
from app.services.docx_validation import InvalidCV
from app.services.parsing.docx_parser import parse_docx
from app.services.parsing.locator import locate
from tests import samples


def parse(data: bytes):
    return parse_docx(data, "cv-1", "cv.docx")


def by_type(cv, typ):
    return [b for b in cv.blocks if b.type == typ]


def test_single_column_block_types():
    cv = parse(samples.single_column())
    assert by_type(cv, BlockType.NAME)[0].text == "Jane Doe"
    assert by_type(cv, BlockType.CONTACT)[0].text.startswith("jane@example.com")
    assert [h.text for h in by_type(cv, BlockType.HEADING)] == ["Summary", "Experience", "Skills", "Education"]
    assert len(by_type(cv, BlockType.BULLET)) == 3
    assert len(by_type(cv, BlockType.ROLE_TITLE)) == 2
    assert by_type(cv, BlockType.SKILL_LINE)[0].text.startswith("Node.js")


def test_headline_is_editable_and_name_contact_locked():
    cv = parse(samples.single_column())
    headline = by_type(cv, BlockType.HEADLINE)
    assert [h.text for h in headline] == ["Backend Software Engineer"]
    assert headline[0].editable
    assert not by_type(cv, BlockType.NAME)[0].editable
    assert not by_type(cv, BlockType.CONTACT)[0].editable


def test_editable_flags():
    cv = parse(samples.single_column())
    editable = {b.type for b in cv.blocks if b.editable}
    assert editable == {BlockType.HEADLINE, BlockType.SUMMARY, BlockType.BULLET, BlockType.SKILL_LINE}
    for b in cv.blocks:
        if b.type in (BlockType.ROLE_TITLE, BlockType.HEADING) or b.section == "Education":
            assert not b.editable


def test_bullets_link_to_their_role():
    cv = parse(samples.single_column())
    roles = {b.id: b.text for b in by_type(cv, BlockType.ROLE_TITLE)}
    bullets = by_type(cv, BlockType.BULLET)
    assert roles[bullets[0].parent_id].startswith("Software Engineer II")
    assert roles[bullets[2].parent_id].startswith("Software Engineer, ShopLab")


def test_facts_extracted():
    cv = parse(samples.single_column())
    assert {"2", "300", "2022", "2020"} <= set(cv.facts.numbers)
    assert {"foodco", "shoplab", "react", "node.js", "postgresql"} <= set(cv.facts.entities)
    assert cv.facts.skills[:3] == ["Node.js", "TypeScript", "React"]
    assert cv.facts.headline_seniority == []


def test_headline_seniority_recorded():
    cv = parse(samples.glyph_bullets())
    assert cv.facts.headline_seniority == ["senior"]


def test_glyph_bullets_stripped_and_prefix_kept():
    cv = parse(samples.glyph_bullets())
    bullets = by_type(cv, BlockType.BULLET)
    assert [b.text for b in bullets] == ["Built ETL pipelines processing 5TB per day.", "Reduced warehouse costs by 30%."]
    assert [b.locator.prefix for b in bullets] == ["• ", "- "]
    assert "WORK EXPERIENCE" in cv.sections


def test_table_layout_is_parsed():
    cv = parse(samples.table_based())
    assert by_type(cv, BlockType.NAME)[0].text == "Jane Doe"
    assert by_type(cv, BlockType.SKILL_LINE)[0].text == "Python, FastAPI, SQL"
    bullet = by_type(cv, BlockType.BULLET)[0]
    assert bullet.locator.table is not None and bullet.editable


def test_headers_and_footers_are_locked():
    cv = parse(samples.with_header_footer())
    parts = {b.locator.part: b for b in cv.blocks if b.locator.part != "body"}
    assert set(parts) == {"header:0", "footer:0"}
    assert not any(b.editable for b in parts.values())


@pytest.mark.parametrize("make", [samples.single_column, samples.glyph_bullets,
                                  samples.table_based, samples.with_header_footer])
def test_every_locator_points_back_to_its_text(make):
    data = make()
    cv = parse(data)
    doc = Document(io.BytesIO(data))
    for b in cv.blocks:
        par = locate(doc, b.locator)
        assert par.text.strip().removeprefix(b.locator.prefix.strip()).strip() == b.text, b.id


def test_block_ids_unique_and_sequential():
    cv = parse(samples.single_column())
    assert [b.id for b in cv.blocks] == [f"b_{i:03d}" for i in range(1, len(cv.blocks) + 1)]


def test_garbage_raises():
    with pytest.raises(InvalidCV):
        parse_docx(b"PK\x03\x04 not really", "x", "x.docx")
