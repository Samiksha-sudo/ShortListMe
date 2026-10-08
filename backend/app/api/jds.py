import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.api.deps import current_user_id, llm_user, owned
from app.db import get_db
from app.models import JobDescription
from app.schemas.jd import JDAnalysisResult
from app.services import jd_analysis
from app.services.llm import LLMError

router = APIRouter(prefix="/v1/jds", tags=["job descriptions"])

MIN_CHARS = 100
MAX_CHARS = 20_000


def normalise(text: str) -> str:
    """Trim and unify line endings so the same JD pasted twice hashes the same."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


class JDIn(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _length(cls, v: str) -> str:
        v = normalise(v)
        if len(v) < MIN_CHARS:
            raise ValueError(f"Paste the full job description (at least {MIN_CHARS} characters).")
        if len(v) > MAX_CHARS:
            raise ValueError(f"That job description is too long (maximum {MAX_CHARS:,} characters).")
        return v


class JDOut(BaseModel):
    jd_id: str
    text: str
    text_hash: str
    created_at: datetime


def _out(jd: JobDescription) -> JDOut:
    return JDOut(jd_id=jd.id, text=jd.text, text_hash=jd.text_hash, created_at=jd.created_at)


@router.post("", status_code=201, response_model=JDOut)
def create_jd(body: JDIn, db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> JDOut:
    jd = JobDescription(user_id=user_id, text=body.text, text_hash=hashlib.sha256(body.text.encode()).hexdigest())
    db.add(jd)
    db.commit()
    return _out(jd)


class AnalysisOut(JDAnalysisResult):
    jd_id: str
    cached: bool


@router.post("/{jd_id}/analysis", response_model=AnalysisOut)
def analyse_jd(jd_id: str, db: Session = Depends(get_db), user_id: str = Depends(llm_user)) -> AnalysisOut:
    jd = owned(db, JobDescription, jd_id, user_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="Job description not found.")
    try:
        result, cached = jd_analysis.analyse(db, jd)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AnalysisOut(jd_id=jd.id, cached=cached, **result.model_dump())


@router.get("/{jd_id}", response_model=JDOut)
def get_jd(jd_id: str, db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> JDOut:
    jd = owned(db, JobDescription, jd_id, user_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return _out(jd)
