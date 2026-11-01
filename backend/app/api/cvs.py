import uuid

from django.http import HttpResponse
from pydantic import BaseModel
from rest_framework.response import Response

from app.api.deps import endpoint, owned
from app.api.errors import ApiError, parse
from app.models import CV
from app.schemas.cv import ParsedCV
from app.services import exporting, storage
from app.services.docx_validation import DOCX_MIME, MAX_BYTES, InvalidCV, validate_docx
from app.services.parsing.docx_parser import parse_docx


@endpoint(["POST"], auth="upload")
def upload_cv(request, user_id):
    file = request.FILES.get("file")
    if file is None:
        raise ApiError(422, [{"loc": ["body", "file"], "msg": "Field required", "type": "missing"}])
    data = file.read(MAX_BYTES + 1)
    filename = file.name or "cv.docx"
    try:
        validate_docx(filename, data)
    except InvalidCV as e:
        raise ApiError(422, str(e)) from None

    cv_id = str(uuid.uuid4())
    try:
        parsed = parse_docx(data, cv_id, filename)
    except InvalidCV as e:
        raise ApiError(422, str(e)) from None

    key = storage.save(f"cvs/{cv_id}.docx", data)
    CV.objects.create(id=cv_id, user_id=user_id, filename=filename[:255], mime=DOCX_MIME, size=len(data),
                      storage_key=key, parsed=parsed.model_dump(mode="json"))
    return Response({"cv_id": cv_id, "filename": filename, "size": len(data), "blocks": len(parsed.blocks),
                     "editable": sum(b.editable for b in parsed.blocks)}, status=201)


class ExportIn(BaseModel):
    # block_id -> final text (the suggestion, or the user's own edit); only accepted changes are sent
    edits: dict[str, str] = {}


def _parsed_cv(cv_id: str, user_id: str) -> tuple[CV, ParsedCV]:
    cv = owned(CV, cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise ApiError(404, "CV not found.")
    return cv, ParsedCV.model_validate(cv.parsed)


def _download(data: bytes, media_type: str, cv: CV, suffix: str) -> HttpResponse:
    stem = cv.filename.rsplit(".", 1)[0] or "cv"
    return HttpResponse(data, content_type=media_type,
                        headers={"Content-Disposition": f'attachment; filename="{stem}-tailored.{suffix}"'})


@endpoint(["POST"])
def export_docx(request, user_id, cv_id):
    cv, parsed = _parsed_cv(cv_id, user_id)
    body = parse(ExportIn, request.data)
    try:
        original = storage.load(cv.storage_key)
    except FileNotFoundError:
        raise ApiError(404, "The original CV file is no longer available.") from None
    try:
        edits = exporting.resolve_edits(parsed, body.edits)
        data = exporting.apply_edits(original, parsed, edits)
    except exporting.ExportError as e:
        raise ApiError(422, str(e)) from None
    return _download(data, DOCX_MIME, cv, "docx")


@endpoint(["POST"])
def export_pdf(request, user_id, cv_id):
    cv, parsed = _parsed_cv(cv_id, user_id)
    body = parse(ExportIn, request.data)
    try:
        data = exporting.render_pdf(parsed, exporting.resolve_edits(parsed, body.edits))
    except exporting.ExportError as e:
        raise ApiError(422, str(e)) from None
    return _download(data, "application/pdf", cv, "pdf")


@endpoint(["GET"])
def get_cv(request, user_id, cv_id):
    _, parsed = _parsed_cv(cv_id, user_id)
    return Response(parsed.model_dump(mode="json"))
