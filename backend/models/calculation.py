"""
models/calculation.py
---------------------
Unified history table for both guest and authenticated users.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Calculation(Base):
    __tablename__ = "calculations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )

    expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[float | None] = mapped_column(Float, nullable=True)
    scale_from: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scale_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship — no back_populates needed here, User owns the cascade
    user: Mapped["User | None"] = relationship("User", back_populates="calculations")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Calculation id={self.id!r} result={self.result}>"