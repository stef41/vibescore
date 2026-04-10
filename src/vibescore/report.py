from __future__ import annotations

import json
from dataclasses import asdict

from ._types import VibeReport


def _fmt_num(n: int | float) -> str:
    """Format a number with comma separators."""
    if isinstance(n, float):
        return f"{n:,.1f}"
    return f"{n:,}"


def _severity_icon(severity: str) -> str:
    return {"critical": "\U0001f534", "warning": "\U0001f7e1", "info": "\U0001f4a1"}.get(severity, "")


def _pad(text: str, width: int) -> str:
    """Left-align *text* padded to *width* (Unicode-aware)."""
    return text + " " * max(0, width - len(text))


def _lang_summary(languages: dict[str, int]) -> str:
    parts: list[str] = []
    for lang, count in sorted(languages.items(), key=lambda kv: -kv[1]):
        if lang == "unknown":
            parts.append(f"{count} other")
        else:
            parts.append(f"{count} {lang.capitalize()}")
    return ", ".join(parts)


def format_report(report: VibeReport) -> str:
    """Generate a rich ASCII report."""
    lines: list[str] = []
    w = 46  # inner table width

    lines.append("")
    lines.append("\U0001f3b5 Vibe Check  v0.1.0")
    lines.append("\u2550" * w)
    lines.append("")
    lines.append(f"  Project:   {report.project_name}")
    lines.append(f"  Files:     {_fmt_num(report.total_files)} ({_lang_summary(report.languages)})")
    lines.append(f"  Lines:     {_fmt_num(report.total_lines)}")
    lines.append(f"  Scanned in {report.scan_time_s:.2f}s")
    lines.append("")

    # ── Table ──
    col_cat = 18
    col_score = 8
    col_grade = 7

    def hline(left: str, mid: str, right: str, fill: str = "\u2500") -> str:
        return left + fill * col_cat + mid + fill * col_score + mid + fill * col_grade + right

    lines.append(hline("\u250c", "\u252c", "\u2510", "\u2500"))
    lines.append(
        "\u2502"
        + _pad(" Category", col_cat)
        + "\u2502"
        + _pad(" Score", col_score)
        + "\u2502"
        + _pad(" Grade", col_grade)
        + "\u2502"
    )
    lines.append(hline("\u251c", "\u253c", "\u2524", "\u2500"))

    for cat in report.categories:
        lines.append(
            "\u2502"
            + _pad(f" {cat.name}", col_cat)
            + "\u2502"
            + _pad(f"  {cat.score:5.1f}", col_score)
            + "\u2502"
            + _pad(f" {cat.grade}", col_grade)
            + "\u2502"
        )

    lines.append(hline("\u251c", "\u253c", "\u2524", "\u2500"))
    lines.append(
        "\u2502"
        + _pad(" Overall", col_cat)
        + "\u2502"
        + _pad(f"  {report.overall_score:5.1f}", col_score)
        + "\u2502"
        + _pad(f" {report.overall_grade}", col_grade)
        + "\u2502"
    )
    lines.append(hline("\u2514", "\u2534", "\u2518", "\u2500"))
    lines.append("")

    # ── Issues ──
    all_issues = []
    for cat in report.categories:
        all_issues.extend(cat.issues)

    criticals = [i for i in all_issues if i.severity == "critical"]
    warnings = [i for i in all_issues if i.severity == "warning"]
    infos = [i for i in all_issues if i.severity == "info"]

    def _issue_line(iss) -> str:  # noqa: ANN001
        loc = ""
        if iss.file:
            loc = f"  {iss.file}"
            if iss.line:
                loc += f":{iss.line}"
        return f"  {iss.code}  {iss.message}{loc}"

    if criticals:
        lines.append(f"\U0001f534 Critical Issues ({len(criticals)})")
        for iss in criticals:
            lines.append(_issue_line(iss))
        lines.append("")

    if warnings:
        lines.append(f"\U0001f7e1 Warnings ({len(warnings)})")
        for iss in warnings[:20]:
            lines.append(_issue_line(iss))
        if len(warnings) > 20:
            lines.append(f"  ... and {len(warnings) - 20} more")
        lines.append("")

    if infos:
        lines.append(f"\U0001f4a1 Info ({len(infos)})")
        for iss in infos[:10]:
            lines.append(_issue_line(iss))
        if len(infos) > 10:
            lines.append(f"  ... and {len(infos) - 10} more")
        lines.append("")

    # ── Tips ──
    tips: list[str] = []
    for cat in report.categories:
        if cat.name == "Testing" and cat.score < 80:
            tips.append("Add tests to improve your Testing grade")
        if cat.name == "Dependencies" and cat.score < 90:
            tips.append("Pin your dependency versions")
        if cat.name == "Security" and cat.score < 90:
            tips.append("Remove hardcoded secrets and use environment variables")
        if cat.name == "Code Quality" and cat.score < 80:
            tips.append("Reduce function complexity and add type annotations")

    if tips:
        lines.append("\U0001f4a1 Tips")
        for tip in tips:
            lines.append(f"  \u2022 {tip}")
        lines.append("")

    return "\n".join(lines)


