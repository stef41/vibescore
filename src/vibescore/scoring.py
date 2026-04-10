from __future__ import annotations

from ._types import CategoryScore

_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (97, "A+"),
    (93, "A"),
    (90, "A-"),
    (87, "B+"),
    (83, "B"),
    (80, "B-"),
    (77, "C+"),
    (73, "C"),
    (70, "C-"),
    (67, "D+"),
    (63, "D"),
    (60, "D-"),
]

_DEFAULT_WEIGHTS: dict[str, float] = {
    "security": 0.30,
    "quality": 0.25,
    "dependencies": 0.20,
    "testing": 0.25,
}


def score_to_grade(score: float) -> str:
    """Convert a 0-100 numeric score to a letter grade."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def compute_overall(
    categories: list[CategoryScore],
    weights: dict[str, float] | None = None,
) -> tuple[float, str]:
    """Compute the weighted-average overall score and grade."""
    w = weights or _DEFAULT_WEIGHTS

    # Build a lowercase name -> category map
    cat_map: dict[str, CategoryScore] = {}
    for cat in categories:
        key = cat.name.lower().replace(" ", "").replace("_", "")
        # Normalise common names
        if "security" in key:
            cat_map["security"] = cat
        elif "quality" in key:
            cat_map["quality"] = cat
        elif "depend" in key or "dep" in key:
            cat_map["dependencies"] = cat
        elif "test" in key:
            cat_map["testing"] = cat
        else:
            cat_map[key] = cat

    total_weight = 0.0
    weighted_sum = 0.0
    for name, weight in w.items():
        if name in cat_map:
            weighted_sum += cat_map[name].score * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0, "F"

    score = round(weighted_sum / total_weight, 1)
    score = max(0.0, min(100.0, score))
    return score, score_to_grade(score)
