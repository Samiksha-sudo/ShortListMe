import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def _token(user_id: str, kind: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    # jti keeps two tokens issued in the same second distinct
    return jwt.encode({"sub": user_id, "type": kind, "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex},
                      settings.jwt_secret, algorithm="HS256")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_token(token: str, kind: str) -> str | None:
    """Return the user id if the token is valid, unexpired and of the given kind, else None."""
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return claims["sub"] if claims.get("type") == kind else None


def create_access_token(user_id: str) -> str:
    return _token(user_id, "access", timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user_id: str) -> str:
    return _token(user_id, "refresh", timedelta(days=settings.refresh_token_days))
