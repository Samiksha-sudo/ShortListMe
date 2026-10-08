from datetime import datetime, timedelta, timezone

import pytest

from app.api import auth as auth_api
from app.db import get_db
from app.main import app
from app.models import PasswordResetToken
from app.services import login_limiter, mailer
from tests.test_signup import signup


@pytest.fixture(autouse=True)
def outbox(monkeypatch):
    login_limiter.clear_all()
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def forgot(client, email="jane@example.com"):
    return client.post("/v1/auth/forgot-password", json={"email": email})


def token_from(sent) -> str:
    return sent[-1][2].split("reset_token=")[1].split()[0]


def reset(client, token, password="brand-new-pass"):
    return client.post("/v1/auth/reset-password", json={"token": token, "password": password})


def db():
    return next(app.dependency_overrides[get_db]())


def test_happy_path_changes_password(client, outbox):
    signup(client)
    assert forgot(client).status_code == 202
    assert len(outbox) == 1 and outbox[0][0] == "jane@example.com"
    assert reset(client, token_from(outbox)).status_code == 200
    login = lambda p: client.post("/v1/auth/login", json={"email": "jane@example.com", "password": p})
    assert login("brand-new-pass").status_code == 200
    assert login("correct-horse").status_code == 401


def test_unknown_email_gets_same_reply_and_no_email(client, outbox):
    signup(client)
    known, unknown = forgot(client), forgot(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox) == 1


def test_only_hash_is_stored(client, outbox):
    signup(client)
    forgot(client)
    token = token_from(outbox)
    row = db().query(PasswordResetToken).one()
    assert row.token_hash != token and token not in row.token_hash


def test_token_is_single_use(client, outbox):
    signup(client)
    forgot(client)
    token = token_from(outbox)
    assert reset(client, token).status_code == 200
    again = reset(client, token, "another-pass-1")
    assert again.status_code == 400 and "invalid or has expired" in again.json()["detail"]


def test_expired_token_rejected(client, outbox):
    signup(client)
    forgot(client)
    session = db()
    row = session.query(PasswordResetToken).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    session.commit()
    assert reset(client, token_from(outbox)).status_code == 400


def test_tampered_token_rejected(client, outbox):
    signup(client)
    forgot(client)
    assert reset(client, token_from(outbox) + "x").status_code == 400
    assert reset(client, "garbage").status_code == 400


def test_weak_new_password_rejected_and_token_kept(client, outbox):
    signup(client)
    forgot(client)
    token = token_from(outbox)
    assert reset(client, token, "short").status_code == 422
    assert reset(client, token).status_code == 200


def test_new_request_invalidates_older_link(client, outbox):
    signup(client)
    forgot(client)
    first = token_from(outbox)
    forgot(client)
    second = token_from(outbox)
    assert first != second
    assert reset(client, first).status_code == 400
    assert reset(client, second).status_code == 200


def test_reset_signs_out_existing_sessions(client, outbox):
    old_refresh = signup(client).json()["refresh_token"]
    forgot(client)
    reset(client, token_from(outbox))
    assert client.post("/v1/auth/refresh", json={"refresh_token": old_refresh}).status_code == 401


def test_reset_clears_login_lockout(client, outbox):
    signup(client)
    for _ in range(5):
        client.post("/v1/auth/login", json={"email": "jane@example.com", "password": "wrong-pass"})
    forgot(client)
    reset(client, token_from(outbox))
    res = client.post("/v1/auth/login", json={"email": "jane@example.com", "password": "brand-new-pass"})
    assert res.status_code == 200


def test_link_points_at_frontend(client, outbox):
    signup(client)
    forgot(client)
    assert outbox[0][2].count(f"{auth_api.settings.frontend_url}/?reset_token=") == 1
