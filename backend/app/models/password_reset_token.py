from django.db import models
from django.utils import timezone

from app.models.user import User


class PasswordResetToken(models.Model):
    # sha256 of the emailed token; the raw token is never stored
    token_hash = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "password_reset_tokens"
