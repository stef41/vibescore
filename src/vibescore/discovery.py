from __future__ import annotations

import os
from pathlib import Path

from ._types import FileInfo

_SKIP_DIRS: set[str] = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    ".eggs",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

_EXT_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".rs": "rust",
    ".go": "go",
}


def _should_skip_dir(name: str) -> bool:
    if name in _SKIP_DIRS:
        return True
    if name.startswith("."):
        return True
    if name.endswith(".egg-info"):
        return True
    return False


def _count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except (OSError, ValueError):
        return 0


def _file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def discover_files(root: str, max_files: int = 5000) -> list[FileInfo]:
    """Walk *root* and return info for every source file found."""
    results: list[FileInfo] = []
    root_path = os.path.abspath(root)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune skipped directories in-place
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]

        for fname in filenames:
            if len(results) >= max_files:
                return results

            full = os.path.join(dirpath, fname)
            ext = os.path.splitext(fname)[1].lower()
            language = _EXT_LANGUAGE.get(ext, "unknown")
            lines = _count_lines(full) if language != "unknown" else 0
            size = _file_size(full)

            rel = os.path.relpath(full, root_path)
            results.append(FileInfo(path=rel, language=language, lines=lines, size_bytes=size))

    return results


def detect_project_type(root: str) -> str:
    """Return 'python', 'node', 'mixed', or 'unknown'."""
    root_path = Path(root)
    has_python = any(
        (root_path / f).exists()
        for f in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile")
    )
    has_node = any(
        (root_path / f).exists()
        for f in ("package.json", "package-lock.json", "yarn.lock")
    )

    if has_python and has_node:
        return "mixed"
    if has_python:
        return "python"
    if has_node:
        return "node"
    return "unknown"
