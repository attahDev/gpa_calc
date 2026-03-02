from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_guest_session
from backend.models.guest_session import GuestSession
from backend.models.calculation import Calculation
from backend.schemas.guest import (
    GuestSessionResponse,
    GuestCalculateRequest,
    GuestCalculateResponse,
    GuestConvertRequest,
    GuestConvertResponse,
)
from backend.core.validator import safe_parse_expression, validate_scale
from backend.core.converter import convert_gpa, convert_gpa_multi, describe_conversion, get_gpa_classification
from backend.core.grade_mapper import SCALE_REGISTRY, _resolve_scale_key
from backend.errors import calc_limit_reached, invalid_input, invalid_scale
from backend.limiter import limiter


router = APIRouter(prefix="/guest", tags=["guest"])


@router.post("/session", response_model=GuestSessionResponse)
@limiter.limit("20/minute")
def create_guest_session(
    request: Request,
    db: Session = Depends(get_db),
):
    session = GuestSession()
    db.add(session)
    db.flush()
    return GuestSessionResponse(
        session_id=session.session_id,
        calc_count=session.calc_count,
    )


@router.post("/calculate", response_model=GuestCalculateResponse)
@limiter.limit("20/minute")
def guest_calculate(
    request: Request,
    body: GuestCalculateRequest,
    db: Session = Depends(get_db),
    session: GuestSession = Depends(get_guest_session),
):
    if session.limit_reached:
        raise calc_limit_reached()

    try:
        scale_key = _resolve_scale_key(body.scale)
    except ValueError:
        raise invalid_scale(body.scale)

    try:
        result = safe_parse_expression(body.expression)
    except (ValueError, ZeroDivisionError) as exc:
        raise invalid_input(str(exc))

    defn = SCALE_REGISTRY[scale_key]
    if result < defn.min or result > defn.max:
        raise invalid_input(
            f"Result {result} is outside the valid range "
            f"[{defn.min}, {defn.max}] for the {scale_key} scale."
        )

    classification = get_gpa_classification(result, scale_key)

    calc = Calculation(
        session_id=session.session_id,
        user_id=None,
        expression=f"{body.expression} on {defn.label}",
        result=result,
        scale_from=scale_key,
        scale_to=None,
    )
    db.add(calc)

    session.calc_count += 1
    db.flush()

    return GuestCalculateResponse(
        result=result,
        scale=scale_key,
        classification=classification,
        calc_count=session.calc_count,
        calcs_remaining=max(0, 5 - session.calc_count),
    )


@router.post("/convert", response_model=GuestConvertResponse)
@limiter.limit("20/minute")
def guest_convert(
    request: Request,
    body: GuestConvertRequest,
    db: Session = Depends(get_db),
    session: GuestSession = Depends(get_guest_session),
):
    if session.limit_reached:
        raise calc_limit_reached()

    try:
        from_key = _resolve_scale_key(body.from_scale)
        to_key   = _resolve_scale_key(body.to_scale)
    except ValueError as exc:
        raise invalid_scale(str(exc))

    try:
        converted = convert_gpa(body.gpa, from_key, to_key)
    except ValueError as exc:
        raise invalid_input(str(exc))

    description    = describe_conversion(body.gpa, from_key, to_key)
    classification = get_gpa_classification(converted, to_key)

    # All scales breakdown
    try:
        multi = convert_gpa_multi(body.gpa, from_key)
        all_scales = [
            {
                "scale": scale,
                "value": round(value, 2),
                "classification": get_gpa_classification(value, scale),
            }
            for scale, value in multi.items()
        ]
    except Exception:
        all_scales = []

    calc = Calculation(
        session_id=session.session_id,
        user_id=None,
        expression=description,
        result=converted,
        scale_from=from_key,
        scale_to=to_key,
    )
    db.add(calc)

    session.calc_count += 1
    db.flush()

    return GuestConvertResponse(
        gpa=body.gpa,
        from_scale=from_key,
        to_scale=to_key,
        converted=converted,
        description=description,
        classification=classification,
        calc_count=session.calc_count,
        calcs_remaining=max(0, 5 - session.calc_count),
        all_scales=all_scales,
    )