def format_json(report: VibeReport) -> str:
    """Return the report as a JSON string."""
    return json.dumps(asdict(report), indent=2, default=str)


def _grade_color(grade: str) -> str:
    """Return a rich color name for a letter grade."""
    if grade.startswith("A"):
        return "green"
    if grade.startswith("B") or grade.startswith("C"):
        return "yellow"
    return "red"


def _severity_style(severity: str) -> str:
    """Return a rich style for issue severity."""
    return {"critical": "bold red", "warning": "yellow", "info": "blue"}.get(severity, "")


def format_report_rich(report: VibeReport) -> str:
    """Generate a colored report using the *rich* library.

    Raises :class:`ImportError` if ``rich`` is not installed so that
    callers can fall back to :func:`format_report`.
    """
    from io import StringIO

    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=60)

    # ── Header panel ──
    header_lines = (
        f"Project:   {report.project_name}\n"
        f"Files:     {_fmt_num(report.total_files)} ({_lang_summary(report.languages)})\n"
        f"Lines:     {_fmt_num(report.total_lines)}\n"
        f"Scanned in {report.scan_time_s:.2f}s"
    )
    console.print(Panel(header_lines, title="\U0001f3b5 Vibe Check  v0.1.0", expand=False))

    # ── Grade table ──
    table = Table(show_header=True, header_style="bold")
    table.add_column("Category", min_width=16)
    table.add_column("Score", justify="right", min_width=6)
    table.add_column("Grade", justify="center", min_width=5)

    for cat in report.categories:
        color = _grade_color(cat.grade)
        table.add_row(cat.name, f"{cat.score:.1f}", Text(cat.grade, style=color))

    table.add_section()
    overall_color = _grade_color(report.overall_grade)
    table.add_row(
        Text("Overall", style="bold"),
        Text(f"{report.overall_score:.1f}", style="bold"),
        Text(report.overall_grade, style=f"bold {overall_color}"),
    )
    console.print(table)

    # ── Issues ──
    all_issues = []
    for cat in report.categories:
        all_issues.extend(cat.issues)

    for sev, label, limit in [
        ("critical", "\U0001f534 Critical Issues", None),
        ("warning", "\U0001f7e1 Warnings", 20),
        ("info", "\U0001f4a1 Info", 10),
    ]:
        issues = [i for i in all_issues if i.severity == sev]
        if not issues:
            continue
        console.print()
        console.print(f"[{_severity_style(sev)}]{label} ({len(issues)})[/]")
        show = issues if limit is None else issues[:limit]
        for iss in show:
            loc = ""
            if iss.file:
                loc = f"  {iss.file}"
                if iss.line:
                    loc += f":{iss.line}"
            console.print(f"  [{_severity_style(sev)}]{iss.code}[/]  {iss.message}{loc}")
        if limit and len(issues) > limit:
            console.print(f"  ... and {len(issues) - limit} more")

    console.print()
    return buf.getvalue()
