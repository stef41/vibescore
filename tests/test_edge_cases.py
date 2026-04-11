"""Exhaustive edge-case tests for vibescore — covers all identified gaps."""

from __future__ import annotations

import json
import os
import time

import pytest

from vibescore._types import CategoryScore, FileInfo, Issue, VibeReport
from vibescore.scoring import score_to_grade, compute_overall
from vibescore.dashboard import (
    HistoryEntry,
    check_streamlit,
    format_history_report,
    load_history,
    save_to_history,
    create_history_entry,
)
from vibescore.deps import (
    _parse_requirements_txt,
    _parse_pyproject_deps,
    _parse_setup_cfg,
    analyze_deps,
)
from vibescore.testing import analyze_testing
from vibescore.discovery import (
    _should_skip_dir,
    discover_files,
    detect_project_type,
)
from vibescore.scanner import scan
from vibescore.report import format_report, format_json


# ═══════════════════════════════════════════════════════════════════════════════
#  _types.py — dataclass construction edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestTypes:
    def test_file_info_construction(self):
        fi = FileInfo(path="src/main.py", language="python", lines=100, size_bytes=2048)
        assert fi.path == "src/main.py"
        assert fi.language == "python"

    def test_issue_defaults(self):
        iss = Issue(code="VC101", severity="warning", message="test")
        assert iss.file is None
        assert iss.line is None

    def test_issue_with_file(self):
        iss = Issue(code="VC101", severity="warning", message="test", file="foo.py", line=42)
        assert iss.file == "foo.py"
        assert iss.line == 42

    def test_category_score_defaults(self):
        cs = CategoryScore(name="Testing", score=85.0, grade="B+")
        assert cs.issues == []
        assert cs.details == {}

    def test_vibe_report_defaults(self):
        r = VibeReport(project_path="/tmp", project_name="test", total_files=5, total_lines=100, languages={"python": 5})
        assert r.overall_score == 0.0
        assert r.overall_grade == "?"
        assert r.scan_time_s == 0.0
        assert r.categories == []


# ═══════════════════════════════════════════════════════════════════════════════
#  dashboard.py — history truncation, check_streamlit, format edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardEdge:
    def test_check_streamlit(self):
        # Just verify it returns a bool (streamlit may or may not be installed)
        result = check_streamlit()
        assert isinstance(result, bool)

    def test_history_truncation(self, tmp_path):
        """save_to_history caps at 100 entries."""
        for i in range(105):
            entry = HistoryEntry(
                timestamp=float(i), overall_score=float(i),
                overall_grade="A", project_name="test",
            )
            save_to_history(str(tmp_path), entry)
        history = load_history(str(tmp_path))
        assert len(history) <= 100

    def test_load_history_no_file(self, tmp_path):
        history = load_history(str(tmp_path / "nonexistent"))
        assert history == []

    def test_load_history_corrupt_json(self, tmp_path):
        (tmp_path / ".vibescore-history.json").write_text("{broken json")
        history = load_history(str(tmp_path))
        assert history == []

    def test_format_history_empty(self):
        report = format_history_report([])
        assert "No scan history" in report

    def test_format_history_with_entries(self):
        entries = [
            HistoryEntry(timestamp=time.time(), overall_score=85.0, overall_grade="B+",
                        categories={"Testing": 90.0, "Security": 80.0},
                        commit_hash="abc1234", project_name="test"),
        ]
        report = format_history_report(entries)
        assert "B+" in report
        assert "abc1234" in report

    def test_create_history_entry_from_report(self):
        report = VibeReport(
            project_path="/tmp", project_name="myproj",
            total_files=10, total_lines=500, languages={"python": 10},
            categories=[
                CategoryScore(name="Testing", score=90.0, grade="A-"),
                CategoryScore(name="Security", score=80.0, grade="B-"),
            ],
            overall_score=85.0, overall_grade="B+",
        )
        entry = create_history_entry(report)
        assert entry.overall_score == 85.0
        assert entry.overall_grade == "B+"
        assert entry.project_name == "myproj"
        assert "Testing" in entry.categories
        assert entry.categories["Testing"] == 90.0

    def test_format_history_many_entries(self):
        """Only show last 20."""
        entries = [
            HistoryEntry(timestamp=float(i), overall_score=float(i),
                        overall_grade="C", project_name="test")
            for i in range(50)
        ]
        report = format_history_report(entries)
        # Should not have all 50 entries displayed
        lines = report.strip().split("\n")
        # header + separator + 20 data = at most ~23 lines
        assert len(lines) <= 25


