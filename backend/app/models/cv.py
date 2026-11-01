from django.db import models
from django.utils import timezone

from app.models.user import User, new_id


class CV(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=new_id)
    # null only for rows created before accounts existed; those are owned by nobody and unreachable
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, db_column="user_id")
    filename = models.CharField(max_length=255)
    mime = models.CharField(max_length=100)
    size = models.IntegerField()
    storage_key = models.CharField(max_length=255)
    parsed = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "cvs"
