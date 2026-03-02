from pydantic import BaseModel, field_validator
from backend.core.grade_mapper import _resolve_scale_key


class GuestSessionResponse(BaseModel):
    """Returned when a new guest session is created."""
    session_id: str
    calc_count: int
    calc_limit: int = 5
    message: str = "Guest session created. You have 5 free calculations."


class GuestCalculateRequest(BaseModel):
    """
    A guest GPA calculation request.
    Accepts either a direct GPA value or an expression string (e.g. "3.5 + 0.2").
    Scale is required — guest calculations are scale-aware.
    """
    expression: str          # numeric expression or plain GPA value as string
    scale: str = "4.0"       # scale key for the calculation

    def validate_scale_field(self) -> str:
        return _resolve_scale_key(self.scale)


class GuestCalculateResponse(BaseModel):
    result: float
    scale: str
    classification: str
    calc_count: int
    calc_limit: int = 5
    calcs_remaining: int


class GuestConvertRequest(BaseModel):
    """A guest GPA conversion request."""
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


class GuestConvertResponse(BaseModel):
    gpa: float
    from_scale: str
    to_scale: str
    converted: float
    description: str
    classification: str
    all_scales: list[dict] = []
    calc_count: int
    calc_limit: int = 5
    calcs_remaining: int