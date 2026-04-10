from __future__ import annotations

import os
import time

from .discovery import discover_files, detect_project_type
from .quality import analyze_quality
from .security import analyze_security
from .deps import analyze_deps
from .testing import analyze_testing
from .scoring import compute_overall
from ._types import VibeReport


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
    quality = analyze_quality(py_files, root)
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
