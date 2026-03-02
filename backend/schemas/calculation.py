from datetime import datetime
from pydantic import BaseModel, field_validator
from backend.core.grade_mapper import _resolve_scale_key


class ConvertRequest(BaseModel):
    gpa: float
    from_scale: str
    to_scale: str

    @field_validator("from_scale", "to_scale")
    @classmethod
    def validate_scale(cls, v: str) -> str:
        return _resolve_scale_key(v)

    @field_validator("gpa")
    @classmethod
    def validate_gpa(cls, v: float) -> float:
        if v < 0:
            raise ValueError("GPA cannot be negative.")
        return v


class ConvertResponse(BaseModel):
    gpa: float
    from_scale: str
    to_scale: str
    converted: float
    description: str
    classification: str
    all_scales: list[dict] = []


class ConvertMultiResponse(BaseModel):
    gpa: float
    from_scale: str
    conversions: dict[str, float]


class GPAResponse(BaseModel):
    gpa: float
    scale: str
    total_credit_hours: int
    total_grade_points: float
    course_count: int | None = None
    classification: str
    scale_label: str | None = None


class TargetCourseInput(BaseModel):
    name: str | None = None
    credit_hours: float  # accept float from JS parseFloat, coerce to int in validator

    @field_validator("credit_hours")
    @classmethod
    def validate_credit_hours(cls, v: float) -> int:
        v = int(v)
        if v < 1 or v > 10:
            raise ValueError("Credit hours must be between 1 and 10.")
        return v


class TargetGradeRequest(BaseModel):
    target_cgpa: float
    remaining_courses: list[TargetCourseInput]

    @field_validator("remaining_courses")
    @classmethod
    def validate_courses(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one course must be provided.")
        return v


class TargetGradeResponse(BaseModel):
    target_cgpa: float
    required_grade_point: float
    required_letter_grade: str | None
    is_achievable: bool
    current_cgpa: float
    projected_cgpa: float
    scale: str


class ProjectionCourseInput(BaseModel):
    name: str
    credit_hours: float  # accept float from JS parseFloat, coerce to int in validator
    grade: str

    @field_validator("credit_hours")
    @classmethod
    def validate_credit_hours(cls, v: float) -> int:
        v = int(v)
        if v < 1 or v > 10:
            raise ValueError("Credit hours must be between 1 and 10.")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Grade cannot be empty.")
        return v


class ProjectionRequest(BaseModel):
    upcoming_courses: list[ProjectionCourseInput]

    @field_validator("upcoming_courses")
    @classmethod
    def validate_upcoming_courses(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one upcoming course must be provided.")
        return v


class ProjectionResponse(BaseModel):
    projected_cgpa: float
    scale: str
    total_credit_hours: int
    completed_credit_hours: int
    projected_credit_hours: int


class CalculationHistoryItem(BaseModel):
    id: str
    expression: str
    result: float
    created_at: datetime
    scale_from: str
    scale_to: str | None

    model_config = {
        "from_attributes": True
    }


class HistoryResponse(BaseModel):
    history: list[CalculationHistoryItem]
    count: int