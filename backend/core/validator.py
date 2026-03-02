import ast
import re
import math
from typing import Union
from .grade_mapper import is_valid_grade, _resolve_scale_key, SCALE_REGISTRY, SUPPORTED_SCALE_KEYS, get_valid_grades

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,    
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
    ast.UAdd,
)


def safe_parse_expression(expression: str) -> float:
    if not expression or not expression.strip():
        raise ValueError("Expression cannot be empty.")

    stripped = expression.strip()

    
    if len(stripped) > 200:
        raise ValueError("Expression is too long (max 200 characters).")

    try:
        tree = ast.parse(stripped, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression syntax: {stripped!r}") from exc

    # Walk every node and reject anything not in our whitelist
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(
                f"Expression contains disallowed operation: "
                f"{type(node).__name__}. Only +, -, *, / are supported."
            )

    
    try:
        result = eval(
            compile(tree, filename="<expression>", mode="eval"),
            {"__builtins__": {}},
            {},
        )
    except ZeroDivisionError:
        raise ZeroDivisionError("Expression contains division by zero.")
    except Exception as exc:
        raise ValueError(f"Could not evaluate expression: {exc}") from exc

    if not math.isfinite(result):
        raise ValueError(f"Expression produced a non-finite result: {result}")

    return float(result)


def validate_scale(scale: Union[float, int, str]) -> float:

    try:
        return _resolve_scale_key(scale)
    except ValueError:
        raise ValueError(
            f"{scale!r} is not a supported GPA scale. "
            f"Supported scale keys: {sorted(SUPPORTED_SCALE_KEYS)}"
        )
# ---------------------------------------------------------------------------
# Grade validation
# ---------------------------------------------------------------------------

def validate_grade(grade: str, scale: "str | float") -> str:
    
    scale_key = _resolve_scale_key(scale)

    if not grade or not isinstance(grade, str):
        raise ValueError("Grade must be a non-empty string.")

    normalised = grade.strip().upper()

    if len(normalised) > 5:
        raise ValueError(f"Grade string is too long: {grade!r}")

    
    if not is_valid_grade(normalised, scale_key):

        valid = ", ".join(get_valid_grades(scale_key))
        raise ValueError(
            f"'{grade}' is not a valid grade for the {scale_key} scale. "
            f"Valid grades: {valid}"
        )
    return normalised


# ---------------------------------------------------------------------------
# Credit hours validation
# ---------------------------------------------------------------------------

def validate_credit_hours(value: Union[int, str]) -> int:

    try:
        as_int = int(value)
        # Reject floats that are not whole numbers e.g. 2.5
        if isinstance(value, float) and value != as_int:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError(
            f"Credit hours must be a whole number, got {value!r}."
        )

    if as_int < 1 or as_int > 10:
        raise ValueError(
            f"Credit hours must be between 1 and 10, got {as_int}."
        )
    return as_int


# ---------------------------------------------------------------------------
# GPA value validation
# ---------------------------------------------------------------------------

def validate_gpa_value(gpa: Union[float, int, str], scale: "str | float") -> float:
    scale_key = _resolve_scale_key(scale)
    defn      = SCALE_REGISTRY[scale_key]

    try:
        as_float = float(gpa)
    except (TypeError, ValueError):
        raise ValueError(f"GPA must be a number, got {gpa!r}.")

    if not math.isfinite(as_float):
        raise ValueError(f"GPA must be a finite number, got {gpa!r}.")

    # Use defn.min and defn.max — works for all scale categories
    if as_float < defn.min:
        raise ValueError(
            f"GPA {as_float} is below the minimum of {defn.min} "
            f"for the {scale_key} scale."
        )
    if as_float > defn.max:
        raise ValueError(
            f"GPA {as_float} exceeds the maximum of {defn.max} "
            f"for the {scale_key} scale."
        )
    return round(as_float, 4)


# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

def validate_email(email: str) -> str:
    if not email or not isinstance(email, str):
        raise ValueError("Email must be a non-empty string.")

    stripped = email.strip().lower()

    if len(stripped) > 255:
        raise ValueError("Email exceeds 255 character limit.")

    # Minimal structural check: must have @ with content on both sides and a dot in domain
    pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    if not re.match(pattern, stripped):
        raise ValueError(f"'{email}' does not appear to be a valid email address.")

    return stripped