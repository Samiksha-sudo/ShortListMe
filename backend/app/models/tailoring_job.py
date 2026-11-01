from django.db import models
from django.utils import timezone

from app.models.user import User, new_id


class TailoringJob(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=new_id)
    # null only for rows created before accounts existed; those are owned by nobody and unreachable
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, db_column="user_id")
    cv_id = models.CharField(max_length=36)
    jd_id = models.CharField(max_length=36)
    status = models.CharField(max_length=16, default="queued")  # queued | running | done | failed
    step = models.CharField(max_length=16, default="queued")  # queued | analysing | matching | rewriting | done
    error = models.CharField(max_length=500, null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "tailoring_jobs"

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
