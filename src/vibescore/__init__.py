from __future__ import annotations

__version__ = "0.4.0"

from .scanner import scan
from ._types import VibeReport, CategoryScore, Issue, FileInfo
from .scoring import score_to_grade, compute_overall
from .actions import generate_workflow
from .watch import watch, get_file_mtimes
from .dashboard import load_history, save_to_history, create_history_entry, HistoryEntry

__all__ = [
    "scan",
    "VibeReport",
    "CategoryScore",
    "Issue",
    "FileInfo",
    "score_to_grade",
    "compute_overall",
    "generate_workflow",
    "watch",
    "get_file_mtimes",
    "load_history",
    "save_to_history",
    "create_history_entry",
    "HistoryEntry",
    "__version__",
]
