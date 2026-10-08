from pydantic import BaseModel, Field


class ProposedEdit(BaseModel):
    block_id: str
    new_text: str
    rationale: str
    added_keywords: list[str] = Field(default_factory=list)


class ModelEdits(BaseModel):
    edits: list[ProposedEdit] = Field(default_factory=list)


class DroppedEdit(BaseModel):
    block_id: str
    reason: str


class RewriteOut(BaseModel):
    cv_id: str
    jd_id: str
    edits: list[ProposedEdit]
    dropped: list[DroppedEdit]
