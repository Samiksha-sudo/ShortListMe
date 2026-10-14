import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import TailoringJob, User

STRIPE_API = "https://api.stripe.com/v1"
ACTIVE = {"active", "trialing"}
SIGNATURE_TOLERANCE_SECONDS = 300
PERIOD_DAYS = 30


class BillingError(Exception):
    """Billing isn't available or Stripe refused; the message is safe to show to users."""


def is_admin(user: User) -> bool:
    return user.email.lower() in {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}


def is_pro(user: User) -> bool:
    return user.subscription_status in ACTIVE


def _used(db: Session, user_id: str, since: datetime | None) -> int:
    # Failed runs are free for the user: only jobs that did (or may still) produce a result count.
    q = select(func.count()).select_from(TailoringJob).where(TailoringJob.user_id == user_id, TailoringJob.status != "failed")
    if since is not None:
        q = q.where(TailoringJob.created_at >= since)
    return db.scalar(q) or 0


def usage(db: Session, user: User) -> dict:
    if is_admin(user):  # never charged, never limited
        return {"plan": "admin", "used": _used(db, user.id, None), "limit": 0, "remaining": 0}
    if is_pro(user):
        since = datetime.now(timezone.utc) - timedelta(days=PERIOD_DAYS)
        limit, used = settings.pro_tailorings_per_month, _used(db, user.id, since)
    else:
        limit, used = settings.free_tailorings, _used(db, user.id, None)
    return {"plan": "pro" if is_pro(user) else "free", "used": used, "limit": limit, "remaining": max(limit - used, 0)}


def _call(method: str, path: str, data: dict) -> dict:
    if not settings.stripe_secret_key:
        raise BillingError("Payments are not set up yet.")
    try:
        res = httpx.request(method, f"{STRIPE_API}{path}", data=data, auth=(settings.stripe_secret_key, ""), timeout=20)
    except httpx.HTTPError as exc:
        raise BillingError("The payment service did not respond. Please try again.") from exc
    if res.status_code != 200:
        raise BillingError("The payment service rejected the request.")
    return res.json()


def checkout_url(db: Session, user: User) -> str:
    if not settings.stripe_price_id:
        raise BillingError("Payments are not set up yet.")
    if is_admin(user):
        raise BillingError("Your account is free of charge, so there's nothing to buy.")
    if is_pro(user):
        raise BillingError("You already have an active subscription.")
    data = {"mode": "subscription", "line_items[0][price]": settings.stripe_price_id, "line_items[0][quantity]": "1",
            "client_reference_id": user.id,
            "success_url": f"{settings.frontend_url}/?billing=success#/settings", "cancel_url": f"{settings.frontend_url}/?billing=cancelled#/settings"}
    if user.stripe_customer_id:
        data["customer"] = user.stripe_customer_id
    else:
        data["customer_email"] = user.email
    return _call("POST", "/checkout/sessions", data)["url"]


def portal_url(user: User) -> str:
    if not user.stripe_customer_id:
        raise BillingError("You don't have a subscription to manage.")
    return _call("POST", "/billing_portal/sessions",
                 {"customer": user.stripe_customer_id, "return_url": settings.frontend_url})["url"]


def verify_signature(payload: bytes, header: str, now: float | None = None) -> bool:
    """Stripe-Signature: `t=<unix>,v1=<hmac-sha256 of "<t>.<payload>">`, rejecting stale timestamps."""
    secret = settings.stripe_webhook_secret
    if not secret or not header:
        return False
    parts = [p.split("=", 1) for p in header.split(",") if "=" in p]
    stamp = next((v for k, v in parts if k == "t"), "")
    sigs = [v for k, v in parts if k == "v1"]
    if not stamp.isdigit() or abs((now or time.time()) - int(stamp)) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    expected = hmac.new(secret.encode(), f"{stamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in sigs)


def apply_event(db: Session, event: dict) -> None:
    """Keep the user's subscription status in step with Stripe. Unknown events and users are ignored."""
    kind, obj = event.get("type", ""), event.get("data", {}).get("object", {})
    if kind == "checkout.session.completed" and obj.get("mode") == "subscription":
        user = db.get(User, obj.get("client_reference_id") or "")
        if user is not None:
            user.stripe_customer_id = obj.get("customer")
            user.subscription_status = "active"
    elif kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        user = db.scalar(select(User).where(User.stripe_customer_id == obj.get("customer")))
        if user is not None:
            user.subscription_status = "canceled" if kind.endswith("deleted") else obj.get("status")
    db.commit()


def delete_customer(user: User) -> None:
    """Best effort: deleting the Stripe customer also cancels their subscriptions. Never blocks account deletion."""
    if not user.stripe_customer_id or not settings.stripe_secret_key:
        return
    try:
        httpx.delete(f"{STRIPE_API}/customers/{user.stripe_customer_id}", auth=(settings.stripe_secret_key, ""), timeout=20)
    except httpx.HTTPError:
        pass
