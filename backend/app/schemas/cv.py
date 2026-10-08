from enum import Enum

from pydantic import BaseModel


class BlockType(str, Enum):
    NAME = "name"
    CONTACT = "contact"
    HEADLINE = "headline"
    HEADING = "heading"
    SUMMARY = "summary"
    ROLE_TITLE = "role_title"
    BULLET = "bullet"
    SKILL_LINE = "skill_line"
    OTHER = "other"


class Locator(BaseModel):
    part: str  # "body", "header:<section index>", "footer:<section index>"
    table: list[int] | None = None  # [table, row, cell] when inside a body table
    p: int  # paragraph index within the body / header / footer / cell
    runs: int  # number of runs in the paragraph (export writes into the first run)
    prefix: str = ""  # leading bullet glyph stripped from the text, restored on export


class Block(BaseModel):
    id: str
    type: BlockType
    section: str
    text: str
    locator: Locator
    editable: bool
    parent_id: str | None = None


class Facts(BaseModel):
    numbers: list[str]
    entities: list[str]
    skills: list[str]
    headline_seniority: list[str]


class ParsedCV(BaseModel):
    cv_id: str
    filename: str
    sections: list[str]
    blocks: list[Block]
    facts: Facts
