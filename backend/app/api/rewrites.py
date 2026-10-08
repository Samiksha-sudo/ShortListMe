from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import llm_user, owned
from app.db import get_db
from app.models import CV, JobDescription
from app.schemas.cv import ParsedCV
from app.schemas.rewrite import RewriteOut
from app.services import jd_analysis, rewriting
from app.services.llm import LLMError

router = APIRouter(prefix="/v1/rewrites", tags=["rewrites"])


class RewriteIn(BaseModel):
    cv_id: str
    jd_id: str


@router.post("", response_model=RewriteOut)
def propose_rewrites(body: RewriteIn, db: Session = Depends(get_db), user_id: str = Depends(llm_user)) -> RewriteOut:
    cv = owned(db, CV, body.cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    jd = owned(db, JobDescription, body.jd_id, user_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="Job description not found.")
    try:
        analysis, _ = jd_analysis.analyse(db, jd)
        edits, dropped = rewriting.propose(ParsedCV.model_validate(cv.parsed), analysis)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RewriteOut(cv_id=cv.id, jd_id=jd.id, edits=edits, dropped=dropped)
