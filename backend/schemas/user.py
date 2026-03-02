from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from backend.core.grade_mapper import _resolve_scale_key


_COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "qwerty123", "iloveyou", "admin123", "letmein1", "welcome1",
    "monkey123", "dragon123", "master123", "abc123456", "sunshine1",
    "princess1", "football1", "shadow123", "superman1", "michael1",
}


def _check_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(v) > 72:
        raise ValueError("Password must be at most 72 characters (bcrypt limit).")
    if v.lower() in _COMMON_PASSWORDS:
        raise ValueError("This password is too common. Please choose a stronger one.")
    has_upper   = any(c.isupper()  for c in v)
    has_digit   = any(c.isdigit()  for c in v)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v)
    if not (has_upper or has_digit or has_special):
        raise ValueError(
            "Password must include at least one uppercase letter, number, or special character."
        )
    return v


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    gpa_scale: str = "4.0"
    university_name: str | None = None
    session_id: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) > 150:
                raise ValueError("Name must be at most 150 characters.")
        return v or None

    @field_validator("gpa_scale")
    @classmethod
    def validate_scale(cls, v: str) -> str:
        return _resolve_scale_key(v)

    @field_validator("university_name")
    @classmethod
    def validate_university(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("University name must be at most 100 characters.")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    gpa_scale: str | None = None
    university_name: str | None = None

    @field_validator("gpa_scale")
    @classmethod
    def validate_scale(cls, v: str | None) -> str | None:
        if v is not None:
            return _resolve_scale_key(v)
        return v

    @field_validator("university_name")
    @classmethod
    def validate_university(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("University name must be at most 100 characters.")
        return v


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return _check_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirmation do not match.")
        return self


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    gpa_scale: str
    university_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserResponse