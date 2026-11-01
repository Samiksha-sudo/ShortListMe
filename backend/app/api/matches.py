from pydantic import BaseModel
from rest_framework.response import Response

from app.api.deps import endpoint, owned
from app.api.errors import ApiError, parse
from app.models import CV, JobDescription
from app.schemas.cv import ParsedCV
from app.schemas.match import MatchOut
from app.services import jd_analysis, matching
from app.services.llm import LLMError


class MatchIn(BaseModel):
    cv_id: str
    jd_id: str


@endpoint(["POST"], auth="llm")
def create_match(request, user_id):
    body = parse(MatchIn, request.data)
    cv = owned(CV, body.cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise ApiError(404, "CV not found.")
    jd = owned(JobDescription, body.jd_id, user_id)
    if jd is None:
        raise ApiError(404, "Job description not found.")
    try:
        analysis, _ = jd_analysis.analyse(jd)
        items = matching.match(ParsedCV.model_validate(cv.parsed), analysis)
    except LLMError as exc:
        raise ApiError(502, str(exc)) from exc
    count = lambda s: sum(i.status == s for i in items)  # noqa: E731
    out = MatchOut(cv_id=cv.id, jd_id=jd.id, score=matching.score(items), items=items,
                   covered=count("covered"), weak=count("weak"), gaps=count("gap"))
    return Response(out.model_dump(mode="json"))
