import uuid

from django.db import models
from django.utils import timezone


def new_id() -> str:
    return str(uuid.uuid4())


class User(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=new_id)
    email = models.CharField(max_length=320, unique=True)
    password_hash = models.CharField(max_length=255)
    stripe_customer_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    subscription_status = models.CharField(max_length=32, null=True, blank=True)  # Stripe status, e.g. active
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "users"
