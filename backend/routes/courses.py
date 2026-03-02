from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.models.semester import Semester
from backend.models.course import Course
from backend.schemas.course import (
    CourseCreateRequest,
    CourseUpdateRequest,
    CourseResponse,
    CourseListResponse,
)
from backend.schemas.base import OKResponse
from backend.core.grade_mapper import grade_to_point, is_valid_grade
from backend.errors import not_found, invalid_grade
from backend.limiter import limiter


router = APIRouter(tags=["courses"])


def _get_semester_for_user(semester_id: str, user_id: str, db: Session) -> Semester:
    semester = (
        db.query(Semester)
        .filter(Semester.id == semester_id, Semester.user_id == user_id)
        .first()
    )
    if not semester:
        raise not_found("Semester")
    return semester


@router.get("/semesters/{semester_id}/courses", response_model=CourseListResponse)
@limiter.limit("60/minute")
def list_courses(
    request: Request,
    semester_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_semester_for_user(semester_id, current_user.id, db)
    courses = (
        db.query(Course)
        .filter(Course.semester_id == semester_id)
        .order_by(Course.created_at.asc())
        .all()
    )
    return CourseListResponse(courses=courses, count=len(courses))


@router.post("/semesters/{semester_id}/courses", response_model=CourseResponse, status_code=201)
@limiter.limit("30/minute")
def add_course(
    request: Request,
    semester_id: str,
    body: CourseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_semester_for_user(semester_id, current_user.id, db)

    scale_key = current_user.gpa_scale
    if not is_valid_grade(body.grade, scale_key):
        raise invalid_grade(body.grade, scale_key)

    grade_point = grade_to_point(body.grade, scale_key)
    course = Course(
        semester_id=semester_id,
        name=body.name,
        credit_hours=body.credit_hours,
        grade=body.grade,
        grade_point=grade_point,
    )
    db.add(course)
    db.flush()
    return course


@router.patch("/courses/{course_id}", response_model=CourseResponse)
@limiter.limit("30/minute")
def update_course(
    request: Request,
    course_id: str,
    body: CourseUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .join(Semester, Course.semester_id == Semester.id)
        .filter(Course.id == course_id, Semester.user_id == current_user.id)
        .first()
    )
    if not course:
        raise not_found("Course")

    scale_key = current_user.gpa_scale

    if body.name is not None:
        course.name = body.name
    if body.credit_hours is not None:
        course.credit_hours = body.credit_hours
    if body.grade is not None:
        if not is_valid_grade(body.grade, scale_key):
            raise invalid_grade(body.grade, scale_key)
        course.grade = body.grade
        course.grade_point = grade_to_point(body.grade, scale_key)

    db.flush()
    return course


@router.delete("/courses/{course_id}", response_model=OKResponse)
@limiter.limit("30/minute")
def delete_course(
    request: Request,
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .join(Semester, Course.semester_id == Semester.id)
        .filter(Course.id == course_id, Semester.user_id == current_user.id)
        .first()
    )
    if not course:
        raise not_found("Course")

    db.delete(course)
    return OKResponse(message="Course deleted.")