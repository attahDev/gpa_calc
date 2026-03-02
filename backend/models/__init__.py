# Import all models so SQLAlchemy's metadata registry is populated
# before create_all() is called. Order matters for foreign keys.
from backend.models.user import User
from backend.models.semester import Semester
from backend.models.course import Course
from backend.models.calculation import Calculation
from backend.models.guest_session import GuestSession

# Explicitly configure all mappers to catch relationship errors early
from sqlalchemy.orm import configure_mappers
configure_mappers()

__all__ = ["User", "Semester", "Course", "Calculation", "GuestSession"]