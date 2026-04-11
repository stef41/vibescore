from __future__ import annotations

import os
import time

from .discovery import discover_files, detect_project_type
from .quality import analyze_quality
from .quality_js import analyze_quality_js
from .quality_rs import analyze_quality_rs
from .quality_go import analyze_quality_go
from .security import analyze_security
from .deps import analyze_deps
from .testing import analyze_testing
from .scoring import compute_overall, score_to_grade
from ._types import CategoryScore, VibeReport


def scan(path: str) -> VibeReport:
    """Scan a project directory and return a full vibe report."""
    start = time.perf_counter()
    root = str(path)

    files = discover_files(root)

    # Count languages
    languages: dict[str, int] = {}
    for f in files:
        languages[f.language] = languages.get(f.language, 0) + 1

    # Run all analysers
    py_files = [f for f in files if f.language == "python"]
    js_files = [f for f in files if f.language in ("javascript", "typescript")]
    rs_files = [f for f in files if f.language == "rust"]
    go_files = [f for f in files if f.language == "go"]

    quality_scores: list[tuple[CategoryScore, int]] = []
    if py_files:
        quality_scores.append((analyze_quality(py_files, root), len(py_files)))
    if js_files:
        quality_scores.append((analyze_quality_js(js_files, root), len(js_files)))
    if rs_files:
        quality_scores.append((analyze_quality_rs(rs_files, root), len(rs_files)))
    if go_files:
        quality_scores.append((analyze_quality_go(go_files, root), len(go_files)))

    if quality_scores:
        total_files = sum(count for _, count in quality_scores)
        merged_score = sum(cat.score * count for cat, count in quality_scores) / total_files
        all_quality_issues: list = []
        for cat, _ in quality_scores:
            all_quality_issues.extend(cat.issues)
        quality = CategoryScore(
            name="Code Quality",
            score=round(merged_score, 1),
            grade=score_to_grade(merged_score),
            issues=all_quality_issues,
        )
    else:
        quality = CategoryScore(name="Code Quality", score=100.0, grade="A+", issues=[])

    security = analyze_security(files, root)
    deps = analyze_deps(root)
    testing = analyze_testing(files, root)

    categories = [quality, security, deps, testing]
    overall_score, overall_grade = compute_overall(categories)

    project_name = os.path.basename(os.path.abspath(root))

    return VibeReport(
        project_path=root,
        project_name=project_name,
        total_files=len(files),
        total_lines=sum(f.lines for f in files),
        languages=languages,
        categories=categories,
        overall_score=overall_score,
        overall_grade=overall_grade,
        scan_time_s=time.perf_counter() - start,
    )
