import jwt

from app.core.config import settings
from app.db import get_db
from app.main import app
from app.models import User


def signup(client, email="Jane@Example.com", password="correct-horse"):
    return client.post("/v1/auth/signup", json={"email": email, "password": password})


def test_signup_returns_tokens_and_user(client):
    res = signup(client)
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "jane@example.com"
    assert "password_hash" not in body["user"]
    claims = jwt.decode(body["access_token"], settings.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == body["user"]["id"] and claims["type"] == "access"
    refresh = jwt.decode(body["refresh_token"], settings.jwt_secret, algorithms=["HS256"])
    assert refresh["type"] == "refresh"


def test_password_is_stored_hashed(client):
    signup(client, password="correct-horse")
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).filter_by(email="jane@example.com").one()
    assert user.password_hash != "correct-horse" and user.password_hash.startswith("$argon2")


def test_duplicate_email_rejected_case_insensitively(client):
    assert signup(client, "jane@example.com").status_code == 201
    res = signup(client, "JANE@example.com")
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_weak_password_rejected(client):
    res = signup(client, password="short")
    assert res.status_code == 422
    assert "at least 8" in res.text


def test_bad_email_rejected(client):
    res = signup(client, email="not-an-email")
    assert res.status_code == 422
    assert "valid email" in res.text


def test_delete_account_erases_user_and_data(client):
    from tests import samples
    from tests.test_upload_cv import post
    cv_id = post(client, "cv.docx", samples.single_column()).json()["cv_id"]
    assert client.request("DELETE", "/v1/auth/account", json={"password": "wrong-password"}).status_code == 403
    assert client.request("DELETE", "/v1/auth/account", json={"password": "correct-horse"}).status_code == 204
    assert client.get(f"/v1/cvs/{cv_id}").status_code == 401  # token no longer maps to a user
    login = client.post("/v1/auth/login", json={"email": "default@example.com", "password": "correct-horse"})
    assert login.status_code == 401