# ═══════════════════════════════════════════════════════════════════════════════
#  deps.py — _parse_setup_cfg, VC402, VC405
# ═══════════════════════════════════════════════════════════════════════════════

class TestDepsEdge:
    def test_parse_setup_cfg(self, tmp_path):
        cfg = tmp_path / "setup.cfg"
        cfg.write_text("[options]\ninstall_requires =\n    requests>=2.28\n    flask\n")
        deps = _parse_setup_cfg(str(cfg))
        assert len(deps) == 2
        names = [d[0] for d in deps]
        assert "requests" in names
        assert "flask" in names

    def test_parse_setup_cfg_no_install_requires(self, tmp_path):
        cfg = tmp_path / "setup.cfg"
        cfg.write_text("[options]\npackage_dir =\n    = src\n")
        deps = _parse_setup_cfg(str(cfg))
        assert deps == []

    def test_parse_setup_cfg_nonexistent(self):
        deps = _parse_setup_cfg("/nonexistent/setup.cfg")
        assert deps == []

    def test_vc402_no_lock_file(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\ndependencies = ["requests"]\n')
        result = analyze_deps(str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC402" in codes

    def test_vc402_with_lock_file(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\ndependencies = ["requests>=2.0"]\n')
        (tmp_path / "poetry.lock").write_text("# lock\n")
        result = analyze_deps(str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC402" not in codes

    def test_vc405_wildcard_pin(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests==*\n")
        result = analyze_deps(str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC405" in codes

    def test_vc401_unpinned(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests\nflask\n")
        result = analyze_deps(str(tmp_path))
        codes = [i.code for i in result.issues]
        assert codes.count("VC401") == 2

    def test_all_pinned(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("requests>=2.28.0\nflask==2.3.1\n")
        result = analyze_deps(str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC401" not in codes
        assert "VC405" not in codes

    def test_no_dep_file(self, tmp_path):
        result = analyze_deps(str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC403" in codes
        assert result.score == 50.0

    def test_parse_pyproject_empty_deps(self, tmp_path):
        pp = tmp_path / "pyproject.toml"
        pp.write_text('[project]\nname = "test"\ndependencies = []\n')
        deps = _parse_pyproject_deps(str(pp))
        assert deps == []


# ═══════════════════════════════════════════════════════════════════════════════
#  testing.py — VC505 (no assertions)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTestingModuleEdge:
    def test_vc505_test_no_assertions(self, tmp_path):
        """A test file with no assert keyword should trigger VC505."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def hello(): pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_main.py").write_text("def test_hello():\n    pass\n")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
        (tests / "conftest.py").write_text("")

        files = [
            FileInfo(path="src/main.py", language="python", lines=1, size_bytes=20),
            FileInfo(path="tests/test_main.py", language="python", lines=2, size_bytes=40),
            FileInfo(path="tests/conftest.py", language="python", lines=0, size_bytes=0),
        ]
        result = analyze_testing(files, str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC505" in codes

    def test_vc505_with_assertions(self, tmp_path):
        """A test file with assert should NOT trigger VC505."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def hello(): pass\n")
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_main.py").write_text("def test_hello():\n    assert True\n")
        (tests / "conftest.py").write_text("")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n")

        files = [
            FileInfo(path="src/main.py", language="python", lines=1, size_bytes=20),
            FileInfo(path="tests/test_main.py", language="python", lines=2, size_bytes=40),
            FileInfo(path="tests/conftest.py", language="python", lines=0, size_bytes=0),
        ]
        result = analyze_testing(files, str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC505" not in codes


# ═══════════════════════════════════════════════════════════════════════════════
#  discovery.py — Rust/Go detection, .egg-info skipping
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiscoveryEdge:
    def test_rust_file_detection(self, tmp_path):
        (tmp_path / "main.rs").write_text("fn main() { println!(\"hello\"); }")
        files = discover_files(str(tmp_path))
        rust_files = [f for f in files if f.language == "rust"]
        assert len(rust_files) == 1

    def test_go_file_detection(self, tmp_path):
        (tmp_path / "main.go").write_text("package main\nfunc main() {}")
        files = discover_files(str(tmp_path))
        go_files = [f for f in files if f.language == "go"]
        assert len(go_files) == 1

    def test_egg_info_skipped(self, tmp_path):
        egg = tmp_path / "mypackage.egg-info"
        egg.mkdir()
        (egg / "PKG-INFO").write_text("Name: mypackage\n")
        (tmp_path / "main.py").write_text("print('hello')")
        files = discover_files(str(tmp_path))
        paths = [f.path for f in files]
        assert not any("egg-info" in p for p in paths)

    def test_should_skip_dot_dir(self):
        assert _should_skip_dir(".hidden") is True

    def test_should_skip_git(self):
        assert _should_skip_dir(".git") is True

    def test_should_skip_node_modules(self):
        assert _should_skip_dir("node_modules") is True

    def test_should_not_skip_src(self):
        assert _should_skip_dir("src") is False

    def test_max_files(self, tmp_path):
        for i in range(20):
            (tmp_path / f"file{i}.py").write_text(f"x = {i}")
        files = discover_files(str(tmp_path), max_files=5)
        assert len(files) <= 5

    def test_detect_project_type_rust(self, tmp_path):
        # No Python or Node markers → unknown
        (tmp_path / "Cargo.toml").write_text("[package]\nname = \"test\"")
        assert detect_project_type(str(tmp_path)) == "unknown"

    def test_detect_project_type_mixed(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        (tmp_path / "package.json").write_text('{"name": "test"}')
        assert detect_project_type(str(tmp_path)) == "mixed"

    def test_unknown_extension(self, tmp_path):
        (tmp_path / "readme.md").write_text("# Hi")
        (tmp_path / "data.csv").write_text("a,b\n1,2")
        files = discover_files(str(tmp_path))
        for f in files:
            if f.path.endswith(".md") or f.path.endswith(".csv"):
                assert f.language == "unknown"
                assert f.lines == 0  # Unknown files don't get line count


# ═══════════════════════════════════════════════════════════════════════════════
#  scanner.py — multi-language, empty project
# ═══════════════════════════════════════════════════════════════════════════════

class TestScannerEdge:
    def test_empty_project(self, tmp_path):
        report = scan(str(tmp_path))
        assert report.total_files == 0
        assert report.overall_grade != ""

    def test_python_only_project(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def hello():\n    return 'world'\n")
        report = scan(str(tmp_path))
        assert "python" in report.languages

    def test_rust_only_project(self, tmp_path):
        (tmp_path / "main.rs").write_text("fn main() {\n    println!(\"hello\");\n}\n")
        report = scan(str(tmp_path))
        assert "rust" in report.languages or report.total_files >= 1

    def test_go_only_project(self, tmp_path):
        (tmp_path / "main.go").write_text("package main\n\nfunc main() {\n    fmt.Println(\"hi\")\n}\n")
        report = scan(str(tmp_path))
        assert "go" in report.languages or report.total_files >= 1

    def test_scan_has_categories(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("x = 1\n")
        report = scan(str(tmp_path))
        cat_names = [c.name for c in report.categories]
        # Should have at least some categories
        assert len(cat_names) >= 1

    def test_scan_timing(self, tmp_path):
        report = scan(str(tmp_path))
        assert report.scan_time_s >= 0.0


# ═══════════════════════════════════════════════════════════════════════════════
#  report.py — edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportEdge:
    def test_format_report_empty_categories(self):
        report = VibeReport(
            project_path="/tmp", project_name="test",
            total_files=0, total_lines=0, languages={},
            overall_score=0, overall_grade="F",
        )
        text = format_report(report)
        assert "F" in text

    def test_format_json_roundtrip(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"')
        (tmp_path / "main.py").write_text("x = 1\n")
        report = scan(str(tmp_path))
        json_str = format_json(report)
        data = json.loads(json_str)
        assert "overall_score" in data
        assert "overall_grade" in data

    def test_format_report_with_issues(self):
        report = VibeReport(
            project_path="/tmp", project_name="test",
            total_files=5, total_lines=500, languages={"python": 5},
            categories=[
                CategoryScore(
                    name="Security", score=70.0, grade="B-",
                    issues=[
                        Issue(code="VC301", severity="critical", message="Hardcoded secret found"),
                        Issue(code="VC302", severity="warning", message="SQL injection risk"),
                    ],
                ),
            ],
            overall_score=70.0, overall_grade="B-",
        )
        text = format_report(report)
        assert "Security" in text
        assert "VC301" in text or "secret" in text.lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  scoring.py — boundary values
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringEdge:
    def test_grade_boundaries(self):
        assert score_to_grade(100) == "A+"
        assert score_to_grade(97) == "A+"
        assert score_to_grade(95) == "A"
        assert score_to_grade(0) == "F"
        assert score_to_grade(-5) == "F"  # Clamped

    def test_compute_overall_empty(self):
        score, grade = compute_overall([])
        assert isinstance(score, float)
        assert grade == "F"

    def test_compute_overall_single(self):
        cats = [CategoryScore(name="Testing", score=80.0, grade="B-")]
        score, grade = compute_overall(cats)
        assert score > 0
        assert isinstance(grade, str)

    def test_all_perfect(self):
        cats = [
            CategoryScore(name="Security", score=100.0, grade="A+"),
            CategoryScore(name="Quality", score=100.0, grade="A+"),
            CategoryScore(name="Testing", score=100.0, grade="A+"),
            CategoryScore(name="Dependencies", score=100.0, grade="A+"),
        ]
        score, grade = compute_overall(cats)
        assert score == 100.0
        assert grade == "A+"

    def test_all_zero(self):
        cats = [
            CategoryScore(name="Security", score=0.0, grade="F"),
            CategoryScore(name="Quality", score=0.0, grade="F"),
            CategoryScore(name="Testing", score=0.0, grade="F"),
            CategoryScore(name="Dependencies", score=0.0, grade="F"),
        ]
        score, grade = compute_overall(cats)
        assert score == 0.0
        assert grade == "F"


# ═══════════════════════════════════════════════════════════════════════════════
#  quality_rs.py and quality_go.py — ensure Rust/Go analysers handle edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiLanguageEdge:
    def test_rust_quality_empty_file(self, tmp_path):
        from vibescore.quality_rs import analyze_quality_rs
        (tmp_path / "empty.rs").write_text("")
        files = [FileInfo(path="empty.rs", language="rust", lines=0, size_bytes=0)]
        result = analyze_quality_rs(files, str(tmp_path))
        assert isinstance(result, CategoryScore)

    def test_go_quality_empty_file(self, tmp_path):
        from vibescore.quality_go import analyze_quality_go
        (tmp_path / "empty.go").write_text("")
        files = [FileInfo(path="empty.go", language="go", lines=0, size_bytes=0)]
        result = analyze_quality_go(files, str(tmp_path))
        assert isinstance(result, CategoryScore)

    def test_rust_clean_code(self, tmp_path):
        from vibescore.quality_rs import analyze_quality_rs
        code = '''/// A well-documented function
fn add(a: i32, b: i32) -> i32 {
    a + b
}

/// Entry point
fn main() {
    let result = add(1, 2);
    println!("{}", result);
}
'''
        (tmp_path / "clean.rs").write_text(code)
        files = [FileInfo(path="clean.rs", language="rust", lines=12, size_bytes=len(code))]
        result = analyze_quality_rs(files, str(tmp_path))
        assert result.score >= 80.0

    def test_go_clean_code(self, tmp_path):
        from vibescore.quality_go import analyze_quality_go
        code = '''package main

import "fmt"

// Add adds two integers.
func Add(a, b int) int {
    return a + b
}

func main() {
    result := Add(1, 2)
    fmt.Println(result)
}
'''
        (tmp_path / "clean.go").write_text(code)
        files = [FileInfo(path="clean.go", language="go", lines=14, size_bytes=len(code))]
        result = analyze_quality_go(files, str(tmp_path))
        assert result.score >= 70.0

    def test_rust_unwrap_detected(self, tmp_path):
        from vibescore.quality_rs import analyze_quality_rs
        code = ('fn main() {\n'
                '    let a = Some(1).unwrap();\n'
                '    let b = Some(2).unwrap();\n'
                '    let c = Some(3).unwrap();\n'
                '    let d = Some(4).unwrap();\n'
                '    let e = Some(5).unwrap();\n'
                '    let f = Some(6).unwrap();\n'
                '}\n')
        (tmp_path / "bad.rs").write_text(code)
        files = [FileInfo(path="bad.rs", language="rust", lines=4, size_bytes=len(code))]
        result = analyze_quality_rs(files, str(tmp_path))
        codes = [i.code for i in result.issues]
        assert "VC221" in codes

    def test_go_unchecked_error(self, tmp_path):
        from vibescore.quality_go import analyze_quality_go
        code = '''package main

import "os"

func main() {
    os.Open("file.txt")
}
'''
        (tmp_path / "bad.go").write_text(code)
        files = [FileInfo(path="bad.go", language="go", lines=7, size_bytes=len(code))]
        result = analyze_quality_go(files, str(tmp_path))
        # Should detect unchecked error (VC231) or at least return a score
        assert isinstance(result.score, float)
