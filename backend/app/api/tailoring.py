from pydantic import BaseModel
from rest_framework.response import Response

from app.api.deps import endpoint, owned
from app.api.errors import ApiError, parse
from app.models import CV, JobDescription, TailoringJob, User
from app.services import background, billing, tailoring


class TailorIn(BaseModel):
    cv_id: str
    jd_id: str


def _out(job: TailoringJob) -> dict:
    return {"job_id": job.id, "status": job.status, "step": job.step, "steps": tailoring.STEPS, "error": job.error,
            "result": job.result, "created_at": job.created_at}


@endpoint(["POST"], auth="llm")
def start(request, user_id):
    body = parse(TailorIn, request.data)
    cv = owned(CV, body.cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise ApiError(404, "CV not found.")
    if owned(JobDescription, body.jd_id, user_id) is None:
        raise ApiError(404, "Job description not found.")
    quota = billing.usage(User.objects.get(pk=user_id))
    if quota["plan"] != "admin" and quota["remaining"] == 0:
        detail = ("You've used all your tailorings for this month." if quota["plan"] == "pro"
                  else f"You've used your {quota['limit']} free tailorings. Upgrade to keep going.")
        raise ApiError(402, detail)
    job = TailoringJob.objects.create(user_id=user_id, cv_id=body.cv_id, jd_id=body.jd_id)
    background.run(tailoring.run, job.id)
    job.refresh_from_db()  # an inline (test) run has already moved it on; report the current state
    return Response(_out(job), status=202)


@endpoint(["GET"])
def status(request, user_id, job_id):
    job = owned(TailoringJob, job_id, user_id)
    if job is None:
        raise ApiError(404, "Tailoring job not found.")
    return Response(_out(job))
