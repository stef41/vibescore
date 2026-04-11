"""Tests for dashboard module."""
from __future__ import annotations

import os
import tempfile
import time
from dataclasses import dataclass, field

from vibescore.dashboard import (
    HistoryEntry,
    create_history_entry,
    format_history_report,
    load_history,
    save_to_history,
)


@dataclass
class _FakeReport:
    """Mimics VibeReport for testing create_history_entry."""

    project_name: str = "testproj"
    overall_score: float = 92.5
    overall_grade: str = "A"
    categories: list = field(default_factory=list)


class TestHistoryEntry:
    def test_create_entry(self) -> None:
        report = _FakeReport(overall_grade="A", overall_score=92.5)
        entry = create_history_entry(report)
        assert isinstance(entry, HistoryEntry)
        assert entry.overall_grade == "A"
        assert entry.overall_score == 92.5
        assert entry.timestamp > 0

    def test_entry_has_timestamp(self) -> None:
        report = _FakeReport()
        entry = create_history_entry(report)
        assert entry.timestamp > 0


class TestLoadSave:
    def test_load_empty(self) -> None:
        tmpdir = tempfile.mkdtemp()
        result = load_history(tmpdir)
        assert result == []

    def test_save_and_load(self) -> None:
        tmpdir = tempfile.mkdtemp()
        entry = HistoryEntry(
            timestamp=time.time(),
            overall_score=90.0,
            overall_grade="A-",
        )
        save_to_history(tmpdir, entry)
        loaded = load_history(tmpdir)
        assert len(loaded) == 1
        assert loaded[0].overall_grade == "A-"
        assert loaded[0].overall_score == 90.0

    def test_save_multiple(self) -> None:
        tmpdir = tempfile.mkdtemp()
        for i, grade in enumerate(["A", "B", "C"]):
            entry = HistoryEntry(
                timestamp=time.time() + i,
                overall_score=90.0 - i * 10,
                overall_grade=grade,
            )
            save_to_history(tmpdir, entry)
        loaded = load_history(tmpdir)
        assert len(loaded) == 3


class TestFormatReport:
    def test_empty_history(self) -> None:
        report = format_history_report([])
        assert "No" in report or "empty" in report.lower() or report.strip() == ""

    def test_format_entries(self) -> None:
        entries = [
            HistoryEntry(timestamp=time.time(), overall_score=95.0, overall_grade="A"),
            HistoryEntry(timestamp=time.time(), overall_score=70.0, overall_grade="C"),
        ]
        report = format_history_report(entries)
        assert "A" in report
        assert "95" in report
        assert "C" in report
