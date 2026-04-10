from __future__ import annotations

import ast
import os

from ._types import CategoryScore, FileInfo, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"critical": 10, "warning": 5, "info": 2}


def _is_test_file(path: str) -> bool:
    base = os.path.basename(path)
    return base.startswith("test_") or base.endswith("_test.py")


def _is_source_file(fi: FileInfo) -> bool:
    """A Python source file that isn't a test, conftest, or setup."""
    if fi.language != "python":
        return False
    base = os.path.basename(fi.path)
    if _is_test_file(fi.path):
        return False
    if base in ("conftest.py", "setup.py"):
        return False
    return True


def _count_test_functions(path: str) -> int:
    """Parse a Python file and count functions starting with test_."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except (OSError, ValueError):
        return 0

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError:
        return 0

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                count += 1
    return count


def _has_assert(path: str) -> bool:
    """Check if a file contains any assert statement."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except (OSError, ValueError):
        return False
    return "assert" in source


def _has_ci_config(root: str) -> bool:
    """Check for common CI configuration files."""
    # GitHub Actions
    gh_dir = os.path.join(root, ".github", "workflows")
    if os.path.isdir(gh_dir):
        for f in os.listdir(gh_dir):
            if f.endswith((".yml", ".yaml")):
                return True

    # GitLab CI
    if os.path.isfile(os.path.join(root, ".gitlab-ci.yml")):
        return True

    # Jenkins
    if os.path.isfile(os.path.join(root, "Jenkinsfile")):
        return True

    return False


def analyze_testing(files: list[FileInfo], root: str) -> CategoryScore:
    """Analyse test coverage and quality."""
    issues: list[Issue] = []

    # Identify test files and source files
    test_files: list[FileInfo] = []
    source_files: list[FileInfo] = []

    for fi in files:
        if fi.language != "python":
            continue
        if _is_test_file(fi.path):
            test_files.append(fi)
        elif _is_source_file(fi):
            source_files.append(fi)

    total_test_functions = 0

    # VC501: no test files
    if not test_files:
        issues.append(Issue("VC501", "critical", "No test files found"))
        return CategoryScore(
            name="Testing",
            score=0.0,
            grade="F",
            issues=issues,
            details={
                "test_file_count": 0,
                "test_function_count": 0,
                "source_file_count": len(source_files),
                "test_ratio": 0.0,
            },
        )

    # Count test functions
    for tf in test_files:
        full_path = os.path.join(root, tf.path)
        total_test_functions += _count_test_functions(full_path)

        # VC505: test file with no assertions
        if not _has_assert(full_path):
            issues.append(Issue("VC505", "info", f"Test file has no assertions: {tf.path}", tf.path))

    # VC502: low test count
    if total_test_functions < 10:
        issues.append(Issue("VC502", "warning", f"Low test count ({total_test_functions} test functions, recommended ≥10)"))

    # VC503: no CI config
    if not _has_ci_config(root):
        issues.append(Issue("VC503", "info", "No CI configuration found"))

    # VC504: no conftest.py
    has_conftest = any(os.path.basename(fi.path) == "conftest.py" for fi in files if fi.language == "python")
    if not has_conftest:
        issues.append(Issue("VC504", "warning", "No conftest.py found"))

    # VC506: low test-to-code ratio
    test_ratio = len(test_files) / max(len(source_files), 1)
    if test_ratio < 0.30:
        issues.append(
            Issue(
                "VC506",
                "warning",
                f"Low test-to-code ratio ({len(test_files)} test files / {len(source_files)} source files = {test_ratio:.0%})",
            )
        )

    # Score
    score = 100.0
    for iss in issues:
        score -= _SEVERITY_DEDUCT.get(iss.severity, 0)
    score = max(0.0, min(100.0, score))

    return CategoryScore(
        name="Testing",
        score=round(score, 1),
        grade=score_to_grade(score),
        issues=issues,
        details={
            "test_file_count": len(test_files),
            "test_function_count": total_test_functions,
            "source_file_count": len(source_files),
            "test_ratio": round(test_ratio, 2),
        },
    )
