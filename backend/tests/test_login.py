import jwt
import pytest

from app.core.config import settings
from app.services import login_limiter, security
from tests.test_signup import signup


@pytest.fixture(autouse=True)
def _fresh_limiter():
    login_limiter.clear_all()


def login(client, email="jane@example.com", password="correct-horse"):
    return client.post("/v1/auth/login", json={"email": email, "password": password})


def test_login_success_returns_tokens(client):
    signup(client)
    res = login(client, email="JANE@example.com")
    assert res.status_code == 200
    body = res.json()
    assert body["user"]["email"] == "jane@example.com"
    assert security.decode_token(body["access_token"], "access") == body["user"]["id"]
    assert security.decode_token(body["refresh_token"], "refresh") == body["user"]["id"]


def test_wrong_password_and_unknown_email_give_same_message(client):
    signup(client)
    wrong = login(client, password="wrong-password")
    unknown = login(client, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_rate_limited_after_five_failures(client):
    signup(client)
    for _ in range(5):
        assert login(client, password="wrong-password").status_code == 401
    assert login(client, password="wrong-password").status_code == 429
    # even the right password is refused while blocked
    assert login(client).status_code == 429


def test_successful_login_resets_failure_count(client):
    signup(client)
    for _ in range(4):
        login(client, password="wrong-password")
    assert login(client).status_code == 200
    for _ in range(4):
        assert login(client, password="wrong-password").status_code == 401


def test_refresh_issues_new_access_token(client):
    refresh_token = signup(client).json()["refresh_token"]
    res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    assert security.decode_token(res.json()["access_token"], "access") is not None


def test_refresh_rejects_access_token_and_garbage(client):
    access = signup(client).json()["access_token"]
    assert client.post("/v1/auth/refresh", json={"refresh_token": access}).status_code == 401
    assert client.post("/v1/auth/refresh", json={"refresh_token": "garbage"}).status_code == 401


def test_expired_refresh_token_rejected(client):
    user_id = signup(client).json()["user"]["id"]
    expired = jwt.encode({"sub": user_id, "type": "refresh", "exp": 1}, settings.jwt_secret, algorithm="HS256")
    assert client.post("/v1/auth/refresh", json={"refresh_token": expired}).status_code == 401


def test_logout_invalidates_refresh_token(client):
    refresh_token = signup(client).json()["refresh_token"]
    assert client.post("/v1/auth/logout", json={"refresh_token": refresh_token}).status_code == 204
    res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 401


def test_two_logins_get_distinct_refresh_tokens(client):
    signup(client)
    a = login(client).json()["refresh_token"]
    b = login(client).json()["refresh_token"]
    assert a != b
