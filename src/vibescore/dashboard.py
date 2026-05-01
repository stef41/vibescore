"""Web dashboard for vibescore — historical grade tracking.

Stores scan results over time and provides a simple web dashboard
to view grade history and trends.

Usage:
    vibescore --dashboard        # launch dashboard
    vibescore --save-history     # save current scan to history

Requires: ``pip install vibescore[web]``
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

_STREAMLIT_AVAILABLE = importlib.util.find_spec("streamlit") is not None

_HISTORY_FILE = ".vibescore-history.json"


@dataclass
class HistoryEntry:
    """A single scan result stored in history."""

    timestamp: float
    overall_score: float
    overall_grade: str
    categories: dict[str, float] = field(default_factory=dict)
    commit_hash: str = ""
    project_name: str = ""


def _history_path(project_root: str) -> str:
    return os.path.join(project_root, _HISTORY_FILE)


def load_history(project_root: str) -> list[HistoryEntry]:
    """Load scan history from the project's history file."""
    path = _history_path(project_root)
    if not os.path.isfile(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            HistoryEntry(
                timestamp=e.get("timestamp", 0),
                overall_score=e.get("overall_score", 0),
                overall_grade=e.get("overall_grade", "?"),
                categories=e.get("categories", {}),
                commit_hash=e.get("commit_hash", ""),
                project_name=e.get("project_name", ""),
            )
            for e in data
        ]
    except (json.JSONDecodeError, OSError):
        return []


def save_to_history(project_root: str, entry: HistoryEntry) -> None:
    """Append a scan result to the project's history file."""
    history = load_history(project_root)
    history.append(entry)

    # Keep last 100 entries
    if len(history) > 100:
        history = history[-100:]

    path = _history_path(project_root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([_entry_to_dict(e) for e in history], f, indent=2)


def _entry_to_dict(entry: HistoryEntry) -> dict:
    return {
        "timestamp": entry.timestamp,
        "overall_score": entry.overall_score,
        "overall_grade": entry.overall_grade,
        "categories": entry.categories,
        "commit_hash": entry.commit_hash,
        "project_name": entry.project_name,
    }


def create_history_entry(report: object) -> HistoryEntry:
    """Create a HistoryEntry from a VibeReport."""
    # Accept any object with the right attributes (avoids circular import)
    cats: dict[str, float] = {}
    for cat in getattr(report, "categories", []):
        cats[cat.name] = cat.score

    commit = ""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    return HistoryEntry(
        timestamp=time.time(),
        overall_score=getattr(report, "overall_score", 0),
        overall_grade=getattr(report, "overall_grade", "?"),
        categories=cats,
        commit_hash=commit,
        project_name=getattr(report, "project_name", ""),
    )


def format_history_report(history: list[HistoryEntry]) -> str:
    """Format history as a text table."""
    if not history:
        return "No scan history found."

    lines: list[str] = []
    lines.append("vibescore History")
    lines.append("=" * 70)
    lines.append(f"{'Date':20s}  {'Grade':6s}  {'Score':6s}  {'Commit':8s}  Categories")
    lines.append("-" * 70)

    for entry in history[-20:]:  # last 20
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.timestamp))
        cats = "  ".join(f"{k[:3]}={v:.0f}" for k, v in entry.categories.items())
        lines.append(
            f"{ts:20s}  {entry.overall_grade:6s}  {entry.overall_score:5.1f}  "
            f"{entry.commit_hash:8s}  {cats}"
        )

    return "\n".join(lines)


def check_streamlit() -> bool:
    """Check whether streamlit is importable."""
    return _STREAMLIT_AVAILABLE


def launch_dashboard(project_root: str) -> None:
    """Launch the Streamlit web dashboard for vibescore.

    Raises RuntimeError if streamlit is not installed.
    """
    if not _STREAMLIT_AVAILABLE:
        raise RuntimeError(
            "Streamlit is required for the dashboard. Install with: pip install vibescore[web]"
        )

    import streamlit as st

    from .scanner import scan

    st.set_page_config(page_title="vibescore dashboard", page_icon="🎵", layout="wide")
    st.title("🎵 vibescore Dashboard")

    # Load history
    history = load_history(project_root)

    if history:
        # Grade over time
        st.subheader("Grade History")
        dates = [time.strftime("%m/%d", time.localtime(e.timestamp)) for e in history]
        scores = [e.overall_score for e in history]
        st.line_chart(dict(zip(dates, scores)))

        # Category trends
        st.subheader("Category Trends")
        cat_names = list(history[-1].categories.keys()) if history else []
        for cat in cat_names:
            st.markdown(f"**{cat}**")
            cat_scores = [e.categories.get(cat, 0) for e in history]
            st.line_chart(dict(zip(dates, cat_scores)))

        # Latest report
        st.subheader("Latest Scan")
        latest = history[-1]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Grade", latest.overall_grade)
        with col2:
            st.metric("Score", f"{latest.overall_score:.1f}")
        with col3:
            st.metric("Commit", latest.commit_hash or "N/A")
    else:
        st.info("No scan history yet. Run `vibescore --save-history` to start tracking.")

    # Run new scan
    if st.button("🔍 Run New Scan"):
        with st.spinner("Scanning..."):
            report = scan(project_root)
            entry = create_history_entry(report)
            save_to_history(project_root, entry)
            st.success(f"Scan complete: {report.overall_grade} ({report.overall_score:.1f})")
            st.rerun()
