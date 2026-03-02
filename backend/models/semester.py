import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Semester(Base):
    __tablename__ = "semesters"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="semesters")  # noqa: F821
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        "Course", back_populates="semester", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Semester id={self.id!r} name={self.name!r} user_id={self.user_id!r}>"