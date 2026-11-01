import json

from rest_framework.response import Response

from app.api.deps import endpoint
from app.api.errors import ApiError
from app.models import User
from app.services import billing


@endpoint(["GET"])
def get_usage(request, user_id):
    return Response(billing.usage(User.objects.get(pk=user_id)))


@endpoint(["POST"])
def checkout(request, user_id):
    try:
        return Response({"url": billing.checkout_url(User.objects.get(pk=user_id))})
    except billing.BillingError as exc:
        raise ApiError(400, str(exc)) from exc


@endpoint(["POST"])
def portal(request, user_id):
    try:
        return Response({"url": billing.portal_url(User.objects.get(pk=user_id))})
    except billing.BillingError as exc:
        raise ApiError(400, str(exc)) from exc


@endpoint(["POST"], auth=None)
def webhook(request):
    payload = request._request.body  # raw bytes: the signature covers them exactly as Stripe sent them
    if not billing.verify_signature(payload, request.headers.get("stripe-signature", "")):
        raise ApiError(400, "Invalid signature.")
    try:
        event = json.loads(payload)
    except ValueError:
        raise ApiError(400, "Invalid payload.") from None
    billing.apply_event(event)
    return Response({"received": True})
