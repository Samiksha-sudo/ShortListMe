import pytest

from app.core.config import settings
from app.services import rate_limiter
from tests.client import TestClient


def sign_in(client, email):
    res = client.post("/v1/auth/signup", json={"email": email, "password": "correct-horse"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _inline_background_work(settings):  # pytest-django's `settings` fixture, not the app's
    settings.BACKGROUND_SYNC = True


@pytest.fixture
def client(tmp_path, monkeypatch, db):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    rate_limiter.clear_all()
    c = TestClient()
    # Signed in as a default user; tests for other users / anonymous access build their own headers.
    c.headers.update(sign_in(c, "default@example.com"))
    return c
