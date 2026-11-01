from django.db import models
from django.utils import timezone

from app.models.user import User


class RefreshToken(models.Model):
    # sha256 of the token, so a leaked database does not leak usable tokens
    token_hash = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "refresh_tokens"
