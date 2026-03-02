import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.calculation import Calculation
from backend.models.guest_session import GuestSession


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Password ──────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT config ────────────────────────────────────────────────────────────

_JWT_SECRET    = os.getenv("JWT_SECRET", "")
_JWT_ALGORITHM = "HS256"

# Access token: short-lived (default 15 min)
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))

# Refresh token: long-lived (default 7 days)
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))


def _require_secret() -> str:
    if not _JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET environment variable is not set. "
            "Add it to your .env file or Render dashboard."
        )
    return _JWT_SECRET


def create_access_token(user_id: str) -> str:
    secret = _require_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub":  user_id,
        "type": "access",
        "iat":  now,
        "exp":  now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    secret = _require_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub":  user_id,
        "type": "refresh",
        "iat":  now,
        "exp":  now + timedelta(days=REFRESH_TOKEN_DAYS),
    }
    return jwt.encode(payload, secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    secret = _require_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Token is invalid or has expired.")
    if payload.get("type") != "access":
        raise ValueError("Wrong token type.")
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise ValueError("Token payload is missing the subject claim.")
    return user_id


def decode_refresh_token(token: str) -> str:
    secret = _require_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=[_JWT_ALGORITHM])
    except JWTError:
        raise ValueError("Refresh token is invalid or has expired.")
    if payload.get("type") != "refresh":
        raise ValueError("Wrong token type.")
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise ValueError("Token payload is missing the subject claim.")
    return user_id


# ── Brute-force lockout ───────────────────────────────────────────────────

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES     = 15


def record_failed_login(user: User, db: Session) -> None:
    """Increment failed counter. Lock account after MAX_FAILED_ATTEMPTS."""
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
    db.flush()


def record_successful_login(user: User, db: Session) -> None:
    """Reset lockout state on successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    db.flush()


# ── Guest migration ───────────────────────────────────────────────────────

def migrate_guest_session(session_id: str, new_user_id: str, db: Session) -> int:
    calculations = (
        db.query(Calculation)
        .filter(Calculation.session_id == session_id)
        .all()
    )
    for calc in calculations:
        calc.user_id    = new_user_id
        calc.session_id = None

    guest_session = (
        db.query(GuestSession)
        .filter(GuestSession.session_id == session_id)
        .first()
    )
    if guest_session:
        db.delete(guest_session)

    return len(calculations)