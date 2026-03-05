from datetime import datetime
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SemesterCreateRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Semester name cannot be empty.")
        if len(v) > 50:
            raise ValueError("Semester name must be at most 50 characters.")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class SemesterResponse(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: datetime
    course_count: int = 0
    credit_hours: int = 0
    gpa: float | None = None

    model_config = {"from_attributes": True}


class SemesterListResponse(BaseModel):
    semesters: list[SemesterResponse]
    count: int