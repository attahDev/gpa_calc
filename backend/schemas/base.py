from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    Standard error envelope returned by every failing API call.
    Shape is fixed — no route may return a different error structure.
    """
    error: bool = True
    message: str      # human-readable, safe to show in the UI
    code: str         # machine-readable, used by api.js for branching


class OKResponse(BaseModel):
    """Minimal success acknowledgement for operations with no return data."""
    ok: bool = True
    message: str = "success"