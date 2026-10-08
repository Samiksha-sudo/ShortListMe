import logging

from sqlalchemy.orm import Session, sessionmaker

from app.models import CV, JobDescription, TailoringJob
from app.schemas.cv import ParsedCV
from app.services import jd_analysis, matching, rewriting
from app.services.llm import LLMError

logger = logging.getLogger(__name__)

STEPS = ["analysing", "matching", "rewriting"]


def _set(db: Session, job: TailoringJob, **fields) -> None:
    for k, v in fields.items():
        setattr(job, k, v)
    db.commit()


def run(job_id: str, factory: sessionmaker) -> None:
    """Run the whole pipeline for one job, recording progress; never raises (failures are stored on the job)."""
    with factory() as db:
        job = db.get(TailoringJob, job_id)
        if job is None:
            return
        try:
            cv = db.get(CV, job.cv_id)
            jd = db.get(JobDescription, job.jd_id)
            if cv is None or cv.parsed is None or jd is None:
                raise LLMError("The CV or job description no longer exists.")
            parsed = ParsedCV.model_validate(cv.parsed)

            _set(db, job, status="running", step="analysing")
            analysis, _ = jd_analysis.analyse(db, jd)

            _set(db, job, step="matching")
            items = matching.match(parsed, analysis)
            count = lambda s: sum(i.status == s for i in items)  # noqa: E731
            match = {"score": matching.score(items), "items": [i.model_dump() for i in items],
                     "covered": count("covered"), "weak": count("weak"), "gaps": count("gap")}

            _set(db, job, step="rewriting")
            edits, dropped = rewriting.propose(parsed, analysis, items)

            _set(db, job, status="done", step="done",
                 result={"match": match, "edits": [e.model_dump() for e in edits],
                         "dropped": [d.model_dump() for d in dropped]})
        except LLMError as exc:
            db.rollback()
            _set(db, job, status="failed", error=str(exc)[:500])
        except Exception:  # noqa: BLE001 - a background task must not die silently
            logger.exception("tailoring job %s crashed", job_id)
            db.rollback()
            _set(db, job, status="failed", error="Something went wrong while tailoring your CV. Please try again.")
