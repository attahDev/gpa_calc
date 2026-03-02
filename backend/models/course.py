import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    semester_id: Mapped[str] = mapped_column(
        String, ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    credit_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(10), nullable=False)
    grade_point: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    semester: Mapped["Semester"] = relationship("Semester", back_populates="courses")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Course id={self.id!r} name={self.name!r} "
            f"grade={self.grade!r} grade_point={self.grade_point}>"
        )