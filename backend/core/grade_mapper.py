
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Classification band defaults
# Shared by all standard academic scales unless overridden in the registry.
# Keys are the LOWER bound of each band (ratio >= key → that classification).
# Sorted descending so the first match wins.
# ---------------------------------------------------------------------------

STANDARD_BANDS: dict[float, str] = {
    0.875: "First Class / Distinction",
    0.750: "Second Class Upper / Merit",
    0.625: "Second Class Lower / Credit",
    0.500: "Third Class / Pass",
    0.000: "Below Pass / Fail",
}

GERMAN_BANDS: dict[float, str] = {
    0.833: "Sehr gut (Very Good)",
    0.500: "Gut (Good)",
    0.167: "Befriedigend (Satisfactory)",
    0.000: "Ausreichend (Sufficient — Lowest Pass)",
   -1.000: "Nicht bestanden (Fail)",   
}

ITALIAN_110_BANDS: dict[float, str] = {
    0.977: "First Class / Distinction",  # ~109+
    0.772: "Second Class Upper / Merit", # ~100+
    0.545: "Second Class Lower / Credit", # ~90+
    0.000: "Third Class / Pass",
}
ITALIAN_30_BANDS: dict[float, str] = {
    0.977: "First Class / Distinction",   # 30+
    0.750: "Second Class Upper / Merit",  # 27+
    0.500: "Second Class Lower / Credit", # 24+
    0.000: "Third Class / Pass",          # 18+
}

# ---------------------------------------------------------------------------
# ScaleDefinition dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScaleDefinition:
    max:                  float             # highest grade point (worst if inverted)
    min:                  float             # lowest grade point (best if inverted)
    pass_threshold:       float             # pass/fail boundary (floor or ceiling — see is_inverted)
    label:                str               # display name for UI
    region:               str               # geographic/institutional context
    is_range_bound:       bool              # True = non-zero conversion floor/ceiling
    is_inverted:          bool              # True = lower is better (e.g. German scale)
    classification_bands: dict[float, str]  # performance ratio → label, sorted descending


# ---------------------------------------------------------------------------
# Scale registry — the ONLY place scales are defined
# ---------------------------------------------------------------------------

SCALE_REGISTRY: dict[str, ScaleDefinition] = {

    # ── LINEAR SCALES (is_range_bound=False, is_inverted=False) ─────────────
    # Conversion uses full [0, max] range.
    # pass_threshold used for classification only.

    "4.0": ScaleDefinition(
        max=4.0,
        min=0.0,
        pass_threshold=1.0,       # D grade — lowest recorded pass
        label="4.0 Scale (US/Canada)",
        region="US/Canada",
        is_range_bound=False,
        is_inverted=False,
        classification_bands=STANDARD_BANDS,
    ),

    "5.0": ScaleDefinition(
        max=5.0,
        min=0.0,
        pass_threshold=1.0,       # E grade — lowest recorded pass
        label="5.0 Scale (Nigeria/West Africa)",
        region="Nigeria",
        is_range_bound=False,
        is_inverted=False,
        classification_bands=STANDARD_BANDS,
    ),

    # ── INVERTED SCALES (is_range_bound=False, is_inverted=True) ────────────
    # Lower grade point = better performance.
    # pass_threshold is a CEILING — grades above it are a fail.
    # min = best possible grade (1.0), max = worst possible grade (6.0).

    "6.0_DE": ScaleDefinition(
        max=4.0,                  # worst grade (Ungenügend)
        min=1.0,                  # best grade (Sehr gut)
        pass_threshold=4.0,       # grades <= 4.0 pass, > 4.0 fail
        label="6-Point Scale (Germany)",
        region="Germany",
        is_range_bound=True,
        is_inverted=True,
        classification_bands=GERMAN_BANDS,
    ),

    # ── RANGE-BOUND SCALES (is_range_bound=True, is_inverted=False) ─────────
    # Non-zero conversion floor. Grades below pass_threshold never recorded.
    # pass_threshold used for BOTH conversion and classification.

    "110": ScaleDefinition(
        max=110.0,
        min=0.0,
        pass_threshold=66.0,      # grades below 66 not recorded — students retake
        label="110 Scale (Italy — final degree)",
        region="Italy",
        is_range_bound=True,
        is_inverted=False,
        classification_bands=ITALIAN_110_BANDS,
    ),

    "30": ScaleDefinition(
        max=30.0,
        min=0.0,
        pass_threshold=18.0,      # grades below 18 not recorded — students retake
        label="30 Scale (Italy — course grade)",
        region="Italy",
        is_range_bound=True,
        is_inverted=False,
        classification_bands=ITALIAN_30_BANDS,
    ),
}

# Supported scale keys as a set — fast membership checks
SUPPORTED_SCALE_KEYS: set[str] = set(SCALE_REGISTRY.keys())

_FLOAT_TO_KEY: dict[float, str] = {
    4.0: "4.0",
    5.0: "5.0",
}


# ---------------------------------------------------------------------------
# Grade point tables — keyed by scale key string
# ---------------------------------------------------------------------------

