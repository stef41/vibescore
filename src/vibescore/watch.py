"""Watch mode — re-run vibescore when files change."""

from __future__ import annotations

import os
import time
from typing import Callable, Optional


def get_file_mtimes(
    path: str,
    extensions: tuple[str, ...] = (".py", ".js", ".ts", ".jsx", ".tsx"),
) -> dict[str, float]:
    """Get modification times for all matching files under path."""
    mtimes: dict[str, float] = {}
    for dirpath, dirnames, filenames in os.walk(path):
        # Skip hidden dirs and common non-source dirs
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")
        ]
        for fname in filenames:
            if any(fname.endswith(ext) for ext in extensions):
                fpath = os.path.join(dirpath, fname)
                try:
                    mtimes[fpath] = os.path.getmtime(fpath)
                except OSError:
                    continue
    return mtimes


def watch(
    path: str,
    callback: Callable[[str], None],
    interval: float = 1.0,
    extensions: tuple[str, ...] = (".py", ".js", ".ts", ".jsx", ".tsx"),
    max_iterations: Optional[int] = None,
) -> None:
    """Watch path for changes and call callback when files change.

    Args:
        path: Directory to watch.
        callback: Function called with the changed file path.
        interval: Polling interval in seconds.
        extensions: File extensions to watch.
        max_iterations: If set, stop after this many poll cycles (for testing).
    """
    prev_mtimes = get_file_mtimes(path, extensions)
    iterations = 0

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(interval)
        iterations += 1

        curr_mtimes = get_file_mtimes(path, extensions)

        # Check for new or modified files
        for fpath, mtime in curr_mtimes.items():
            if fpath not in prev_mtimes or prev_mtimes[fpath] != mtime:
                callback(fpath)

        prev_mtimes = curr_mtimes
