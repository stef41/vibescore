from __future__ import annotations

import os
import re

from ._types import CategoryScore, FileInfo, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"warning": 3, "info": 1}

# Patterns for function declarations
_RE_FUNCTION_DECL = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+\w+\s*\(", re.MULTILINE
)
_RE_CONST_ARROW = re.compile(
    r"(?:export\s+)?const\s+\w+\s*=\s*(?:async\s+)?\(", re.MULTILINE
)
_RE_METHOD = re.compile(
    r"^\s+(?:async\s+)?\w+\s*\([^)]*\)\s*\{", re.MULTILINE
)

_RE_CONSOLE_LOG = re.compile(r"\bconsole\.\w+\s*\(")
_RE_EXPORT_FUNC = re.compile(
    r"^export\s+(?:async\s+)?function\s+\w+", re.MULTILINE
)
_RE_EXPORT_CONST = re.compile(
    r"^export\s+const\s+\w+\s*=", re.MULTILINE
)
_RE_JSDOC = re.compile(r"/\*\*")
_RE_VAR = re.compile(r"\bvar\s+\w+")
_RE_LOOSE_EQ = re.compile(r"(?<!=)(?<!\!)={2}(?!=)")
_RE_ANY_TYPE = re.compile(r":\s*any\b")


def _read_source(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


def _is_test_file(path: str) -> bool:
    base = os.path.basename(path).lower()
    parts = path.replace("\\", "/").lower().split("/")
    if any(p in ("test", "tests", "__tests__", "spec", "specs") for p in parts):
        return True
    if base.endswith((".test.js", ".test.ts", ".test.jsx", ".test.tsx",
                      ".spec.js", ".spec.ts", ".spec.jsx", ".spec.tsx")):
        return True
    return False


def _count_nesting_depth(line: str) -> int:
    """Estimate nesting depth from leading indentation."""
    stripped = line.expandtabs(4)
    spaces = len(stripped) - len(stripped.lstrip())
    # Heuristic: 2 or 4 spaces per level; pick based on first indent
    indent_size = 2
    return spaces // indent_size


def _find_matching_brace(lines: list[str], start: int) -> int:
    """Find the line index of the closing brace that matches the opening brace
    on or after *start*. Returns *start* if no opening brace is found."""
    depth = 0
    found_open = False
    for i in range(start, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                found_open = True
            elif ch == "}":
                depth -= 1
                if found_open and depth == 0:
                    return i
    return start


def _detect_functions(src: str) -> list[tuple[str, int, int]]:
    """Return (name, start_line_0idx, end_line_0idx) for detected functions."""
    lines = src.splitlines()
    funcs: list[tuple[str, int, int]] = []

    for i, line in enumerate(lines):
        m = re.match(r".*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", line)
        if not m:
            m = re.match(r".*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", line)
        if not m:
            m = re.match(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", line)
        if m:
            name = m.group(1)
            end = _find_matching_brace(lines, i)
            funcs.append((name, i, end))

    return funcs


def _check_callback_hell(lines: list[str], start: int, end: int) -> int:
    """Count the max depth of nested inline callbacks inside a function body."""
    max_depth = 0
    depth = 0
    for i in range(start, min(end + 1, len(lines))):
        line = lines[i]
        # Detect inline callback: function(, => {, etc.
        callbacks = len(re.findall(r"(?:function\s*\(|=>\s*\{)", line))
        depth += callbacks
        max_depth = max(max_depth, depth)
        # Closing braces reduce depth
        closes = line.count("}")
        depth = max(0, depth - closes)
    return max_depth


def analyze_quality_js(files: list[FileInfo], root: str) -> CategoryScore:
    """Analyse JavaScript/TypeScript code quality and return a scored category."""
    issues: list[Issue] = []

    for fi in files:
        if fi.language not in ("javascript", "typescript"):
            continue

        full_path = os.path.join(root, fi.path)
        src = _read_source(full_path)
        if src is None:
            continue

        lines = src.splitlines()
        is_test = _is_test_file(fi.path)

        # ── VC211: Function too long (>50 lines) ────────────────────
        funcs = _detect_functions(src)
        for name, start, end in funcs:
            length = end - start + 1
            if length > 50:
                issues.append(
                    Issue("VC211", "warning",
                          f"Function '{name}' too long ({length} lines)",
                          fi.path, start + 1)
                )

        # ── VC212: Deep nesting (>4 levels) ─────────────────────────
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            depth = _count_nesting_depth(line)
            if depth > 4:
                issues.append(
                    Issue("VC212", "warning",
                          f"Deep nesting (depth {depth})",
                          fi.path, i + 1)
                )

        # ── VC213: console.log left in code (not in test files) ─────
        if not is_test:
            for i, line in enumerate(lines):
                if _RE_CONSOLE_LOG.search(line):
                    issues.append(
                        Issue("VC213", "info",
                              "console.log left in code",
                              fi.path, i + 1)
                    )

        # ── VC214: No JSDoc on exported function ────────────────────
        for i, line in enumerate(lines):
            if _RE_EXPORT_FUNC.match(line) or _RE_EXPORT_CONST.match(line):
                # Check if preceded by a JSDoc comment
                has_jsdoc = False
                for j in range(i - 1, -1, -1):
                    prev = lines[j].strip()
                    if prev.endswith("*/"):
                        # Walk up to find /**
                        for k in range(j, -1, -1):
                            if _RE_JSDOC.search(lines[k]):
                                has_jsdoc = True
                                break
                        break
                    if prev == "" or prev.startswith("*") or prev.startswith("//"):
                        continue
                    break
                if not has_jsdoc:
                    issues.append(
                        Issue("VC214", "info",
                              "Exported function missing JSDoc comment",
                              fi.path, i + 1)
                    )

        # ── VC215: Use of `var` ─────────────────────────────────────
        for i, line in enumerate(lines):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if _RE_VAR.search(line):
                issues.append(
                    Issue("VC215", "warning",
                          "Use of 'var' instead of 'let'/'const'",
                          fi.path, i + 1)
                )

        # ── VC216: Loose equality (== instead of ===) ───────────────
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if _RE_LOOSE_EQ.search(line):
                issues.append(
                    Issue("VC216", "warning",
                          "Use of '==' instead of '===' (loose equality)",
                          fi.path, i + 1)
                )

        # ── VC217: `any` type annotation in TypeScript ──────────────
        if fi.language == "typescript":
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                if _RE_ANY_TYPE.search(line):
                    issues.append(
                        Issue("VC217", "info",
                              "'any' type annotation in TypeScript",
                              fi.path, i + 1)
                    )

        # ── VC218: Callback hell (>3 levels of nested callbacks) ────
        for name, start, end in funcs:
            depth = _check_callback_hell(lines, start, end)
            if depth > 3:
                issues.append(
                    Issue("VC218", "warning",
                          f"Callback hell in '{name}' ({depth} nested callbacks)",
                          fi.path, start + 1)
                )

    # Compute score
    score = 100.0
    warns = [i for i in issues if i.severity == "warning"]
    infos = [i for i in issues if i.severity == "info"]
    for _ in warns:
        score -= _SEVERITY_DEDUCT["warning"]
    info_deduction = min(15.0, len(infos) * _SEVERITY_DEDUCT["info"])
    score -= info_deduction
    score = max(0.0, min(100.0, score))

    return CategoryScore(
        name="Code Quality",
        score=round(score, 1),
        grade=score_to_grade(score),
        issues=issues,
    )
