
from backend.core.grade_mapper import (
    SCALE_REGISTRY, ScaleDefinition,
    _resolve_scale_key,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_gpa(gpa: float, from_scale: "str | float", to_scale: "str | float") -> float:

    # Resolve both scales to string keys immediately
    from_key = _resolve_scale_key(from_scale)
    to_key   = _resolve_scale_key(to_scale)
    from_def = SCALE_REGISTRY[from_key]
    to_def   = SCALE_REGISTRY[to_key]

    _validate_gpa_range(gpa, from_def, from_key)

    # Same scale — return as-is
    if from_key == to_key:
        return round(gpa, 2)

    # Hard fail: range-bound source below pass floor
    if from_def.is_range_bound and gpa < from_def.pass_threshold:
        return 0.0

    # Hard fail: inverted source above pass ceiling
    if from_def.is_inverted and gpa > from_def.pass_threshold:
        return 0.0

    # Step 1 — normalise source to a 0–1 performance ratio (1.0 = best)
    
    ratio = _to_performance_ratio(gpa, from_def, to_def)

    # Step 2 — project ratio onto target scale
    converted = _from_performance_ratio(ratio, to_def, from_def)

    return round(converted, 2)


def convert_gpa_multi(gpa: float, from_scale: "str | float") -> dict[str, float]:

    from_key = _resolve_scale_key(from_scale)
    from_def = SCALE_REGISTRY[from_key]
    _validate_gpa_range(gpa, from_def, from_key)

    return {
        key: convert_gpa(gpa, from_key, key)
        for key in sorted(SCALE_REGISTRY.keys())
    }


def describe_conversion(gpa: float, from_scale: "str | float", to_scale: "str | float") -> str:

    from_key   = _resolve_scale_key(from_scale)
    to_key     = _resolve_scale_key(to_scale)
    result     = convert_gpa(gpa, from_key, to_key)
    from_label = SCALE_REGISTRY[from_key].label
    to_label   = SCALE_REGISTRY[to_key].label
    return f"{gpa} on {from_label} → {result} on {to_label}"


def get_gpa_classification(gpa: float, scale: "str | float") -> str:
    scale_key = _resolve_scale_key(scale)
    defn      = SCALE_REGISTRY[scale_key]
    _validate_gpa_range(gpa, defn, scale_key)

    if defn.is_inverted:
        # Lower is better. pass_threshold is a ceiling — above it is fail.
        if gpa > defn.pass_threshold:
            return _lowest_band(defn)
        # Ratio within effective passing range [min, pass_threshold]:
        # 1.0 = best (min), 0.0 = lowest pass (pass_threshold)
        effective_range = defn.pass_threshold - defn.min
        if effective_range == 0:
            return _lowest_band(defn)
        ratio = (defn.pass_threshold - gpa) / effective_range
    else:
        # Higher is better. pass_threshold is a floor — below it is fail.
        if gpa < defn.pass_threshold:
            return _lowest_band(defn)
        if defn.is_range_bound:
            # Range-bound: effective passing range is [pass_threshold, max]
            effective_range = defn.max - defn.pass_threshold
            ratio = (gpa - defn.pass_threshold) / effective_range if effective_range else 1.0
        else:
            # Linear: classify within full [0, max] range
            ratio = gpa / defn.max if defn.max else 1.0

    return _classify_ratio(ratio, defn)


# ---------------------------------------------------------------------------
# Internal — normalisation and projection
# ---------------------------------------------------------------------------

def _to_performance_ratio(gpa, from_def, to_def):
    if from_def.is_inverted:
        return (from_def.max - gpa) / (from_def.max - from_def.min)
    
    if from_def.is_range_bound or to_def.is_range_bound:
        effective_range = from_def.max - from_def.pass_threshold
        return (gpa - from_def.pass_threshold) / effective_range
    else:
        return gpa / from_def.max

def _from_performance_ratio(ratio, to_def, from_def):
    if to_def.is_inverted:
        return to_def.max - ratio * (to_def.max - to_def.min)
    
    if from_def.is_range_bound or to_def.is_range_bound:
        effective_range = to_def.max - to_def.pass_threshold
        return ratio * effective_range + to_def.pass_threshold
    else:
        return ratio * to_def.max

# ---------------------------------------------------------------------------
# Internal — classification helpers
# ---------------------------------------------------------------------------

def _classify_ratio(ratio: float, defn: ScaleDefinition) -> str:

    for threshold, label in sorted(defn.classification_bands.items(), reverse=True):
        if ratio >= threshold:
            return label
    return _lowest_band(defn)


def _lowest_band(defn: ScaleDefinition) -> str:

    return defn.classification_bands.get(
        min(defn.classification_bands.keys()),
        "Below Pass / Fail"
    )


# ---------------------------------------------------------------------------
# Internal — validation
# ---------------------------------------------------------------------------

def _validate_gpa_range(gpa: float, defn: ScaleDefinition, key: str) -> None:

    import math
    if not isinstance(gpa, (int, float)) or isinstance(gpa, bool):
        raise ValueError(f"GPA must be a number, got {type(gpa).__name__}.")
    if not math.isfinite(gpa):
        raise ValueError(f"GPA must be a finite number, got {gpa}.")

    lo = defn.min
    hi = defn.max

    if gpa < lo:
        raise ValueError(
            f"GPA {gpa} is below the minimum of {lo} for the {key} scale."
        )
    if gpa > hi:
        raise ValueError(
            f"GPA {gpa} exceeds the maximum of {hi} for the {key} scale."
        )