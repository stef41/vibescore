from __future__ import annotations

__version__ = "0.1.0"

from .scanner import scan
from ._types import VibeReport, CategoryScore, Issue, FileInfo
from .scoring import score_to_grade, compute_overall

__all__ = [
    "scan",
    "VibeReport",
    "CategoryScore",
    "Issue",
    "FileInfo",
    "score_to_grade",
    "compute_overall",
    "__version__",
]
