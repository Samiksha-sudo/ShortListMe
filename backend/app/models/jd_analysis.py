from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class JDAnalysis(Base):
    """Cache of the LLM's reading of a job description, keyed by the sha256 of its normalised text."""

    __tablename__ = "jd_analyses"

    text_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
