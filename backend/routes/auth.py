import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, Cookie
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserUpdateRequest,
    PasswordChangeRequest,
    UserResponse,
    AuthResponse,
)
from backend.schemas.base import OKResponse
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    record_failed_login,
    record_successful_login,
    migrate_guest_session,
    REFRESH_TOKEN_DAYS,
)
from backend.errors import invalid_input, invalid_credentials, unauthorised
from backend.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Cookie helpers ────────────────────────────────────────────────────────

_COOKIE_NAME    = "gpa_refresh"
_COOKIE_MAX_AGE = REFRESH_TOKEN_DAYS * 24 * 60 * 60
_IS_PROD        = os.getenv("ENVIRONMENT", "production") == "production"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,          # JS cannot read this — XSS protection
        secure=_IS_PROD,        # HTTPS only in production; False for localhost
        samesite="lax",         # CSRF protection
        max_age=_COOKIE_MAX_AGE,
        path="/auth",           # only sent to /auth/* requests
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_COOKIE_NAME,
        path="/auth",
        httponly=True,
        secure=_IS_PROD,
        samesite="lax",
    )


# ── Register ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
@limiter.limit("5/minute")
def register(
    request: Request,
    response: Response,
    body: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise invalid_input("An account with this email already exists.")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        gpa_scale=body.gpa_scale,
        university_name=body.university_name or "",
    )
    db.add(user)
    db.flush()

    if body.session_id:
        migrate_guest_session(
            session_id=body.session_id,
            new_user_id=user.id,
            db=db,
        )

    access_token  = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(token=access_token, user=UserResponse.model_validate(user))


# ── Login ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    body: UserLoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()

    # Always verify password (constant-time, prevents email enumeration)
    password_ok = verify_password(
        body.password,
        user.hashed_password if user else "$2b$12$invalidhashfortimingnormalization",
    )

    # Account locked — tell user how long to wait
    if user and user.is_locked:
        mins_left = max(
            1,
            int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        )
        raise invalid_credentials(
            f"Account locked after too many failed attempts. "
            f"Try again in {mins_left} minute{'s' if mins_left != 1 else ''}."
        )

    if not user or not password_ok:
        if user:
            record_failed_login(user, db)
        raise invalid_credentials()

    record_successful_login(user, db)

    access_token  = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(token=access_token, user=UserResponse.model_validate(user))


# ── Token refresh ─────────────────────────────────────────────────────────

@router.post("/refresh", response_model=AuthResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    gpa_refresh: str | None = Cookie(default=None),
):
    """
    Silent token refresh. Browser sends the httpOnly cookie automatically.
    Returns a new short-lived access token + rotates the refresh cookie.
    """
    if not gpa_refresh:
        raise unauthorised("Session expired. Please log in again.")

    try:
        user_id = decode_refresh_token(gpa_refresh)
    except ValueError:
        _clear_refresh_cookie(response)
        raise unauthorised("Session expired. Please log in again.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        _clear_refresh_cookie(response)
        raise unauthorised("Account not found. Please log in again.")

    # Rotate — issue fresh pair
    new_access  = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh)

    return AuthResponse(token=new_access, user=UserResponse.model_validate(user))


# ── Logout ────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=OKResponse)
def logout(response: Response):
    _clear_refresh_cookie(response)
    return OKResponse(message="Logged out successfully.")


# ── Profile ───────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name or None
    if body.gpa_scale is not None:
        current_user.gpa_scale = body.gpa_scale
    if body.university_name is not None:
        current_user.university_name = body.university_name
    db.flush()
    return UserResponse.model_validate(current_user)


@router.patch("/password", response_model=OKResponse)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    body: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise invalid_input("Current password is incorrect.")
    if body.new_password == body.current_password:
        raise invalid_input("New password must be different from your current password.")
    current_user.hashed_password = hash_password(body.new_password)
    db.flush()
    return OKResponse(message="Password updated successfully.")


@router.delete("/account", response_model=OKResponse)
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _clear_refresh_cookie(response)
    db.delete(current_user)
    db.flush()
    return OKResponse(message="Account deleted. Sorry to see you go.")