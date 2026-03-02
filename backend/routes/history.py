from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.models.calculation import Calculation
from backend.schemas.calculation import HistoryResponse
from backend.schemas.base import OKResponse
from backend.limiter import limiter

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=HistoryResponse)
@limiter.limit("60/minute")
def get_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = (
        db.query(Calculation)
        .filter(Calculation.user_id == current_user.id)
        .order_by(Calculation.created_at.desc())
        .all()
    )
    return HistoryResponse(history=history, count=len(history))


@router.delete("", response_model=OKResponse)
@limiter.limit("10/minute")
def clear_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Calculation).filter(Calculation.user_id == current_user.id).delete()
    return OKResponse(message="History cleared successfully")