import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # nullable only for rows created before accounts existed; those are owned by nobody and unreachable
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    # sha256 of the normalised text; later stories use it as the cache key for the JD analysis
    text_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
