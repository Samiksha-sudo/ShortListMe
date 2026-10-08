import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import rate_limiter
from tests import samples
from tests.conftest import sign_in
from tests.test_jd import create
from tests.test_upload_cv import post


@pytest.fixture
def other(client):
    return sign_in(client, "other@example.com")


@pytest.fixture
def anon(client):
    return TestClient(app)


def test_requests_without_a_valid_token_are_401(anon):
    assert anon.get("/v1/cvs/x").status_code == 401
    assert anon.post("/v1/cvs", files={"file": ("a.docx", b"x")}).status_code == 401
    assert anon.post("/v1/jds", json={"text": "x"}).status_code == 401
    assert anon.post("/v1/tailoring", json={"cv_id": "a", "jd_id": "b"}).status_code == 401
    assert anon.get("/v1/tailoring/x").status_code == 401
    assert anon.get("/v1/cvs/x", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_refresh_token_is_not_accepted_as_access(anon):
    refresh = anon.post("/v1/auth/signup", json={"email": "r@example.com", "password": "correct-horse"}).json()["refresh_token"]
    assert anon.get("/v1/cvs/x", headers={"Authorization": f"Bearer {refresh}"}).status_code == 401


def test_other_users_cannot_read_or_use_my_data(client, other):
    jd_id = create(client).json()["jd_id"]
    cv_id = post(client, "cv.docx", samples.single_column()).json()["cv_id"]
    job_id = client.post("/v1/tailoring", json={"cv_id": cv_id, "jd_id": jd_id}).json()["job_id"]

    # the owner can reach all of it
    assert client.get(f"/v1/jds/{jd_id}").status_code == 200
    assert client.get(f"/v1/cvs/{cv_id}").status_code == 200
    assert client.get(f"/v1/tailoring/{job_id}").status_code == 200

    # anyone else gets the same 404 as for an id that doesn't exist
    assert client.get(f"/v1/jds/{jd_id}", headers=other).status_code == 404
    assert client.post(f"/v1/jds/{jd_id}/analysis", headers=other).status_code == 404
    assert client.get(f"/v1/cvs/{cv_id}", headers=other).status_code == 404
    assert client.post(f"/v1/cvs/{cv_id}/export.docx", json={}, headers=other).status_code == 404
    assert client.post(f"/v1/cvs/{cv_id}/export.pdf", json={}, headers=other).status_code == 404
    assert client.get(f"/v1/tailoring/{job_id}", headers=other).status_code == 404
    for path in ("/v1/matches", "/v1/rewrites", "/v1/tailoring"):
        assert client.post(path, json={"cv_id": cv_id, "jd_id": jd_id}, headers=other).status_code == 404


def test_llm_endpoints_are_rate_limited_per_user(client, other, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_llm", 2)
    for _ in range(2):
        assert client.post("/v1/jds/missing/analysis").status_code == 404
    limited = client.post("/v1/jds/missing/analysis")
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
    # another user has their own budget
    assert client.post("/v1/jds/missing/analysis", headers=other).status_code == 404


def test_upload_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_upload", 1)
    assert post(client, "a.txt", b"x").status_code == 422
    assert post(client, "a.txt", b"x").status_code == 429
