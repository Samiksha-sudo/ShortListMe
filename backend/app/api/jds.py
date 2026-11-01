import hashlib

from pydantic import BaseModel, field_validator
from rest_framework.response import Response

from app.api.deps import endpoint, owned
from app.api.errors import ApiError, parse
from app.models import JobDescription
from app.services import jd_analysis
from app.services.llm import LLMError

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


def _out(jd: JobDescription) -> dict:
    return {"jd_id": jd.id, "text": jd.text, "text_hash": jd.text_hash, "created_at": jd.created_at}


@endpoint(["POST"])
def create_jd(request, user_id):
    body = parse(JDIn, request.data)
    jd = JobDescription.objects.create(user_id=user_id, text=body.text,
                                       text_hash=hashlib.sha256(body.text.encode()).hexdigest())
    return Response(_out(jd), status=201)


@endpoint(["POST"], auth="llm")
def analyse_jd(request, user_id, jd_id):
    jd = owned(JobDescription, jd_id, user_id)
    if jd is None:
        raise ApiError(404, "Job description not found.")
    try:
        result, cached = jd_analysis.analyse(jd)
    except LLMError as exc:
        raise ApiError(502, str(exc)) from exc
    return Response({"jd_id": jd.id, "cached": cached, **result.model_dump(mode="json")})


@endpoint(["GET"])
def get_jd(request, user_id, jd_id):
    jd = owned(JobDescription, jd_id, user_id)
    if jd is None:
        raise ApiError(404, "Job description not found.")
    return Response(_out(jd))
