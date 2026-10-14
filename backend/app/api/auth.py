import secrets
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.api.deps import current_user_id
from app.models import CV, JobDescription, PasswordResetToken, RefreshToken, TailoringJob, User
from app.services import billing, login_limiter, mailer, security, storage

router = APIRouter(prefix="/v1/auth", tags=["auth"])

MIN_PASSWORD = 8


class SignupIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        try:
            return validate_email(v.strip(), check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            raise ValueError("Enter a valid email address.") from None

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD:
            raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
        return v


class UserOut(BaseModel):
    id: str
    email: str


class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class AccessOut(BaseModel):
    access_token: str


BAD_LOGIN = "Incorrect email or password."
# Verified against when the email is unknown, so response time does not reveal whether an account exists.
_DUMMY_HASH = security.hash_password("not-a-real-password")


def _issue_tokens(db: Session, user: User) -> AuthOut:
    refresh = security.create_refresh_token(user.id)
    db.add(RefreshToken(token_hash=security.hash_token(refresh), user_id=user.id))
    db.commit()
    return AuthOut(user=UserOut(id=user.id, email=user.email),
                   access_token=security.create_access_token(user.id), refresh_token=refresh)


@router.post("/signup", status_code=201, response_model=AuthOut)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> AuthOut:
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=body.email, password_hash=security.hash_password(body.password))
    db.add(user)
    db.commit()
    return _issue_tokens(db, user)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> AuthOut:
    email = body.email.strip().lower()
    if login_limiter.is_blocked(email):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 15 minutes.")
    user = db.scalar(select(User).where(User.email == email))
    ok = security.verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok:
        login_limiter.record_failure(email)
        raise HTTPException(status_code=401, detail=BAD_LOGIN)
    login_limiter.reset(email)
    return _issue_tokens(db, user)


def _stored_token(db: Session, token: str) -> RefreshToken | None:
    if security.decode_token(token, "refresh") is None:
        return None
    row = db.get(RefreshToken, security.hash_token(token))
    return row if row is not None and not row.revoked else None


@router.post("/refresh", response_model=AccessOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> AccessOut:
    row = _stored_token(db, body.refresh_token)
    if row is None:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return AccessOut(access_token=security.create_access_token(row.user_id))


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)) -> None:
    row = _stored_token(db, body.refresh_token)
    if row is not None:
        row.revoked = True
        db.commit()


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD:
            raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
        return v


class MessageOut(BaseModel):
    message: str


FORGOT_REPLY = "If an account exists for that email, we've sent a link to reset your password."
BAD_RESET = "This reset link is invalid or has expired. Request a new one."


def _send_reset_email(email: str, token: str) -> None:
    link = f"{settings.frontend_url.rstrip('/')}/?reset_token={token}"
    mailer.send_email(
        email, "Reset your ShortlistMe password",
        f"We got a request to reset your password.\n\nOpen this link within {settings.reset_token_minutes} minutes:\n"
        f"{link}\n\nIf you didn't ask for this, you can ignore this email.",
    )


@router.post("/forgot-password", status_code=202, response_model=MessageOut)
def forgot_password(body: ForgotIn, background: BackgroundTasks, db: Session = Depends(get_db)) -> MessageOut:
    # Same reply whether or not the account exists, so this can't be used to find registered emails.
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        # A newer request replaces any older unused link.
        db.execute(update(PasswordResetToken)
                   .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False))
                   .values(used=True))
        token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            token_hash=security.hash_token(token), user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_minutes)))
        db.commit()
        background.add_task(_send_reset_email, user.email, token)
    return MessageOut(message=FORGOT_REPLY)


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetIn, db: Session = Depends(get_db)) -> MessageOut:
    row = db.get(PasswordResetToken, security.hash_token(body.token))
    if row is None or row.used:
        raise HTTPException(status_code=400, detail=BAD_RESET)
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail=BAD_RESET)
    user = db.get(User, row.user_id)
    user.password_hash = security.hash_password(body.password)
    row.used = True
    # Anyone holding an old session is signed out.
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
    login_limiter.reset(user.email)
    return MessageOut(message="Your password has been updated. You can log in now.")


class DeleteAccountIn(BaseModel):
    password: str


@router.delete("/account", status_code=204)
def delete_account(body: DeleteAccountIn, user_id: str = Depends(current_user_id), db: Session = Depends(get_db)) -> None:
    """Erase the account and everything stored for it (UK GDPR right to erasure). Requires the password."""
    user = db.get(User, user_id)
    if not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=403, detail="That password is not correct.")
    for cv in db.scalars(select(CV).where(CV.user_id == user_id)):
        try:
            storage.delete(cv.storage_key)
        except (ValueError, OSError):
            pass
    billing.delete_customer(user)
    for model in (TailoringJob, JobDescription, CV, RefreshToken, PasswordResetToken):
        db.execute(delete(model).where(model.user_id == user_id))
    db.delete(user)
    db.commit()
