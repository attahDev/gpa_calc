from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


SESSION_TTL_HOURS = 6


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    session_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    calc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS),
        nullable=False,
    )

    @property
    def is_expired(self) -> bool:
        """True if the session has passed its expiry time."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def limit_reached(self) -> bool:
        """True if the guest has used all 5 free calculations."""
        return self.calc_count >= 5

    def __repr__(self) -> str:
        return (
            f"<GuestSession id={self.session_id!r} "
            f"count={self.calc_count} expired={self.is_expired}>"
        )