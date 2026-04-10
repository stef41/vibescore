from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileInfo:
    path: str
    language: str  # "python", "javascript", "typescript", "unknown"
    lines: int
    size_bytes: int


@dataclass
class Issue:
    code: str  # e.g. "VC101"
    severity: str  # "critical", "warning", "info"
    message: str
    file: str | None = None
    line: int | None = None


@dataclass
class CategoryScore:
    name: str
    score: float  # 0-100
    grade: str  # A+ through F
    issues: list[Issue] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class VibeReport:
    project_path: str
    project_name: str
    total_files: int
    total_lines: int
    languages: dict[str, int]  # language -> file count
    categories: list[CategoryScore] = field(default_factory=list)
    overall_score: float = 0.0
    overall_grade: str = "?"
    scan_time_s: float = 0.0
