from fastapi import HTTPException, status


def _err(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": True, "message": message, "code": code}
    )


def invalid_input(message: str) -> HTTPException:
    return _err(status.HTTP_400_BAD_REQUEST, message, "INVALID_INPUT")

def invalid_scale(scale: str) -> HTTPException:
    return _err(
        status.HTTP_400_BAD_REQUEST,
        f"'{scale}' is not a supported scale key. Supported: 4.0, 5.0, 6.0_DE, 110, 30",
        "INVALID_SCALE",
    )

def invalid_grade(grade: str, scale: str) -> HTTPException:
    return _err(status.HTTP_400_BAD_REQUEST, f"Invalid grade '{grade}' for {scale}-point scale", "INVALID_GRADE")

def unauthorised(message: str = "Authentication required") -> HTTPException:
    return _err(status.HTTP_401_UNAUTHORIZED, message, "UNAUTHORIZED")

def invalid_credentials(message: str = "Incorrect email or password") -> HTTPException:
    return _err(status.HTTP_401_UNAUTHORIZED, message, "INVALID_CREDENTIALS")

def session_expired() -> HTTPException:
    return _err(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Please login again.", "SESSION_EXPIRED")

def not_found(resource: str = "Resource") -> HTTPException:
    return _err(status.HTTP_404_NOT_FOUND, f"{resource} not found", "NOT_FOUND")

def calc_limit_reached() -> HTTPException:
    return _err(
        status.HTTP_400_BAD_REQUEST,
        "You have used your 5 free calculations. Sign up free to continue.",
        "CALC_LIMIT_REACHED"
    )

def server_error(message: str = "An unexpected error occurred.") -> HTTPException:
    return _err(status.HTTP_500_INTERNAL_SERVER_ERROR, message, "SERVER_ERROR")