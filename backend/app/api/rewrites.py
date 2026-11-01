from pydantic import BaseModel
from rest_framework.response import Response

from app.api.deps import endpoint, owned
from app.api.errors import ApiError, parse
from app.models import CV, JobDescription
from app.schemas.cv import ParsedCV
from app.schemas.rewrite import RewriteOut
from app.services import jd_analysis, rewriting
from app.services.llm import LLMError


class RewriteIn(BaseModel):
    cv_id: str
    jd_id: str


@endpoint(["POST"], auth="llm")
def propose_rewrites(request, user_id):
    body = parse(RewriteIn, request.data)
    cv = owned(CV, body.cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise ApiError(404, "CV not found.")
    jd = owned(JobDescription, body.jd_id, user_id)
    if jd is None:
        raise ApiError(404, "Job description not found.")
    try:
        analysis, _ = jd_analysis.analyse(jd)
        edits, dropped = rewriting.propose(ParsedCV.model_validate(cv.parsed), analysis)
    except LLMError as exc:
        raise ApiError(502, str(exc)) from exc
    return Response(RewriteOut(cv_id=cv.id, jd_id=jd.id, edits=edits, dropped=dropped).model_dump(mode="json"))
