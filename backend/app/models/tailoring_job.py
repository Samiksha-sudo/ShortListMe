import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TailoringJob(Base):
    __tablename__ = "tailoring_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # nullable only for rows created before accounts existed; those are owned by nobody and unreachable
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    cv_id: Mapped[str] = mapped_column(String(36))
    jd_id: Mapped[str] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | running | done | failed
    step: Mapped[str] = mapped_column(String(16), default="queued")  # queued | analysing | matching | rewriting | done
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
