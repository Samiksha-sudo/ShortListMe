from tests.client import TestClient



def test_health():
    r = TestClient().get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
