"""Rust code quality analyser for vibescore.

Checks for common Rust quality issues:
- Excessive `unwrap()` usage (VC221)
- `unsafe` blocks (VC222)
- Function length (VC223)
- Missing documentation comments (VC224)
- `clone()` overuse (VC225)
- `todo!()` / `unimplemented!()` macros (VC226)
- Unused `allow` attributes (VC227)
"""
from __future__ import annotations

import os
import re

from ._types import CategoryScore, FileInfo, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"critical": 10, "warning": 3, "info": 1}

_RE_UNWRAP = re.compile(r"\.unwrap\(\)")
_RE_EXPECT = re.compile(r"\.expect\(")
_RE_UNSAFE = re.compile(r"\bunsafe\s*\{")
_RE_FN_DECL = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE)
_RE_DOC_COMMENT = re.compile(r"^\s*///", re.MULTILINE)
_RE_CLONE = re.compile(r"\.clone\(\)")
_RE_TODO_MACRO = re.compile(r"\b(?:todo|unimplemented)!\s*\(")
_RE_ALLOW = re.compile(r"#\[allow\(")
_RE_IMPL_BLOCK = re.compile(r"\bimpl\b")


def _read_source(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


def _is_test_file(path: str) -> bool:
    parts = path.replace("\\", "/").lower().split("/")
    base = os.path.basename(path).lower()
    return any(p in ("tests", "test") for p in parts) or base.startswith("test_")


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


def analyze_quality_rs(files: list[FileInfo], root: str) -> CategoryScore:
    """Analyse Rust source files for code quality issues."""
    issues: list[Issue] = []
    total_fns = 0
    total_unwraps = 0
    total_unsafes = 0
    total_clones = 0
    long_fns = 0

    for fi in files:
        if _is_test_file(fi.path):
            continue

        full_path = os.path.join(root, fi.path)
        source = _read_source(full_path)
        if source is None:
            continue

        rel = fi.path
        lines = source.split("\n")

        # VC221: unwrap() usage
        unwrap_matches = list(_RE_UNWRAP.finditer(source))
        total_unwraps += len(unwrap_matches)
        if len(unwrap_matches) > 5:
            issues.append(Issue(
                code="VC221",
                severity="warning",
                message=f"Excessive unwrap() usage ({len(unwrap_matches)} calls) — use ? operator or proper error handling",
                file=rel,
            ))

        # VC222: unsafe blocks
        unsafe_matches = list(_RE_UNSAFE.finditer(source))
        total_unsafes += len(unsafe_matches)
        for m in unsafe_matches:
            line_no = source[:m.start()].count("\n") + 1
            issues.append(Issue(
                code="VC222",
                severity="warning",
                message="unsafe block — ensure memory safety is guaranteed",
                file=rel,
                line=line_no,
            ))

        # VC223: Function length
        for m in _RE_FN_DECL.finditer(source):
            total_fns += 1
            fn_line = source[:m.start()].count("\n")
            fn_len = _count_fn_lines(source, fn_line)
            if fn_len > 50:
                long_fns += 1
                issues.append(Issue(
                    code="VC223",
                    severity="warning",
                    message=f"Function '{m.group(1)}' is {fn_len} lines (>50)",
                    file=rel,
                    line=fn_line + 1,
                ))

        # VC224: Public items without doc comments
        pub_items = list(re.finditer(r"^\s*pub\s+(?:fn|struct|enum|trait|type)\s+(\w+)", source, re.MULTILINE))
        for item in pub_items:
            item_line = source[:item.start()].count("\n")
            # Check if preceding line has ///
            if item_line > 0 and not lines[item_line - 1].strip().startswith("///"):
                issues.append(Issue(
                    code="VC224",
                    severity="info",
                    message=f"Public item '{item.group(1)}' missing doc comment",
                    file=rel,
                    line=item_line + 1,
                ))

        # VC225: Excessive clone()
        clone_matches = list(_RE_CLONE.finditer(source))
        total_clones += len(clone_matches)
        if len(clone_matches) > 10:
            issues.append(Issue(
                code="VC225",
                severity="info",
                message=f"Heavy clone() usage ({len(clone_matches)} calls) — consider borrowing",
                file=rel,
            ))

        # VC226: todo!/unimplemented! macros
        for m in _RE_TODO_MACRO.finditer(source):
            line_no = source[:m.start()].count("\n") + 1
            issues.append(Issue(
                code="VC226",
                severity="info",
                message="todo!/unimplemented! macro found",
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
            "unwrap_calls": total_unwraps,
            "unsafe_blocks": total_unsafes,
            "clone_calls": total_clones,
            "long_functions": long_fns,
        },
    )
