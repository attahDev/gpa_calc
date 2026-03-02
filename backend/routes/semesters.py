from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.models.semester import Semester
from backend.schemas.semester import SemesterCreateRequest, SemesterResponse, SemesterListResponse
from backend.schemas.base import OKResponse
from backend.errors import not_found
from backend.limiter import limiter


router = APIRouter(prefix="/semesters", tags=["Semesters"])


@router.get("", response_model=SemesterListResponse)
@limiter.limit("60/minute")
def list_semesters(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    semesters = (
        db.query(Semester)
        .filter(Semester.user_id == current_user.id)
        .order_by(Semester.created_at.desc())
        .all()
    )
    semester_data = []
    for sem in semesters:
        course_count = len(sem.courses)
        credit_hours = sum(c.credit_hours for c in sem.courses)
        semester_data.append(SemesterResponse(
            id=sem.id,
            user_id=sem.user_id,
            name=sem.name,
            created_at=sem.created_at,
            course_count=course_count,
            credit_hours=credit_hours,
        ))
    return SemesterListResponse(semesters=semester_data, count=len(semester_data))


@router.post("", response_model=SemesterResponse, status_code=201)
@limiter.limit("20/minute")
def create_semester(
    request: Request,
    body: SemesterCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    semester = Semester(user_id=current_user.id, name=body.name)
    db.add(semester)
    db.flush()
    return SemesterResponse(
        id=semester.id,
        user_id=semester.user_id,
        name=semester.name,
        created_at=semester.created_at,
        course_count=0,
        credit_hours=0,
    )


@router.delete("/{semester_id}", response_model=OKResponse)
@limiter.limit("20/minute")
def delete_semester(
    request: Request,
    semester_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    semester = (
        db.query(Semester)
        .filter(Semester.id == semester_id, Semester.user_id == current_user.id)
        .first()
    )
    if not semester:
        raise not_found("Semester not found")
    db.delete(semester)
    return OKResponse(message="Semester deleted successfully")