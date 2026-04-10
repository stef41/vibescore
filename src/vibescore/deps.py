from __future__ import annotations

import os
import re

from ._types import CategoryScore, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"critical": 10, "warning": 5, "info": 2}

# Matches lines like: requests, requests>=2.0, requests==2.28.1, etc.
_RE_REQ_LINE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9._-]*)\s*(.*)?$")
_RE_HAS_PIN = re.compile(r"[><=!~]")
_RE_WILDCARD = re.compile(r"==\s*\*|>=\s*0(?:\.\d+)*\s*$")


def _parse_requirements_txt(path: str) -> list[tuple[str, str]]:
    """Return list of (name, specifier) tuples from a requirements file."""
    deps: list[tuple[str, str]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                m = _RE_REQ_LINE.match(line)
                if m:
                    deps.append((m.group(1), (m.group(2) or "").strip()))
    except (OSError, ValueError):
        pass
    return deps


def _parse_pyproject_deps(path: str) -> list[tuple[str, str]]:
    """Rough regex parse of dependencies from pyproject.toml."""
    deps: list[tuple[str, str]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except (OSError, ValueError):
        return deps

    # Match dependencies = [ ... ] block
    m = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not m:
        return deps

    block = m.group(1)
    for item in re.findall(r'"([^"]+)"|\'([^\']+)\'', block):
        dep_str = item[0] or item[1]
        dep_str = dep_str.strip()
        if not dep_str:
            continue
        # Split name from specifier
        parts = re.split(r'([><=!~;])', dep_str, maxsplit=1)
        name = parts[0].strip()
        spec = dep_str[len(name):].strip()
        if name:
            deps.append((name, spec))

    return deps


def _parse_setup_cfg(path: str) -> list[tuple[str, str]]:
    """Rough parse of install_requires from setup.cfg."""
    deps: list[tuple[str, str]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except (OSError, ValueError):
        return deps

    m = re.search(r'install_requires\s*=\s*\n((?:\s+.+\n?)*)', content)
    if not m:
        return deps

    for line in m.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'([><=!~;])', line, maxsplit=1)
        name = parts[0].strip()
        spec = line[len(name):].strip()
        if name:
            deps.append((name, spec))

    return deps


def analyze_deps(root: str) -> CategoryScore:
    """Analyse project dependencies."""
    issues: list[Issue] = []

    has_pyproject = os.path.isfile(os.path.join(root, "pyproject.toml"))
    has_setup_py = os.path.isfile(os.path.join(root, "setup.py"))
    has_setup_cfg = os.path.isfile(os.path.join(root, "setup.cfg"))
    has_req_txt = os.path.isfile(os.path.join(root, "requirements.txt"))
    has_pipfile = os.path.isfile(os.path.join(root, "Pipfile"))
    has_package_json = os.path.isfile(os.path.join(root, "package.json"))

    has_any_dep_file = has_pyproject or has_setup_py or has_setup_cfg or has_req_txt or has_pipfile or has_package_json

    # Lock files
    lock_files = [
        "requirements.txt",
        "poetry.lock",
        "Pipfile.lock",
        "pdm.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    ]
    has_lock = any(os.path.isfile(os.path.join(root, lf)) for lf in lock_files)

    if not has_any_dep_file:
        issues.append(Issue("VC403", "warning", "No dependency file found"))
        return CategoryScore(
            name="Dependencies",
            score=50.0,
            grade=score_to_grade(50.0),
            issues=issues,
            details={"dependency_count": 0, "pinned_count": 0, "unpinned_count": 0, "has_lock_file": False},
        )

    # VC404: deprecated setup.py without pyproject.toml
    if has_setup_py and not has_pyproject:
        issues.append(Issue("VC404", "info", "Using setup.py without pyproject.toml (consider migrating)"))

    # Gather all deps
    all_deps: list[tuple[str, str]] = []
    if has_req_txt:
        all_deps.extend(_parse_requirements_txt(os.path.join(root, "requirements.txt")))
    if has_pyproject:
        all_deps.extend(_parse_pyproject_deps(os.path.join(root, "pyproject.toml")))
    if has_setup_cfg:
        all_deps.extend(_parse_setup_cfg(os.path.join(root, "setup.cfg")))

    pinned = 0
    unpinned = 0

    for name, spec in all_deps:
        if _RE_WILDCARD.search(spec):
            issues.append(Issue("VC405", "warning", f"Wildcard version pin: {name}{spec}"))
            unpinned += 1
        elif not _RE_HAS_PIN.search(spec):
            issues.append(Issue("VC401", "warning", f"Unpinned dependency: {name}"))
            unpinned += 1
        else:
            pinned += 1

    # VC402: no lock file
    if not has_lock and has_any_dep_file:
        issues.append(Issue("VC402", "info", "No lock file found (poetry.lock / Pipfile.lock / etc.)"))

    # Score
    score = 100.0
    for iss in issues:
        score -= _SEVERITY_DEDUCT.get(iss.severity, 0)
    score = max(0.0, min(100.0, score))

    return CategoryScore(
        name="Dependencies",
        score=round(score, 1),
        grade=score_to_grade(score),
        issues=issues,
        details={
            "dependency_count": len(all_deps),
            "pinned_count": pinned,
            "unpinned_count": unpinned,
            "has_lock_file": has_lock,
        },
    )
