"""End to end: sign up, use the free allowance, hit the paywall, pay through (a faked) Stripe, keep going, cancel."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings
from app.db import get_session_factory
from app.main import app
from app.models import TailoringJob
from app.services import billing
from tests.conftest import sign_in
from tests.test_billing import SECRET, send, signed, user_id
from tests.test_tailoring import setup, start  # noqa: F401


@pytest.fixture
def stripe(monkeypatch):
    """Pretend to be Stripe: records the calls the app makes and hands back canned URLs."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(settings, "stripe_price_id", "price_20gbp")
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    calls = []

    def fake_request(method, url, data=None, auth=None, timeout=None):
        calls.append({"method": method, "url": url, "data": data, "auth": auth})
        return httpx.Response(200, json={"url": f"https://stripe.test{url.split('/v1', 1)[1]}"})

    monkeypatch.setattr(billing.httpx, "request", fake_request)
    return calls


def subscribe(client, customer="cus_e2e"):
    done = {"type": "checkout.session.completed",
            "data": {"object": {"mode": "subscription", "client_reference_id": user_id(client), "customer": customer}}}
    assert send(client, done).status_code == 200


def test_full_journey(setup, stripe, monkeypatch):  # noqa: F811
    client, cv_id, jd_id, fake, _ = setup
    monkeypatch.setattr(settings, "free_tailorings", 2)
    monkeypatch.setattr(settings, "pro_tailorings_per_month", 3)

    # 1. free allowance
    assert client.get("/v1/billing").json() == {"plan": "free", "used": 0, "limit": 2, "remaining": 2}
    for n in (1, 2):
        job = start(client, cv_id, jd_id)
        assert job.status_code == 202
        assert client.get(f"/v1/tailoring/{job.json()['job_id']}").json()["status"] == "done"
        assert client.get("/v1/billing").json()["used"] == n

    # 2. the paywall
    blocked = start(client, cv_id, jd_id)
    assert blocked.status_code == 402 and "Upgrade" in blocked.json()["detail"]

    # 3. checkout: the app asks Stripe for a subscription session tied to this user
    url = client.post("/v1/billing/checkout").json()["url"]
    assert url == "https://stripe.test/checkout/sessions"
    sent = stripe[-1]
    assert sent["auth"] == ("sk_test_x", "") and sent["data"]["mode"] == "subscription"
    assert sent["data"]["client_reference_id"] == user_id(client)
    assert sent["data"]["customer_email"] == "default@example.com"

    # 4. paying alone changes nothing until Stripe confirms; the webhook flips the plan
    assert start(client, cv_id, jd_id).status_code == 402
    subscribe(client)
    assert client.get("/v1/billing").json()["plan"] == "pro"

    # 5. pro quota counts the last 30 days, so the two earlier runs are included
    assert client.get("/v1/billing").json() == {"plan": "pro", "used": 2, "limit": 3, "remaining": 1}
    assert start(client, cv_id, jd_id).status_code == 202
    over = start(client, cv_id, jd_id)
    assert over.status_code == 402 and "this month" in over.json()["detail"]

    # 6. already subscribed: no second checkout; the portal works
    assert client.post("/v1/billing/checkout").status_code == 400
    assert client.post("/v1/billing/portal").json()["url"] == "https://stripe.test/billing_portal/sessions"
    assert stripe[-1]["data"]["customer"] == "cus_e2e"

    # 7. cancel: back to the free plan, which is already used up
    send(client, {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_e2e"}}})
    assert client.get("/v1/billing").json()["plan"] == "free"
    assert start(client, cv_id, jd_id).status_code == 402


def test_resubscribing_reuses_the_stripe_customer(client, stripe):
    subscribe(client)
    send(client, {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_e2e"}}})
    client.post("/v1/billing/checkout")
    data = stripe[-1]["data"]
    assert data["customer"] == "cus_e2e" and "customer_email" not in data


def test_users_are_billed_separately(client, stripe):
    subscribe(client)
    other = sign_in(client, "other@example.com")
    assert client.get("/v1/billing", headers=other).json()["plan"] == "free"
    assert client.get("/v1/billing").json()["plan"] == "pro"


def test_webhook_for_unknown_user_or_event_is_harmless(client, stripe):
    ghost = {"type": "checkout.session.completed",
             "data": {"object": {"mode": "subscription", "client_reference_id": "nobody", "customer": "cus_x"}}}
    assert send(client, ghost).status_code == 200
    unknown = {"type": "customer.subscription.updated", "data": {"object": {"customer": "cus_none", "status": "active"}}}
    assert send(client, unknown).status_code == 200
    assert send(client, {"type": "invoice.paid", "data": {"object": {}}}).status_code == 200
    assert send(client, {}).status_code == 200
    assert client.get("/v1/billing").json()["plan"] == "free"


def test_one_time_payment_checkout_does_not_grant_pro(client, stripe):
    send(client, {"type": "checkout.session.completed",
                  "data": {"object": {"mode": "payment", "client_reference_id": user_id(client), "customer": "cus_p"}}})
    assert client.get("/v1/billing").json()["plan"] == "free"


def test_webhook_rejects_garbage_body_with_valid_signature(client, stripe):
    body = b"not json"
    assert client.post("/v1/billing/webhook", content=body, headers=signed(body)).status_code == 400


def test_trialing_counts_as_pro(client, stripe):
    subscribe(client)
    send(client, {"type": "customer.subscription.updated", "data": {"object": {"customer": "cus_e2e", "status": "trialing"}}})
    assert client.get("/v1/billing").json()["plan"] == "pro"


def test_stripe_errors_become_clean_messages(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(settings, "stripe_price_id", "price_1")

    monkeypatch.setattr(billing.httpx, "request", lambda *a, **k: httpx.Response(401, json={"error": "bad key"}))
    res = client.post("/v1/billing/checkout")
    assert res.status_code == 400 and res.json()["detail"] == "The payment service rejected the request."

    def down(*a, **k):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(billing.httpx, "request", down)
    res = client.post("/v1/billing/checkout")
    assert res.status_code == 400 and "did not respond" in res.json()["detail"]


def test_checkout_without_secret_key(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "stripe_price_id", "price_1")
    assert client.post("/v1/billing/checkout").json()["detail"] == "Payments are not set up yet."


def test_portal_needs_a_customer(client, stripe):
    res = client.post("/v1/billing/portal")
    assert res.status_code == 400 and "don't have a subscription" in res.json()["detail"]


def test_other_users_quota_is_unaffected(setup, monkeypatch):  # noqa: F811
    client, cv_id, jd_id, *_ = setup
    monkeypatch.setattr(settings, "free_tailorings", 1)
    assert start(client, cv_id, jd_id).status_code == 202
    assert start(client, cv_id, jd_id).status_code == 402
    other = sign_in(client, "fresh@example.com")
    assert client.get("/v1/billing", headers=other).json()["remaining"] == 1


def test_pro_period_only_counts_recent_runs(setup, stripe):  # noqa: F811
    client, cv_id, jd_id, *_ = setup
    start(client, cv_id, jd_id)
    subscribe(client)
    with app.dependency_overrides[get_session_factory]()() as db:
        for job in db.query(TailoringJob).all():
            job.created_at = datetime.now(timezone.utc) - timedelta(days=45)
        db.commit()
    assert client.get("/v1/billing").json()["used"] == 0


def test_signature_check_unit(monkeypatch):
    payload = b'{"a":1}'
    now = 1_700_000_000
    sig = hmac.new(b"whsec", f"{now}.".encode() + payload, hashlib.sha256).hexdigest()
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec")
    assert billing.verify_signature(payload, f"t={now},v1={sig}", now=now)
    assert billing.verify_signature(payload, f"t={now},v1=bad,v1={sig}", now=now)  # key rotation: any v1 may match
    assert not billing.verify_signature(payload + b" ", f"t={now},v1={sig}", now=now)
    assert not billing.verify_signature(payload, f"t={now},v1={sig}", now=now + 301)
    assert not billing.verify_signature(payload, "garbage", now=now)
    assert not billing.verify_signature(payload, "", now=now)


def test_migrations_build_the_schema_from_scratch(tmp_path, monkeypatch):
    db = tmp_path / "fresh.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db}")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    cols = {c["name"] for c in inspect(create_engine(f"sqlite:///{db}")).get_columns("users")}
    assert {"stripe_customer_id", "subscription_status"} <= cols
    command.downgrade(cfg, "-1")
    cols = {c["name"] for c in inspect(create_engine(f"sqlite:///{db}")).get_columns("users")}
    assert not {"stripe_customer_id", "subscription_status"} & cols
    command.upgrade(cfg, "head")


def test_admin_is_free_and_unlimited(setup, stripe, monkeypatch):  # noqa: F811
    client, cv_id, jd_id, *_ = setup
    monkeypatch.setattr(settings, "free_tailorings", 1)
    monkeypatch.setattr(settings, "admin_emails", "Default@Example.com, someone@else.com")
    assert client.get("/v1/billing").json()["plan"] == "admin"
    for _ in range(3):  # well past the free allowance
        assert start(client, cv_id, jd_id).status_code == 202
    assert client.get("/v1/billing").json() == {"plan": "admin", "used": 3, "limit": 0, "remaining": 0}
    res = client.post("/v1/billing/checkout")
    assert res.status_code == 400 and "free of charge" in res.json()["detail"]


def test_non_admin_is_still_limited(setup, monkeypatch):  # noqa: F811
    client, cv_id, jd_id, *_ = setup
    monkeypatch.setattr(settings, "free_tailorings", 1)
    monkeypatch.setattr(settings, "admin_emails", "someone@else.com")
    assert start(client, cv_id, jd_id).status_code == 202
    assert start(client, cv_id, jd_id).status_code == 402


def test_default_admin_is_the_owner():
    assert "kadsamiksha347@gmail.com" in settings.admin_emails
