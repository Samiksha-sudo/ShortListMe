from django.db import models
from django.utils import timezone

from app.models.user import User, new_id


class JobDescription(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=new_id)
    # null only for rows created before accounts existed; those are owned by nobody and unreachable
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, db_column="user_id")
    text = models.TextField()
    # sha256 of the normalised text; used as the cache key for the JD analysis
    text_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "job_descriptions"
