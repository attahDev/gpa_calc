import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.database import engine, Base
from backend.limiter import limiter
import backend.models  # noqa: F401 — registers all models with metadata

from backend.routes.auth import router as auth_router
from backend.routes.guest import router as guest_router
from backend.routes.semesters import router as semesters_router
from backend.routes.courses import router as courses_router
from backend.routes.calculations import router as calculations_router
from backend.routes.history import router as history_router


# ── Security headers middleware ───────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]         = "DENY"
        response.headers["X-XSS-Protection"]        = "1; mode=block"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]      = "geolocation=(), microphone=(), camera=()"
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ── Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


# ── App ───────────────────────────────────────────────────────────────────

IS_PROD = os.getenv("ENVIRONMENT") == "production"

app = FastAPI(
    title="GPA Calculator API",
    description=(
        "Calculate, track, and convert GPAs across international grading scales. "
        "Supports 4.0 (US/Canada), 5.0 (Nigeria/West Africa), "
        "6.0_DE (Germany), 110 (Italy final), and 30 (Italy course)."
    ),
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None,
    openapi_url=None if IS_PROD else "/openapi.json",  # hides schema in prod
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SecurityHeadersMiddleware)

# CORS — credentials=True required for httpOnly cookies
# In production: ALLOWED_ORIGIN = https://your-app.onrender.com (set in Render dashboard)
# In development: ALLOWED_ORIGIN = http://localhost:5500
_ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN")
_IS_DEV = os.getenv("ENVIRONMENT") == "development"

# Dev allows localhost; production allows only the configured origin
_CORS_ORIGINS = (
    [
        _ALLOWED_ORIGIN,
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ]
    if _IS_DEV
    else [_ALLOWED_ORIGIN]   # production: only the real domain
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-ID"],
)


# ── Global exception handler ──────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "An unexpected error occurred. Please try again.",
            "code": "SERVER_ERROR",
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(guest_router)
app.include_router(semesters_router)
app.include_router(courses_router)
app.include_router(calculations_router)
app.include_router(history_router)


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], include_in_schema=False)
def health():
    return {"status": "ok"}