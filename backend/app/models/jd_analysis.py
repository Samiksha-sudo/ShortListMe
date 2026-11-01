from django.db import models
from django.utils import timezone


class JDAnalysis(models.Model):
    """Cache of the LLM's reading of a job description, keyed by the sha256 of its normalised text."""

    text_hash = models.CharField(max_length=64, primary_key=True)
    analysis = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "jd_analyses"
