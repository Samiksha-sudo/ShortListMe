from typing import Literal

from pydantic import BaseModel

Status = Literal["covered", "weak", "gap"]


class Judgement(BaseModel):
    """What the model says about one numbered requirement."""
    index: int
    status: Status
    evidence: str | None = None


class Judgements(BaseModel):
    items: list[Judgement]


class MatchItem(BaseModel):
    requirement: str
    kind: Literal["must", "nice"]
    status: Status
    evidence: str | None = None


class MatchOut(BaseModel):
    cv_id: str
    jd_id: str
    score: int
    items: list[MatchItem]
    covered: int
    weak: int
    gaps: int
