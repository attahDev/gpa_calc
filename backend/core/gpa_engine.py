from dataclasses import dataclass
from typing import Optional
from backend.core.grade_mapper import grade_to_point, _require_valid_scale


@dataclass
class Course:
    credit_hours: int
    grade: str
    name: Optional[str] = None


@dataclass
class GPAResult:
    gpa : float
    total_credit_hours: int
    total_grade_points: float
    scale: float
    course_count: int


@dataclass
class SemesterRecord:
    courses: Optional[list[Course]] = None
    

def calculate_semester_gpa(courses: list[Course], scale: float) -> GPAResult:
    
    _require_valid_scale(scale)
    
    if not courses:
        raise ValueError("Cannot calculate GPA: course list is empty.")
    
    total_points = 0.0
    total_credits = 0
    
    for course in courses:
        _validate_credit_hours(course.credit_hours)
        
        grade_point = grade_to_point(course.grade, scale)
        total_points += course.credit_hours * grade_point
        total_credits += course.credit_hours
    
    if total_credits == 0:
        raise ValueError(
            "Total credit hours summed to zero — cannot compute GPA."
        )
    gpa = round(total_points / total_credits, 2)
    
    return GPAResult(
        gpa=gpa,
        total_credit_hours=total_credits,
        total_grade_points=round(total_points, 4),
        scale=scale,
        course_count=len(courses),
    )
    

def calculate_cgpa(semesters: list[SemesterRecord], scale: float) -> GPAResult:
    
    _require_valid_scale(scale)
    if not semesters:
        raise ValueError(
            "Cannot calculate CGPA: semester list is empty"
            )
    
    grand_total_points = 0.0
    grand_total_credits = 0
    total_courses = 0
    
    for i, semester in enumerate(semesters):

        credits, points, n_courses = _resolve_semester(semester, scale, index=i)
        grand_total_credits += credits
        grand_total_points += points
        total_courses += n_courses
        
    if grand_total_credits == 0:
        raise ValueError("Grand total credit hours is zero - cannot compute CGPA")
    
    cgpa = round(grand_total_points/ grand_total_credits, 2)
    
    return GPAResult(
        gpa=cgpa, 
        total_credit_hours=grand_total_credits,
        total_grade_points=round(grand_total_points, 4),
        scale=scale,
        course_count=total_courses,
    )

def recalculate_grade_points(
    courses: list[Course],
    old_scale: float,
    new_scale: float,
) -> list[tuple[Course, float]]:
    
    
    _require_valid_scale(old_scale)
    _require_valid_scale(new_scale)
    
    results = []
    for course in courses:
        new_point = grade_to_point(course.grade, new_scale)
        results.append((course, new_point))
    return results



def _resolve_semester(
    semester:SemesterRecord,
    scale: float,
    index: int,
) -> tuple[int, float, int]:
    
    has_courses = semester.courses is not None and len(semester.courses) > 0
    # has_precomputed = (
    #     semester.total_credit_hours is not None and semester.total_grade_points is not None
    # )
    
    
    # if has_precomputed:
    #     if semester.total_credit_hours < 0:
    #         raise ValueError(f"Semester {index}: total_credit_hours cannot be negative.")
    #     if semester.total_grade_points < 0:
    #         raise ValueError(f"Semester {index}: total_grade_points cannot be negative.")
    #     return (semester.total_credit_hours, semester.total_grade_points, 0)

    if has_courses:
        result = calculate_semester_gpa(semester.courses, scale)
        return (result.total_credit_hours, result.total_grade_points, result.course_count)
    
    raise ValueError(
        f"Semester at index {index} has neither courses nor pre-computed totals."
    )
    
def _validate_credit_hours(credit_hours: int) -> None:
    if not isinstance(credit_hours, int) or isinstance(credit_hours, bool):
        raise ValueError(f"Credit_hours must be an integer, got {type}")
    
    if credit_hours < 1 or credit_hours > 10:
        raise ValueError(
            f"credit_hours must be between 1 and 10, got {credit_hours}."
        )