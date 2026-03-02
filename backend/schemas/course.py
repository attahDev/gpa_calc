from datetime import datetime
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CourseCreateRequest(BaseModel):
    name: str
    credit_hours: int
    grade: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Course name cannot be empty.")
        if len(v) > 100:
            raise ValueError("Course name must be at most 100 characters.")
        return v

    @field_validator("credit_hours")
    @classmethod
    def validate_credit_hours(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("Credit hours must be between 1 and 10.")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade_format(cls, v: str) -> str:
        # Only basic format validation here — scale-aware validation
        # happens in the route handler once the user's scale key is known
        v = v.strip().upper()
        if not v:
            raise ValueError("Grade cannot be empty.")
        if len(v) > 10:
            raise ValueError("Grade string is too long.")
        return v


class CourseUpdateRequest(BaseModel):
    name: str | None = None
    credit_hours: int | None = None
    grade: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Course name cannot be empty.")
            if len(v) > 100:
                raise ValueError("Course name must be at most 100 characters.")
        return v

    @field_validator("credit_hours")
    @classmethod
    def validate_credit_hours(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Credit hours must be between 1 and 10.")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade_format(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip().upper()
            if not v:
                raise ValueError("Grade cannot be empty.")
            if len(v) > 10:
                raise ValueError("Grade string is too long.")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CourseResponse(BaseModel):
    id: str
    semester_id: str
    name: str
    credit_hours: int
    grade: str
    grade_point: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseListResponse(BaseModel):
    courses: list[CourseResponse]
    count: int