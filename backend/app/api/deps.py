from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import User
from app.services import rate_limiter, security

_bearer = HTTPBearer(auto_error=False)


def current_user_id(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                    db: Session = Depends(get_db)) -> str:
    user_id = security.decode_token(creds.credentials, "access") if creds else None
    if user_id is None or db.get(User, user_id) is None:
        raise HTTPException(status_code=401, detail="Please log in to continue.",
                            headers={"WWW-Authenticate": "Bearer"})
    return user_id


def owned(db: Session, model, row_id: str, user_id: str):
    """The row if it exists and belongs to this user, else None. Callers answer 404 for both, so ids can't be probed."""
    row = db.get(model, row_id)
    return row if row is not None and row.user_id == user_id else None


def rate_limit(bucket: str, limit_attr: str):
    """Dependency: per-user cap on a group of endpoints, returning the user id."""
    def dep(user_id: str = Depends(current_user_id)) -> str:
        wait = rate_limiter.check(f"{bucket}:{user_id}", getattr(settings, limit_attr), settings.rate_limit_window_seconds)
        if wait:
            raise HTTPException(status_code=429, detail=f"You're going a bit fast. Try again in {wait} seconds.",
                                headers={"Retry-After": str(wait)})
        return user_id
    return dep


# Calls that reach the LLM cost money; uploads cost storage and parsing time.
llm_user = rate_limit("llm", "rate_limit_llm")
upload_user = rate_limit("upload", "rate_limit_upload")
