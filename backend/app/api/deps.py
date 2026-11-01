from functools import wraps

from rest_framework.decorators import api_view

from app.api.errors import ApiError
from app.core.config import settings
from app.models import User
from app.services import rate_limiter, security


def current_user_id(request) -> str:
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header[:7].lower() == "bearer " else ""
    user_id = security.decode_token(token, "access") if token else None
    if user_id is None or not User.objects.filter(pk=user_id).exists():
        raise ApiError(401, "Please log in to continue.", {"WWW-Authenticate": "Bearer"})
    return user_id


def owned(model, row_id: str, user_id: str):
    """The row if it exists and belongs to this user, else None. Callers answer 404 for both, so ids can't be probed."""
    row = model.objects.filter(pk=row_id).first()
    return row if row is not None and row.user_id == user_id else None


def _rate_limited(bucket: str, limit_attr: str, request) -> str:
    user_id = current_user_id(request)
    wait = rate_limiter.check(f"{bucket}:{user_id}", getattr(settings, limit_attr), settings.rate_limit_window_seconds)
    if wait:
        raise ApiError(429, f"You're going a bit fast. Try again in {wait} seconds.", {"Retry-After": str(wait)})
    return user_id


def endpoint(methods, auth: str | None = "user"):
    """A JSON endpoint. `auth` is None (public), "user", "llm" or "upload" (the last two add a per-user rate limit).
    When auth is set the view receives the user id as its second argument."""
    def deco(fn):
        @api_view(methods)
        @wraps(fn)
        def view(request, *args, **kwargs):
            if auth is None:
                return fn(request, *args, **kwargs)
            # Calls that reach the LLM cost money; uploads cost storage and parsing time.
            user_id = (current_user_id(request) if auth == "user"
                       else _rate_limited(auth, "rate_limit_llm" if auth == "llm" else "rate_limit_upload", request))
            return fn(request, user_id, *args, **kwargs)
        view.cls.authentication_classes, view.cls.permission_classes = [], []
        return view
    return deco
