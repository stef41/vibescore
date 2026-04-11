from __future__ import annotations

import os
import re

from ._types import CategoryScore, FileInfo, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"critical": 15, "warning": 5, "info": 2}

# Pre-compiled patterns
_RE_SECRET = re.compile(
    r"""(?:api[_\-]?key|secret|token|password|passwd|pwd)\s*[=:]\s*["'][^"']{8,}["']""",
    re.IGNORECASE,
)
_RE_AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
_RE_SQL_INJECT = re.compile(
    r"""(?:execute|cursor\.execute)\s*\([^)]*(?:%s|\.format|f["'])""",
    re.IGNORECASE,
)
_RE_SHELL_INJECT = re.compile(r"\b(?:subprocess\.call|os\.system|os\.popen)\s*\(")
_RE_UNSAFE_DESER = re.compile(r"\b(?:pickle\.load|yaml\.load)\s*\(")
_RE_YAML_SAFE = re.compile(r"Loader\s*=\s*(?:yaml\.)?SafeLoader")
_RE_EVAL_EXEC = re.compile(r"\b(?:eval|exec)\s*\(")
_RE_DEBUG = re.compile(r"DEBUG\s*=\s*True")

_PRIVATE_KEY_PATTERNS = {"*.pem", "*.key", "id_rsa"}


def _is_test_file(path: str) -> bool:
    base = os.path.basename(path).lower()
    parts = path.replace("\\", "/").lower().split("/")
    return base.startswith("test_") or base.endswith("_test.py") or "tests" in parts or "test" in parts


def _read_lines(path: str) -> list[str] | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.readlines()
    except (OSError, ValueError):
        return None


def analyze_security(files: list[FileInfo], root: str) -> CategoryScore:
    """Analyse security issues across all files."""
    issues: list[Issue] = []

    # VC307: no .gitignore
    if not os.path.isfile(os.path.join(root, ".gitignore")):
        issues.append(Issue("VC307", "info", "No .gitignore file found"))

    for fi in files:
        full_path = os.path.join(root, fi.path)

        # VC309: private key files
        base = os.path.basename(fi.path)
        if base in ("id_rsa",) or base.endswith((".pem", ".key")):
            issues.append(Issue("VC309", "critical", f"Private key file: {fi.path}", fi.path))

        # Only scan text source files
        if fi.language == "unknown":
            continue

        lines = _read_lines(full_path)
        if lines is None:
            continue

        is_test = _is_test_file(fi.path)
        is_example = ".env.example" in fi.path or ".env.sample" in fi.path

        for lineno, line in enumerate(lines, start=1):
            # VC301: hardcoded secrets (skip test files and .env.example)
            if not is_test and not is_example and _RE_SECRET.search(line):
                issues.append(
                    Issue("VC301", "critical", "Hardcoded secret detected", fi.path, lineno)
                )

            # VC302: AWS keys
            if _RE_AWS_KEY.search(line):
                issues.append(
                    Issue("VC302", "critical", "Hardcoded AWS access key", fi.path, lineno)
                )

            # VC303: SQL injection
            if _RE_SQL_INJECT.search(line):
                issues.append(
                    Issue("VC303", "warning", "Potential SQL injection via string formatting", fi.path, lineno)
                )

            # VC304: shell injection
            if _RE_SHELL_INJECT.search(line):
                issues.append(
                    Issue("VC304", "warning", "Shell injection risk (use subprocess.run with list args)", fi.path, lineno)
                )

            # VC305: unsafe deserialization
            if _RE_UNSAFE_DESER.search(line):
                # Allow yaml.load with SafeLoader
                if not ("yaml.load" in line and _RE_YAML_SAFE.search(line)):
                    issues.append(
                        Issue("VC305", "warning", "Unsafe deserialization", fi.path, lineno)
                    )

            # VC306: eval/exec
            if _RE_EVAL_EXEC.search(line):
                issues.append(
                    Issue("VC306", "warning", "Use of eval() or exec()", fi.path, lineno)
                )

            # VC308: debug mode
            if _RE_DEBUG.search(line):
                issues.append(
                    Issue("VC308", "warning", "DEBUG = True (possible production debug mode)", fi.path, lineno)
                )

    # Score
    score = 100.0
    for iss in issues:
        score -= _SEVERITY_DEDUCT.get(iss.severity, 0)
    score = max(0.0, min(100.0, score))

    return CategoryScore(
        name="Security",
        score=round(score, 1),
        grade=score_to_grade(score),
        issues=issues,
    )