GRADE_TABLES: dict[str, dict[str, float]] = {

    "4.0": {
        "A":  4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B":  3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C":  2.0,
        "C-": 1.7,
        "D+": 1.3,
        "D":  1.0,   # lowest pass
        "D-": 0.7,
        "F":  0.0,
    },

    "5.0": {
        # Nigerian CGPA system (UNILAG, UI, OAU, etc.)
        "A":  5.0,
        "B":  4.0,
        "C":  3.0,
        "D":  2.0,
        "E":  1.0,   # lowest pass
        "F":  0.0,
    },

    "6.0_DE": {
        "1.0": 1.0,  # Sehr gut (Very Good)
        "1.3": 1.3,
        "1.7": 1.7,
        "2.0": 2.0,  # Gut (Good)
        "2.3": 2.3,
        "2.7": 2.7,
        "3.0": 3.0,  # Befriedigend (Satisfactory)
        "3.3": 3.3,
        "3.7": 3.7,
        "4.0": 4.0,  # Ausreichend (Sufficient) — lowest pass
        "5.0": 5.0,  # Mangelhaft (Deficient) — fail
        "6.0": 6.0,  # Ungenügend (Insufficient) — worst fail
    },

    "110": {
       
        "110L": 110.0,  # 110 con lode (with honours)
        "110":  110.0,
        "109":  109.0, "108": 108.0, "107": 107.0, "106": 106.0,
        "105":  105.0, "104": 104.0, "103": 103.0, "102": 102.0,
        "101":  101.0, "100": 100.0,
        "99":    99.0,  "98":  98.0,  "97":  97.0,  "96":  96.0,
        "95":    95.0,  "94":  94.0,  "93":  93.0,  "92":  92.0,
        "91":    91.0,  "90":  90.0,
        "89":    89.0,  "88":  88.0,  "87":  87.0,  "86":  86.0,
        "85":    85.0,  "84":  84.0,  "83":  83.0,  "82":  82.0,
        "81":    81.0,  "80":  80.0,
        "79":    79.0,  "78":  78.0,  "77":  77.0,  "76":  76.0,
        "75":    75.0,  "74":  74.0,  "73":  73.0,  "72":  72.0,
        "71":    71.0,  "70":  70.0,
        "69":    69.0,  "68":  68.0,  "67":  67.0,  "66":  66.0,
        "FAIL":   0.0,  # explicit fail marker — below 66
    },

    "30": {
        "30L": 30.0,   # 30 con lode (with honours)
        "30":  30.0,   "29": 29.0,  "28": 28.0,  "27": 27.0,
        "26":  26.0,   "25": 25.0,  "24": 24.0,  "23": 23.0,
        "22":  22.0,   "21": 21.0,  "20": 20.0,  "19": 19.0,
        "18":  18.0,
        "FAIL": 0.0,   # explicit fail marker — below 18
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_scale_definition(scale_key: str) -> ScaleDefinition:
   
    _require_valid_scale_key(scale_key)
    return SCALE_REGISTRY[scale_key]


def get_valid_grades(scale_key: str) -> list[str]:
    
    _require_valid_scale_key(scale_key)
    return list(GRADE_TABLES[scale_key].keys())


def grade_to_point(grade: str, scale: "str | float") -> float:

    scale_key  = _resolve_scale_key(scale)   # resolve once, use everywhere
    normalised = grade.strip().upper()
    table      = GRADE_TABLES[scale_key]

    if normalised not in table:
        valid = ", ".join(table.keys())
        raise ValueError(
            f"Grade '{grade}' is not valid for the {scale_key} scale. "
            f"Valid grades: {valid}"
        )
    return table[normalised]


def point_to_grade(point: float, scale: "str | float") -> Optional[str]:

    scale_key = _resolve_scale_key(scale)
    table     = GRADE_TABLES[scale_key]
    for letter, value in table.items():
        if abs(value - point) < 1e-9:   # float-safe equality
            return letter
    return None


def is_valid_grade(grade: str, scale: "str | float") -> bool:

    try:
        scale_key = _resolve_scale_key(scale)
    except ValueError:
        return False
    normalised = grade.strip().upper()
    return normalised in GRADE_TABLES[scale_key]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_scale_key(scale: "str | float"):
    if isinstance(scale, bool):
        raise ValueError(f"scale must be a string or number, got bool.")

    if isinstance(scale, (int, float)):
        key = _FLOAT_TO_KEY.get(float(scale))
        if key:
            return key
        raise ValueError(
            f"Scale {scale} has no float alias. "
            f"Use a string key: {sorted(SUPPORTED_SCALE_KEYS)}"
        )

    if isinstance(scale, str):
        if scale in SCALE_REGISTRY:
            return scale
        raise ValueError(
            f"Scale '{scale}' is not supported. "
            f"Supported keys: {sorted(SUPPORTED_SCALE_KEYS)}"
        )

    raise ValueError(
        f"scale must be a string or number, got {type(scale).__name__}."
    )


def _require_valid_scale_key(key: str) -> None:
    """Raise ValueError if key is not in the registry. Expects a string."""
    if not isinstance(key, str) or key not in SCALE_REGISTRY:
        raise ValueError(
            f"Scale '{key}' is not supported. "
            f"Supported keys: {sorted(SUPPORTED_SCALE_KEYS)}"
        )


def _require_valid_scale(scale: "str | float") -> None:
    _resolve_scale_key(scale)


SUPPORTED_SCALES: set[float] = {4.0, 5.0}