import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CV
from app.services import storage
from app.services.docx_validation import DOCX_MIME, MAX_BYTES, InvalidCV, validate_docx

router = APIRouter(prefix="/v1/cvs", tags=["cvs"])


class CVOut(BaseModel):
    cv_id: str
    filename: str
    size: int


@router.post("", status_code=201, response_model=CVOut)
async def upload_cv(file: UploadFile, db: Session = Depends(get_db)) -> CVOut:
    data = await file.read(MAX_BYTES + 1)
    filename = file.filename or "cv.docx"
    try:
        validate_docx(filename, data)
    except InvalidCV as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    cv_id = str(uuid.uuid4())
    key = storage.save(f"cvs/{cv_id}.docx", data)
    db.add(CV(id=cv_id, filename=filename[:255], mime=DOCX_MIME, size=len(data), storage_key=key))
    db.commit()
    return CVOut(cv_id=cv_id, filename=filename, size=len(data))
