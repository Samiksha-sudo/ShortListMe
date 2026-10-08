import hashlib
import hmac
import json
import time

from app.core.config import settings
from app.services import billing, security
from tests import samples
from tests.conftest import sign_in
from tests.test_jd import JD, create
from tests.test_tailoring import setup, start  # noqa: F401
from tests.test_upload_cv import post

SECRET = "whsec_test"


def signed(payload: bytes, stamp: int | None = None, secret: str = SECRET) -> dict:
    t = str(stamp or int(time.time()))
    sig = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return {"stripe-signature": f"t={t},v1={sig}"}


def send(client, event: dict, **kw):
    body = json.dumps(event).encode()
    return client.post("/v1/billing/webhook", content=body, headers=signed(body, **kw))


def user_id(client):
    return security.decode_token(client.headers["Authorization"].split()[1], "access")


def test_new_user_gets_five_free(client):
    assert client.get("/v1/billing").json() == {"plan": "free", "used": 0, "limit": 5, "remaining": 5}


def test_sixth_tailoring_is_blocked(setup, monkeypatch):  # noqa: F811
    client, cv_id, jd_id, fake, _ = setup
    monkeypatch.setattr(settings, "free_tailorings", 2)
    assert start(client, cv_id, jd_id).status_code == 202
    assert start(client, cv_id, jd_id).status_code == 202
    res = start(client, cv_id, jd_id)
    assert res.status_code == 402 and "Upgrade" in res.json()["detail"]


def test_failed_runs_do_not_use_quota(setup, monkeypatch):  # noqa: F811
    client, cv_id, jd_id, fake, _ = setup
    monkeypatch.setattr(settings, "free_tailorings", 1)
    fake.fail = True
    assert start(client, cv_id, jd_id).status_code == 202
    fake.fail = False
    assert start(client, cv_id, jd_id).status_code == 202


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    body = b"{}"
    assert client.post("/v1/billing/webhook", content=body, headers=signed(body, secret="other")).status_code == 400
    assert client.post("/v1/billing/webhook", content=body).status_code == 400
    assert client.post("/v1/billing/webhook", content=body, headers=signed(body, stamp=int(time.time()) - 3600)).status_code == 400


def test_webhook_off_when_secret_unset(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    body = b"{}"
    assert client.post("/v1/billing/webhook", content=body, headers=signed(body, secret="")).status_code == 400


def test_checkout_then_cancel(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    uid = user_id(client)
    done = {"type": "checkout.session.completed",
            "data": {"object": {"mode": "subscription", "client_reference_id": uid, "customer": "cus_1"}}}
    assert send(client, done).status_code == 200
    assert client.get("/v1/billing").json() == {"plan": "pro", "used": 0, "limit": 50, "remaining": 50}

    gone = {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_1"}}}
    assert send(client, gone).status_code == 200
    assert client.get("/v1/billing").json()["plan"] == "free"


def test_past_due_loses_pro(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    uid = user_id(client)
    send(client, {"type": "checkout.session.completed",
                  "data": {"object": {"mode": "subscription", "client_reference_id": uid, "customer": "cus_2"}}})
    send(client, {"type": "customer.subscription.updated", "data": {"object": {"customer": "cus_2", "status": "past_due"}}})
    assert client.get("/v1/billing").json()["plan"] == "free"


def test_checkout_needs_setup(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_id", "")
    assert client.post("/v1/billing/checkout").status_code == 400


def test_checkout_returns_stripe_url(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_price_id", "price_1")
    seen = {}
    monkeypatch.setattr(billing, "_call", lambda m, p, d: seen.update(data=d) or {"url": "https://checkout.stripe.test/x"})
    assert client.post("/v1/billing/checkout").json() == {"url": "https://checkout.stripe.test/x"}
    assert seen["data"]["client_reference_id"] == user_id(client)
    assert seen["data"]["line_items[0][price]"] == "price_1"


def test_billing_requires_login(client):
    anon = {"Authorization": ""}
    assert client.get("/v1/billing", headers=anon).status_code == 401
    assert client.post("/v1/billing/checkout", headers=anon).status_code == 401
