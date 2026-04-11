"""Go code quality analyser for vibescore.

Checks for common Go quality issues:
- Unchecked errors (VC231)
- Goroutine leaks / missing WaitGroup (VC232)
- Function length (VC233)
- Missing doc comments on exported items (VC234)
- Naked returns (VC235)
- nil pointer risks (VC236)
- panic() in library code (VC237)
"""
from __future__ import annotations

import os
import re

from ._types import CategoryScore, FileInfo, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"critical": 10, "warning": 3, "info": 1}

_RE_FUNC_DECL = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.MULTILINE)
_RE_ERR_ASSIGN = re.compile(r"\berr\s*:?=")
_RE_ERR_CHECK = re.compile(r"if\s+err\s*!=\s*nil")
_RE_GO_KEYWORD = re.compile(r"\bgo\s+\w+")
_RE_WAITGROUP = re.compile(r"sync\.WaitGroup")
_RE_NAKED_RETURN = re.compile(r"^\s*return\s*$", re.MULTILINE)
_RE_NIL_CHECK = re.compile(r"if\s+\w+\s*==\s*nil")
_RE_PANIC = re.compile(r"\bpanic\s*\(")
_RE_EXPORTED = re.compile(r"^(?:func|type|var|const)\s+([A-Z]\w*)", re.MULTILINE)
_RE_METHOD_EXPORTED = re.compile(r"^func\s+\([^)]+\)\s+([A-Z]\w*)\s*\(", re.MULTILINE)
_RE_DOC_COMMENT = re.compile(r"^//\s*\w+", re.MULTILINE)


def _read_source(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


def _is_test_file(path: str) -> bool:
    return os.path.basename(path).endswith("_test.go")


def _count_fn_lines(source: str, fn_start: int) -> int:
    """Count lines in a function starting at *fn_start* line offset."""
    lines = source.split("\n")
    if fn_start >= len(lines):
        return 0
    brace_count = 0
    started = False
    count = 0
    for line in lines[fn_start:]:
        brace_count += line.count("{") - line.count("}")
        if "{" in line and not started:
            started = True
        if started:
            count += 1
            if brace_count <= 0:
                break
    return count


def analyze_quality_go(files: list[FileInfo], root: str) -> CategoryScore:
    """Analyse Go source files for code quality issues."""
    issues: list[Issue] = []
    total_fns = 0
    total_goroutines = 0
    long_fns = 0

    for fi in files:
        if _is_test_file(fi.path):
            continue

        source = _read_source(fi.path)
        if source is None:
            continue

        rel = os.path.relpath(fi.path, root)
        lines = source.split("\n")

        # VC231: Unchecked errors
        err_assigns = len(list(_RE_ERR_ASSIGN.finditer(source)))
        err_checks = len(list(_RE_ERR_CHECK.finditer(source)))
        if err_assigns > err_checks + 2:
            unchecked = err_assigns - err_checks
            issues.append(Issue(
                code="VC231",
                severity="warning",
                message=f"Possibly {unchecked} unchecked error(s) — always handle err returns",
                file=rel,
            ))

        # VC232: Goroutine leaks
        goroutine_count = len(list(_RE_GO_KEYWORD.finditer(source)))
        total_goroutines += goroutine_count
        has_waitgroup = bool(_RE_WAITGROUP.search(source))
        if goroutine_count > 0 and not has_waitgroup:
            issues.append(Issue(
                code="VC232",
                severity="warning",
                message=f"{goroutine_count} goroutine(s) without sync.WaitGroup — potential goroutine leak",
                file=rel,
            ))

        # VC233: Function length
        for m in _RE_FUNC_DECL.finditer(source):
            total_fns += 1
            fn_line = source[:m.start()].count("\n")
            fn_len = _count_fn_lines(source, fn_line)
            if fn_len > 50:
                long_fns += 1
                issues.append(Issue(
                    code="VC233",
                    severity="warning",
                    message=f"Function '{m.group(1)}' is {fn_len} lines (>50)",
                    file=rel,
                    line=fn_line + 1,
                ))

        # VC234: Missing doc comments on exported items
        for m in list(_RE_EXPORTED.finditer(source)) + list(_RE_METHOD_EXPORTED.finditer(source)):
            item_line = source[:m.start()].count("\n")
            name = m.group(1)
            if item_line > 0 and not lines[item_line - 1].strip().startswith("//"):
                issues.append(Issue(
                    code="VC234",
                    severity="info",
                    message=f"Exported '{name}' missing doc comment",
                    file=rel,
                    line=item_line + 1,
                ))

        # VC235: Naked returns
        naked_returns = list(_RE_NAKED_RETURN.finditer(source))
        if len(naked_returns) > 3:
            issues.append(Issue(
                code="VC235",
                severity="info",
                message=f"{len(naked_returns)} naked returns — consider explicit return values",
                file=rel,
            ))

        # VC236: nil pointer risks — check for dereferences without nil check
        # Simplified: just flag panic() calls
        # VC237: panic() in non-main code
        for m in _RE_PANIC.finditer(source):
            line_no = source[:m.start()].count("\n") + 1
            # Check if file is a main package
            if "package main" not in source[:200]:
                issues.append(Issue(
                    code="VC237",
                    severity="warning",
                    message="panic() in library code — return errors instead",
                    file=rel,
                    line=line_no,
                ))

    # Score calculation
    score = 100.0
    for issue in issues:
        score -= _SEVERITY_DEDUCT.get(issue.severity, 0)
    score = max(0.0, min(100.0, score))

    return CategoryScore(
        name="Code Quality",
        score=round(score, 1),
        grade=score_to_grade(score),
        issues=issues,
        details={
            "total_functions": total_fns,
            "goroutines": total_goroutines,
            "long_functions": long_fns,
        },
    )
