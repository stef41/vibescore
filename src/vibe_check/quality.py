from __future__ import annotations

import ast
import os

from ._types import CategoryScore, FileInfo, Issue
from .scoring import score_to_grade

_SEVERITY_DEDUCT = {"critical": 10, "warning": 3, "info": 1}


# ── helpers ──────────────────────────────────────────────────────────────

def _read_source(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


def _cyclomatic_complexity(node: ast.AST) -> int:
    """Count branches inside a function/method body."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # each additional boolean operator adds a path
            complexity += len(child.values) - 1
    return complexity


def _max_nesting(node: ast.AST) -> int:
    """Return the maximum nesting depth inside *node*."""

    def _walk(n: ast.AST, depth: int) -> int:
        best = depth
        for child in ast.iter_child_nodes(n):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)):
                best = max(best, _walk(child, depth + 1))
            else:
                best = max(best, _walk(child, depth))
        return best

    return _walk(node, 0)


def _func_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    if not node.body:
        return 0
    first = node.body[0].lineno
    last = node.end_lineno or node.body[-1].lineno
    return last - first + 1


def _has_mutable_default(node: ast.expr) -> bool:
    return isinstance(node, (ast.List, ast.Dict, ast.Set, ast.Call))


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _has_docstring(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if not func.body:
        return False
    first = func.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        return True
    return False


# ── analyser ─────────────────────────────────────────────────────────────

def analyze_quality(files: list[FileInfo], root: str) -> CategoryScore:
    """Analyse Python code quality and return a scored category."""
    issues: list[Issue] = []

    for fi in files:
        if fi.language != "python":
            continue

        full_path = os.path.join(root, fi.path)
        src = _read_source(full_path)
        if src is None:
            continue

        # VC206: file too long
        if fi.lines > 500:
            issues.append(Issue("VC206", "info", f"File too long ({fi.lines} lines)", fi.path))

        try:
            tree = ast.parse(src, filename=fi.path)
        except SyntaxError:
            continue

        # VC207: star imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.names:
                for alias in node.names:
                    if alias.name == "*":
                        issues.append(
                            Issue("VC207", "warning", f"Star import: from {node.module} import *", fi.path, node.lineno)
                        )

        # Walk functions
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            fname = node.name
            lineno = node.lineno

            # VC201: function too long
            length = _func_line_count(node)
            if length > 50:
                issues.append(
                    Issue("VC201", "warning", f"Function '{fname}' too long ({length} lines)", fi.path, lineno)
                )

            # VC202: high cyclomatic complexity
            cc = _cyclomatic_complexity(node)
            if cc > 10:
                issues.append(
                    Issue("VC202", "warning", f"Function '{fname}' high complexity ({cc})", fi.path, lineno)
                )

            # VC203: too many parameters
            args = node.args
            n_params = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
            # Exclude 'self'/'cls'
            if args.args and args.args[0].arg in ("self", "cls"):
                n_params -= 1
            if n_params > 5:
                issues.append(
                    Issue("VC203", "warning", f"Function '{fname}' has {n_params} parameters (>5)", fi.path, lineno)
                )

            # VC204: missing type annotations
            missing_ann = node.returns is None
            for arg in args.args + args.posonlyargs + args.kwonlyargs:
                if arg.arg in ("self", "cls"):
                    continue
                if arg.annotation is None:
                    missing_ann = True
                    break
            if missing_ann:
                issues.append(
                    Issue("VC204", "info", f"Function '{fname}' missing type annotations", fi.path, lineno)
                )

            # VC205: deep nesting
            depth = _max_nesting(node)
            if depth > 4:
                issues.append(
                    Issue("VC205", "warning", f"Function '{fname}' has deep nesting (depth {depth})", fi.path, lineno)
                )

            # VC208: no docstring on public function
            if _is_public(fname) and not _has_docstring(node):
                issues.append(
                    Issue("VC208", "info", f"Public function '{fname}' missing docstring", fi.path, lineno)
                )

            # VC209: mutable default argument
            for default in args.defaults + args.kw_defaults:
                if default is not None and _has_mutable_default(default):
                    issues.append(
                        Issue("VC209", "warning", f"Function '{fname}' uses mutable default argument", fi.path, lineno)
                    )
                    break

    # Compute score — deduct for critical/warning issues, cap info deductions
    score = 100.0
    critical_warns = [i for i in issues if i.severity in ("critical", "warning")]
    infos = [i for i in issues if i.severity == "info"]
    for iss in critical_warns:
        score -= _SEVERITY_DEDUCT.get(iss.severity, 0)
    # Info deductions capped at 15 points total
    if infos and files:
        total_funcs = max(sum(1 for _ in infos), 1)
        info_penalty = min(15.0, len(infos) * 15.0 / max(total_funcs, 1))
        score -= info_penalty
    score = max(0.0, min(100.0, score))

    return CategoryScore(
        name="Code Quality",
        score=round(score, 1),
        grade=score_to_grade(score),
        issues=issues,
    )
