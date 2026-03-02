from dataclasses import dataclass
from typing import Optional
from .grade_mapper import GRADE_TABLES, SCALE_REGISTRY,  _require_valid_scale, _resolve_scale_key, grade_to_point
from .gpa_engine import Course, SemesterRecord, calculate_cgpa, calculate_semester_gpa

@dataclass 
class TargetGradeResult:
    target_gpa: float
    required_grade_point: float
    required_letter_grade: Optional[str]
    is_acheivable: bool
    current_cgpa: float
    projected_cgpa: float

@dataclass
class ProjectionResult:
    projected_cgpa: float
    scale: float
    total_credit_hours: int
    completed_credit_hours: int
    projected_credit_hours: int
    

def find_target_grade_point(
    completed_semesters: list[SemesterRecord],
    remaining_courses: list[Course],
    target_cgpa: float,
    scale: float,
) -> TargetGradeResult:
    

    _require_valid_scale(scale)

    scale_key = _resolve_scale_key(scale)
    scale_max = SCALE_REGISTRY[scale_key].max

    if not remaining_courses:
        raise ValueError("remaining_courses cannot be empty.")
    
    if target_cgpa < 0 or target_cgpa > scale_max:
        raise ValueError(
             f"target_cgpa {target_cgpa} must be between 0 and {scale_max}."
        )
        
    current_cgpa = 0.0
    completed_credits = 0
    completed_points = 0.0
    
    
    if completed_semesters:
        cgpa_result = calculate_cgpa(completed_semesters, scale)
        current_cgpa = cgpa_result.gpa
        completed_credits = cgpa_result.total_credit_hours
        completed_points = cgpa_result.total_grade_points
    
    remaining_credits = sum(c.credit_hours for c in remaining_courses)
    total_credits = completed_credits + remaining_credits
    
    if remaining_credits == 0:
        raise ValueError(
            "Total remaining credit hours summed to zero."
        )
    
    required_point = (
        ((target_cgpa * total_credits)- completed_points)/ remaining_credits
    )
    
    required_point = round(required_point , 4)
    
    scale_key = _resolve_scale_key(scale)
    max_grade_point = max(GRADE_TABLES[scale_key].values())
    min_grade_point = min(GRADE_TABLES[scale_key].values())
    
    is_acheivable = min_grade_point <= required_point <= max_grade_point
    
    closest_letter = _find_minimum_passing_grade(required_point, scale)
    
    
    if is_acheivable and closest_letter is not None:
        actual_point = grade_to_point(closest_letter, scale)
        projected_total_points = completed_points + actual_point * remaining_credits
        projected_cgpa = round(projected_total_points / total_credits, 2)
        
    else:
        projected_total_points = completed_points + required_point * remaining_credits
        projected_cgpa = round(projected_total_points / total_credits, 2)
        
    return TargetGradeResult(
        target_gpa= target_cgpa,
        required_grade_point=required_point,
        required_letter_grade=closest_letter,
        is_acheivable=is_acheivable,
        current_cgpa=current_cgpa,
        projected_cgpa=projected_cgpa,
    )
    

def project_cgpa(
    completed_semesters: list[SemesterRecord],
    upcoming_courses: list[Course],
    scale: float,
    
) -> ProjectionResult:
    
    _require_valid_scale(scale)
    if not upcoming_courses:
        raise ValueError("upcoming_courses cannot be empty.")
    
    completed_credits = 0
    completed_points = 0.0
    
    if completed_semesters:
        cgpa_result =calculate_cgpa(completed_semesters, scale)
        completed_credits= cgpa_result.total_credit_hours
        completed_points = cgpa_result.total_grade_points
        
        
    
    upcoming_result = calculate_semester_gpa(upcoming_courses, scale)
    upcoming_credits = upcoming_result.total_credit_hours
    upcoming_points = upcoming_result.total_grade_points
    
    total_credits = completed_credits + upcoming_credits
    total_points = completed_points + upcoming_points
    
    
    if total_credits == 0:
        raise ValueError("Total credit hours is zero — cannot project CGPA.")
    
    projected_cgpa = round(total_points / total_credits, 2)
    
    
    return ProjectionResult(
        projected_cgpa=projected_cgpa,
        scale=scale,
        total_credit_hours=total_credits,
        completed_credit_hours= completed_credits,
        projected_credit_hours=upcoming_credits,
    )
    
    
def _find_minimum_passing_grade(required_point: float, scale: float) -> Optional[str]:
    
    table = GRADE_TABLES[_resolve_scale_key(scale)]
    
    sorted_grades = sorted(table.items(), key=lambda kv: kv[1])
    
    
    best_match = None
    
    for letter, point in sorted_grades:
        if point >= required_point - 1e-9:
            if best_match is None:
                best_match = letter
            else:
                if point < grade_to_point(best_match, scale):
                    best_match = letter
    return best_match