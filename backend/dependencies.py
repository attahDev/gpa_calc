
from sqlalchemy.orm import Session
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import get_db
from backend.models.user import User
from backend.models.guest_session import GuestSession
from backend.services.auth_service import decode_access_token


_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Auth dependency — Phase 3 real JWT implementation
# ---------------------------------------------------------------------------

def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """
    Verify the JWT from the Authorization: Bearer header and return the User.

    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": True,
                "message": "Authentication required. Please log in.",
                "code": "UNAUTHORIZED",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError:
        # Covers: expired, wrong signature, malformed, missing sub claim
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": True,
                "message": "Your session has expired. Please log in again.",
                "code": "SESSION_EXPIRED",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Token was valid but the user has been deleted
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": True,
                "message": "Account not found. Please log in again.",
                "code": "UNAUTHORIZED",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ---------------------------------------------------------------------------
# Guest session dependency
# ---------------------------------------------------------------------------

def get_guest_session(
    db: Session = Depends(get_db),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID"),
) -> GuestSession:
    """
    Validate a guest session from the X-Session-ID header.
    """
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": True,
                "message": "X-Session-ID header is required for guest calculations.",
                "code": "UNAUTHORIZED",
            },
        )

    session = db.query(GuestSession).filter(
        GuestSession.session_id == x_session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": True,
                "message": "Guest session not found. Please start a new session.",
                "code": "NOT_FOUND",
            },
        )

    if session.is_expired:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": True,
                "message": "Your guest session has expired. Please start a new session.",
                "code": "SESSION_EXPIRED",
            },
        )

    return session
