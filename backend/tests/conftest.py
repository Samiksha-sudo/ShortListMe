import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import Base, get_db, get_session_factory
from app.main import app
from app.services import rate_limiter


def sign_in(client, email):
    res = client.post("/v1/auth/signup", json={"email": email, "password": "correct-horse"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "storage"))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_session_factory] = lambda: Session
    rate_limiter.clear_all()
    c = TestClient(app)
    # Signed in as a default user; tests for other users / anonymous access build their own headers.
    c.headers.update(sign_in(c, "default@example.com"))
    yield c
    app.dependency_overrides.clear()
