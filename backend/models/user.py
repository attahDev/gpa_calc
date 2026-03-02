import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(
        String(150), nullable=True, default=None
    )
    gpa_scale: Mapped[str] = mapped_column(
        String(50), nullable=False, default="5.0"
    )
    university_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # ── Brute-force lockout ───────────────────────────────────────────────
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    # ── Relationships ─────────────────────────────────────────────────────
    semesters: Mapped[list["Semester"]] = relationship(
        "Semester", back_populates="user", cascade="all, delete-orphan"
    )
    calculations: Mapped[list["Calculation"]] = relationship(
        "Calculation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User id={self.id!r} email={self.email!r} scale={self.gpa_scale!r}>"