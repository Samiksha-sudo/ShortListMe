import secrets
from datetime import datetime, timedelta, timezone

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, field_validator
from rest_framework.response import Response

from app.api.deps import endpoint
from app.api.errors import ApiError, parse
from app.core.config import settings
from app.models import CV, JobDescription, PasswordResetToken, RefreshToken, TailoringJob, User
from app.services import background, billing, login_limiter, mailer, security, storage

MIN_PASSWORD = 8


def _check_password(v: str) -> str:
    if len(v) < MIN_PASSWORD:
        raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
    return v


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

    _password = field_validator("password")(classmethod(lambda cls, v: _check_password(v)))


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    token: str
    password: str

    _password = field_validator("password")(classmethod(lambda cls, v: _check_password(v)))


class DeleteAccountIn(BaseModel):
    password: str


BAD_LOGIN = "Incorrect email or password."
# Verified against when the email is unknown, so response time does not reveal whether an account exists.
_DUMMY_HASH = security.hash_password("not-a-real-password")


def _issue_tokens(user: User) -> dict:
    refresh = security.create_refresh_token(user.id)
    RefreshToken.objects.create(token_hash=security.hash_token(refresh), user_id=user.id)
    return {"user": {"id": user.id, "email": user.email},
            "access_token": security.create_access_token(user.id), "refresh_token": refresh}


@endpoint(["POST"], auth=None)
def signup(request):
    body = parse(SignupIn, request.data)
    if User.objects.filter(email=body.email).exists():
        raise ApiError(409, "An account with this email already exists.")
    user = User.objects.create(email=body.email, password_hash=security.hash_password(body.password))
    return Response(_issue_tokens(user), status=201)


@endpoint(["POST"], auth=None)
def login(request):
    body = parse(LoginIn, request.data)
    email = body.email.strip().lower()
    if login_limiter.is_blocked(email):
        raise ApiError(429, "Too many failed attempts. Try again in 15 minutes.")
    user = User.objects.filter(email=email).first()
    ok = security.verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok:
        login_limiter.record_failure(email)
        raise ApiError(401, BAD_LOGIN)
    login_limiter.reset(email)
    return Response(_issue_tokens(user))


def _stored_token(token: str) -> RefreshToken | None:
    if security.decode_token(token, "refresh") is None:
        return None
    row = RefreshToken.objects.filter(pk=security.hash_token(token)).first()
    return row if row is not None and not row.revoked else None


@endpoint(["POST"], auth=None)
def refresh(request):
    row = _stored_token(parse(RefreshIn, request.data).refresh_token)
    if row is None:
        raise ApiError(401, "Session expired. Please log in again.")
    return Response({"access_token": security.create_access_token(row.user_id)})


@endpoint(["POST"], auth=None)
def logout(request):
    row = _stored_token(parse(RefreshIn, request.data).refresh_token)
    if row is not None:
        row.revoked = True
        row.save()
    return Response(status=204)


FORGOT_REPLY = "If an account exists for that email, we've sent a link to reset your password."
BAD_RESET = "This reset link is invalid or has expired. Request a new one."


def _send_reset_email(email: str, token: str) -> None:
    link = f"{settings.frontend_url.rstrip('/')}/?reset_token={token}"
    mailer.send_email(
        email, "Reset your ShortlistMe password",
        f"We got a request to reset your password.\n\nOpen this link within {settings.reset_token_minutes} minutes:\n"
        f"{link}\n\nIf you didn't ask for this, you can ignore this email.",
    )


@endpoint(["POST"], auth=None)
def forgot_password(request):
    # Same reply whether or not the account exists, so this can't be used to find registered emails.
    email = parse(ForgotIn, request.data).email.strip().lower()
    user = User.objects.filter(email=email).first()
    if user is not None:
        # A newer request replaces any older unused link.
        PasswordResetToken.objects.filter(user_id=user.id, used=False).update(used=True)
        token = secrets.token_urlsafe(32)
        PasswordResetToken.objects.create(
            token_hash=security.hash_token(token), user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_minutes))
        background.run(_send_reset_email, user.email, token)
    return Response({"message": FORGOT_REPLY}, status=202)


@endpoint(["POST"], auth=None)
def reset_password(request):
    body = parse(ResetIn, request.data)
    row = PasswordResetToken.objects.filter(pk=security.hash_token(body.token)).first()
    if row is None or row.used or row.expires_at < datetime.now(timezone.utc):
        raise ApiError(400, BAD_RESET)
    user = User.objects.get(pk=row.user_id)
    user.password_hash = security.hash_password(body.password)
    user.save()
    row.used = True
    row.save()
    # Anyone holding an old session is signed out.
    RefreshToken.objects.filter(user_id=user.id).update(revoked=True)
    login_limiter.reset(user.email)
    return Response({"message": "Your password has been updated. You can log in now."})


@endpoint(["DELETE"])
def delete_account(request, user_id):
    """Erase the account and everything stored for it (UK GDPR right to erasure). Requires the password."""
    body = parse(DeleteAccountIn, request.data)
    user = User.objects.get(pk=user_id)
    if not security.verify_password(body.password, user.password_hash):
        raise ApiError(403, "That password is not correct.")
    for cv in CV.objects.filter(user_id=user_id):
        try:
            storage.delete(cv.storage_key)
        except (ValueError, OSError):
            pass
    billing.delete_customer(user)
    for model in (TailoringJob, JobDescription, CV, RefreshToken, PasswordResetToken):
        model.objects.filter(user_id=user_id).delete()
    user.delete()
    return Response(status=204)
