from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.models.semester import Semester
from backend.models.course import Course as CourseModel
from backend.models.calculation import Calculation
from backend.limiter import limiter

from backend.core.gpa_engine import (
    Course as EngCourse,
    SemesterRecord,
    calculate_semester_gpa,
    calculate_cgpa,
)
from backend.core.converter import (
    convert_gpa,
    convert_gpa_multi,
    describe_conversion,
    get_gpa_classification,
)
from backend.core.projector import find_target_grade_point, project_cgpa
from backend.core.grade_mapper import (
    SCALE_REGISTRY,
    is_valid_grade,
    grade_to_point,
    _resolve_scale_key,
)
from backend.schemas.calculation import (
    ConvertRequest,
    ConvertResponse,
    ConvertMultiResponse,
    GPAResponse,
    TargetGradeRequest,
    TargetGradeResponse,
    ProjectionRequest,
    ProjectionResponse,
)
from backend.errors import not_found, invalid_input, invalid_scale, invalid_grade


router = APIRouter(prefix="/calculations", tags=["Calculations"])


# ── Semester GPA ──────────────────────────────────────────────────────────

@router.get("/gpa/{semester_id}", response_model=GPAResponse)
@limiter.limit("60/minute")
def get_gpa(
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

    courses_db = (
        db.query(CourseModel)
        .filter(CourseModel.semester_id == semester_id)
        .all()
    )
    if not courses_db:
        raise not_found("No courses found for this semester")

    scale_key = current_user.gpa_scale
    engine_courses = [
        EngCourse(name=c.name, credit_hours=c.credit_hours, grade=c.grade)
        for c in courses_db
    ]

    try:
        result = calculate_semester_gpa(engine_courses, scale_key)
    except Exception as e:
        raise invalid_input(str(e))

    classification = get_gpa_classification(result.gpa, scale_key)
    defn = SCALE_REGISTRY[scale_key]

    _save_calculation(
        db=db,
        user_id=current_user.id,
        expression=f"Semester GPA: {semester.name} — {result.gpa} on {defn.label}",
        result=result.gpa,
        scale_from=scale_key,
        scale_to=scale_key,
    )

    return GPAResponse(
        gpa=result.gpa,
        total_credit_hours=result.total_credit_hours,
        total_grade_points=result.total_grade_points,
        classification=classification,
        scale=scale_key,
        scale_label=defn.label,
    )


# ── CGPA ──────────────────────────────────────────────────────────────────

@router.get("/cgpa", response_model=GPAResponse)
@limiter.limit("60/minute")
def get_cgpa(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    semesters_db = (
        db.query(Semester)
        .filter(Semester.user_id == current_user.id)
        .order_by(Semester.created_at.asc())
        .all()
    )
    if not semesters_db:
        raise invalid_input("No semesters found. Add semesters and courses first.")

    scale_key = current_user.gpa_scale
    semester_records = []
    for sem in semesters_db:
        courses_db = (
            db.query(CourseModel)
            .filter(CourseModel.semester_id == sem.id)
            .all()
        )
        if not courses_db:
            continue
        engine_courses = [
            EngCourse(credit_hours=c.credit_hours, grade=c.grade, name=c.name)
            for c in courses_db
        ]
        semester_records.append(SemesterRecord(courses=engine_courses))

    if not semester_records:
        raise invalid_input("No courses found across your semesters. Add courses first.")

    try:
        result = calculate_cgpa(semester_records, scale_key)
    except ValueError as exc:
        raise invalid_input(str(exc))

    classification = get_gpa_classification(result.gpa, scale_key)
    defn = SCALE_REGISTRY[scale_key]

    _save_calculation(
        db=db,
        user_id=current_user.id,
        expression=f"CGPA: {result.gpa} on {defn.label} ({result.total_credit_hours} credits)",
        result=result.gpa,
        scale_from=scale_key,
        scale_to=scale_key,
    )

    return GPAResponse(
        gpa=result.gpa,
        scale=scale_key,
        total_credit_hours=result.total_credit_hours,
        total_grade_points=result.total_grade_points,
        course_count=result.course_count,
        classification=classification,
    )


# ── Convert ───────────────────────────────────────────────────────────────

@router.post("/convert", response_model=ConvertResponse)
@limiter.limit("60/minute")
def convert(
    request: Request,
    body: ConvertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    _save_calculation(
        db=db,
        user_id=current_user.id,
        expression=description,
        result=converted,
        scale_from=from_key,
        scale_to=to_key,
    )

    return ConvertResponse(
        gpa=body.gpa,
        from_scale=from_key,
        to_scale=to_key,
        converted=converted,
        description=description,
        classification=classification,
        all_scales=all_scales,
    )


# ── Target grade ──────────────────────────────────────────────────────────

@router.post("/target-grade", response_model=TargetGradeResponse)
@limiter.limit("30/minute")
def target_grade(
    request: Request,
    body: TargetGradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scale_key = current_user.gpa_scale
    defn      = SCALE_REGISTRY[scale_key]

    if body.target_cgpa < defn.min or body.target_cgpa > defn.max:
        raise invalid_input(
            f"Target CGPA {body.target_cgpa} is outside the valid range "
            f"[{defn.min}, {defn.max}] for the {scale_key} scale."
        )

    semesters_db = (
        db.query(Semester)
        .filter(Semester.user_id == current_user.id)
        .order_by(Semester.created_at.asc())
        .all()
    )

    completed_records = []
    for sem in semesters_db:
        courses_db = db.query(CourseModel).filter(CourseModel.semester_id == sem.id).all()
        if courses_db:
            completed_records.append(SemesterRecord(courses=[
                EngCourse(credit_hours=c.credit_hours, grade=c.grade, name=c.name)
                for c in courses_db
            ]))

    remaining_eng = [
        EngCourse(credit_hours=c.credit_hours, grade="F", name=c.name)
        for c in body.remaining_courses
    ]

    try:
        result = find_target_grade_point(
            completed_semesters=completed_records,
            remaining_courses=remaining_eng,
            target_cgpa=body.target_cgpa,
            scale=scale_key,
        )
    except ValueError as exc:
        raise invalid_input(str(exc))

    return TargetGradeResponse(
        target_cgpa=result.target_gpa,
        required_grade_point=result.required_grade_point,
        required_letter_grade=result.required_letter_grade,
        is_achievable=result.is_acheivable,
        current_cgpa=result.current_cgpa,
        projected_cgpa=result.projected_cgpa,
        scale=scale_key,
    )


# ── Projection ────────────────────────────────────────────────────────────

@router.post("/projection", response_model=ProjectionResponse)
@limiter.limit("30/minute")
def projection(
    request: Request,
    body: ProjectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scale_key = current_user.gpa_scale

    for course in body.upcoming_courses:
        if not is_valid_grade(course.grade, scale_key):
            raise invalid_grade(course.grade, scale_key)

    semesters_db = (
        db.query(Semester)
        .filter(Semester.user_id == current_user.id)
        .order_by(Semester.created_at.asc())
        .all()
    )

    completed_records = []
    for sem in semesters_db:
        courses_db = db.query(CourseModel).filter(CourseModel.semester_id == sem.id).all()
        if courses_db:
            completed_records.append(SemesterRecord(courses=[
                EngCourse(credit_hours=c.credit_hours, grade=c.grade, name=c.name)
                for c in courses_db
            ]))

    upcoming_eng = [
        EngCourse(credit_hours=c.credit_hours, grade=c.grade, name=c.name)
        for c in body.upcoming_courses
    ]

    try:
        result = project_cgpa(
            completed_semesters=completed_records,
            upcoming_courses=upcoming_eng,
            scale=scale_key,
        )
    except ValueError as exc:
        raise invalid_input(str(exc))

    return ProjectionResponse(
        projected_cgpa=result.projected_cgpa,
        scale=scale_key,
        total_credit_hours=result.total_credit_hours,
        completed_credit_hours=result.completed_credit_hours,
        projected_credit_hours=result.projected_credit_hours,
    )


# ── Internal helper ───────────────────────────────────────────────────────

def _save_calculation(
    db: Session,
    user_id: str,
    expression: str,
    result: float,
    scale_from: str,
    scale_to: str | None = None,
    session_id: str | None = None,
) -> None:
    calc = Calculation(
        user_id=user_id,
        session_id=session_id,
        expression=expression,
        result=result,
        scale_from=scale_from,
        scale_to=scale_to if scale_to is not None else scale_from,
    )
    db.add(calc)
    db.flush()