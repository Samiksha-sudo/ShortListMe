from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import llm_user, owned
from app.db import get_db
from app.models import CV, JobDescription
from app.schemas.cv import ParsedCV
from app.schemas.match import MatchOut
from app.services import jd_analysis, matching
from app.services.llm import LLMError

router = APIRouter(prefix="/v1/matches", tags=["matches"])


class MatchIn(BaseModel):
    cv_id: str
    jd_id: str


@router.post("", response_model=MatchOut)
def create_match(body: MatchIn, db: Session = Depends(get_db), user_id: str = Depends(llm_user)) -> MatchOut:
    cv = owned(db, CV, body.cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    jd = owned(db, JobDescription, body.jd_id, user_id)
    if jd is None:
        raise HTTPException(status_code=404, detail="Job description not found.")
    try:
        analysis, _ = jd_analysis.analyse(db, jd)
        items = matching.match(ParsedCV.model_validate(cv.parsed), analysis)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    count = lambda s: sum(i.status == s for i in items)  # noqa: E731
    return MatchOut(cv_id=cv.id, jd_id=jd.id, score=matching.score(items), items=items,
                    covered=count("covered"), weak=count("weak"), gaps=count("gap"))
