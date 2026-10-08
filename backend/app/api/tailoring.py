from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import current_user_id, llm_user, owned
from app.db import get_db, get_session_factory
from app.models import CV, JobDescription, TailoringJob, User
from app.services import billing, tailoring

router = APIRouter(prefix="/v1/tailoring", tags=["tailoring"])


class TailorIn(BaseModel):
    cv_id: str
    jd_id: str


class JobOut(BaseModel):
    job_id: str
    status: str
    step: str
    steps: list[str]
    error: str | None = None
    result: dict | None = None
    created_at: datetime


def _out(job: TailoringJob) -> JobOut:
    return JobOut(job_id=job.id, status=job.status, step=job.step, steps=tailoring.STEPS, error=job.error,
                  result=job.result, created_at=job.created_at)


@router.post("", status_code=202, response_model=JobOut)
def start(body: TailorIn, background: BackgroundTasks, db: Session = Depends(get_db),
          factory: sessionmaker = Depends(get_session_factory),
          user_id: str = Depends(llm_user)) -> JobOut:
    cv = owned(db, CV, body.cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    if owned(db, JobDescription, body.jd_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Job description not found.")
    quota = billing.usage(db, db.get(User, user_id))
    if quota["plan"] != "admin" and quota["remaining"] == 0:
        detail = ("You've used all your tailorings for this month." if quota["plan"] == "pro"
                  else f"You've used your {quota['limit']} free tailorings. Upgrade to keep going.")
        raise HTTPException(status_code=402, detail=detail)
    job = TailoringJob(user_id=user_id, cv_id=body.cv_id, jd_id=body.jd_id)
    db.add(job)
    db.commit()
    background.add_task(tailoring.run, job.id, factory)
    return _out(job)


@router.get("/{job_id}", response_model=JobOut)
def status(job_id: str, db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> JobOut:
    job = owned(db, TailoringJob, job_id, user_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tailoring job not found.")
    return _out(job)
