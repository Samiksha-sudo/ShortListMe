import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user_id
from app.db import get_db
from app.models import User
from app.services import billing

router = APIRouter(prefix="/v1/billing", tags=["billing"])


class UsageOut(BaseModel):
    plan: str
    used: int
    limit: int
    remaining: int


class UrlOut(BaseModel):
    url: str


@router.get("", response_model=UsageOut)
def get_usage(db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> dict:
    return billing.usage(db, db.get(User, user_id))


@router.post("/checkout", response_model=UrlOut)
def checkout(db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> UrlOut:
    try:
        return UrlOut(url=billing.checkout_url(db, db.get(User, user_id)))
    except billing.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/portal", response_model=UrlOut)
def portal(db: Session = Depends(get_db), user_id: str = Depends(current_user_id)) -> UrlOut:
    try:
        return UrlOut(url=billing.portal_url(db.get(User, user_id)))
    except billing.BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()
    if not billing.verify_signature(payload, request.headers.get("stripe-signature", "")):
        raise HTTPException(status_code=400, detail="Invalid signature.")
    try:
        event = json.loads(payload)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload.") from None
    billing.apply_event(db, event)
    return {"received": True}
