import logging

from app.models import CV, JobDescription, TailoringJob
from app.schemas.cv import ParsedCV
from app.services import jd_analysis, matching, rewriting
from app.services.llm import LLMError

logger = logging.getLogger(__name__)

STEPS = ["analysing", "matching", "rewriting"]


def _set(job: TailoringJob, **fields) -> None:
    for k, v in fields.items():
        setattr(job, k, v)
    job.save()


def run(job_id: str) -> None:
    """Run the whole pipeline for one job, recording progress; never raises (failures are stored on the job)."""
    job = TailoringJob.objects.filter(pk=job_id).first()
    if job is None:
        return
    try:
        cv = CV.objects.filter(pk=job.cv_id).first()
        jd = JobDescription.objects.filter(pk=job.jd_id).first()
        if cv is None or cv.parsed is None or jd is None:
            raise LLMError("The CV or job description no longer exists.")
        parsed = ParsedCV.model_validate(cv.parsed)

        _set(job, status="running", step="analysing")
        analysis, _ = jd_analysis.analyse(jd)

        _set(job, step="matching")
        items = matching.match(parsed, analysis)
        count = lambda s: sum(i.status == s for i in items)  # noqa: E731
        match = {"score": matching.score(items), "items": [i.model_dump() for i in items],
                 "covered": count("covered"), "weak": count("weak"), "gaps": count("gap")}

        _set(job, step="rewriting")
        edits, dropped = rewriting.propose(parsed, analysis, items)

        _set(job, status="done", step="done",
             result={"match": match, "edits": [e.model_dump() for e in edits],
                     "dropped": [d.model_dump() for d in dropped]})
    except LLMError as exc:
        _set(job, status="failed", error=str(exc)[:500])
    except Exception:  # noqa: BLE001 - a background task must not die silently
        logger.exception("tailoring job %s crashed", job_id)
        _set(job, status="failed", error="Something went wrong while tailoring your CV. Please try again.")
