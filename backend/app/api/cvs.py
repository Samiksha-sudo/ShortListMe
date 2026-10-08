import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user_id, owned, upload_user
from app.db import get_db
from app.models import CV
from app.schemas.cv import ParsedCV
from app.services import exporting, storage
from app.services.parsing.docx_parser import parse_docx
from app.services.docx_validation import DOCX_MIME, MAX_BYTES, InvalidCV, validate_docx

router = APIRouter(prefix="/v1/cvs", tags=["cvs"])


class CVOut(BaseModel):
    cv_id: str
    filename: str
    size: int
    blocks: int
    editable: int


@router.post("", status_code=201, response_model=CVOut)
async def upload_cv(file: UploadFile, db: Session = Depends(get_db),
                    user_id: str = Depends(upload_user)) -> CVOut:
    data = await file.read(MAX_BYTES + 1)
    filename = file.filename or "cv.docx"
    try:
        validate_docx(filename, data)
    except InvalidCV as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    cv_id = str(uuid.uuid4())
    try:
        parsed = parse_docx(data, cv_id, filename)
    except InvalidCV as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    key = storage.save(f"cvs/{cv_id}.docx", data)
    db.add(CV(id=cv_id, user_id=user_id, filename=filename[:255], mime=DOCX_MIME, size=len(data), storage_key=key,
              parsed=parsed.model_dump(mode="json")))
    db.commit()
    return CVOut(cv_id=cv_id, filename=filename, size=len(data),
                 blocks=len(parsed.blocks), editable=sum(b.editable for b in parsed.blocks))


class ExportIn(BaseModel):
    # block_id -> final text (the suggestion, or the user's own edit); only accepted changes are sent
    edits: dict[str, str] = {}


@router.post("/{cv_id}/export.docx")
def export_docx(cv_id: str, body: ExportIn, db: Session = Depends(get_db),
                user_id: str = Depends(current_user_id)) -> Response:
    cv = owned(db, CV, cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    parsed = ParsedCV.model_validate(cv.parsed)
    try:
        original = storage.load(cv.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="The original CV file is no longer available.") from None
    try:
        edits = exporting.resolve_edits(parsed, body.edits)
        data = exporting.apply_edits(original, parsed, edits)
    except exporting.ExportError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    stem = cv.filename.rsplit(".", 1)[0] or "cv"
    return Response(content=data, media_type=DOCX_MIME,
                    headers={"Content-Disposition": f'attachment; filename="{stem}-tailored.docx"'})


@router.post("/{cv_id}/export.pdf")
def export_pdf(cv_id: str, body: ExportIn, db: Session = Depends(get_db),
                user_id: str = Depends(current_user_id)) -> Response:
    cv = owned(db, CV, cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    parsed = ParsedCV.model_validate(cv.parsed)
    try:
        data = exporting.render_pdf(parsed, exporting.resolve_edits(parsed, body.edits))
    except exporting.ExportError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
    stem = cv.filename.rsplit(".", 1)[0] or "cv"
    return Response(content=data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{stem}-tailored.pdf"'})


@router.get("/{cv_id}", response_model=ParsedCV)
def get_cv(cv_id: str, db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> ParsedCV:
    cv = owned(db, CV, cv_id, user_id)
    if cv is None or cv.parsed is None:
        raise HTTPException(status_code=404, detail="CV not found.")
    return ParsedCV.model_validate(cv.parsed)
