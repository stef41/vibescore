from __future__ import annotations

import json
import os
import tempfile
import unittest

from vibescore.scanner import scan
from vibescore.report import format_report, format_json


def _make_report():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "app.py"), "w") as f:
            f.write("x = 1\n")
        return scan(d)


class TestFormatReport(unittest.TestCase):
    def test_contains_project_name(self):
        report = _make_report()
        text = format_report(report)
        self.assertIn(report.project_name, text)

    def test_contains_vibe_check_header(self):
        text = format_report(_make_report())
        self.assertIn("Vibe Check", text)

    def test_contains_all_categories(self):
        text = format_report(_make_report())
        self.assertIn("Code Quality", text)
        self.assertIn("Security", text)
        self.assertIn("Dependencies", text)
        self.assertIn("Testing", text)

    def test_contains_overall(self):
        text = format_report(_make_report())
        self.assertIn("Overall", text)

    def test_contains_grade(self):
        report = _make_report()
        text = format_report(report)
        self.assertIn(report.overall_grade, text)

    def test_contains_file_count(self):
        report = _make_report()
        text = format_report(report)
        self.assertIn(str(report.total_files), text)

    def test_is_string(self):
        text = format_report(_make_report())
        self.assertIsInstance(text, str)


class TestFormatJson(unittest.TestCase):
    def test_valid_json(self):
        report = _make_report()
        output = format_json(report)
        data = json.loads(output)
        self.assertIsInstance(data, dict)

    def test_contains_overall_score(self):
        output = format_json(_make_report())
        data = json.loads(output)
        self.assertIn("overall_score", data)

    def test_contains_overall_grade(self):
        output = format_json(_make_report())
        data = json.loads(output)
        self.assertIn("overall_grade", data)

    def test_contains_categories(self):
        output = format_json(_make_report())
        data = json.loads(output)
        self.assertIn("categories", data)
        self.assertEqual(len(data["categories"]), 4)

    def test_contains_project_path(self):
        output = format_json(_make_report())
        data = json.loads(output)
        self.assertIn("project_path", data)

    def test_contains_languages(self):
        output = format_json(_make_report())
        data = json.loads(output)
        self.assertIn("languages", data)

    def test_contains_scan_time(self):
        output = format_json(_make_report())
        data = json.loads(output)
        self.assertIn("scan_time_s", data)

    def test_category_has_issues(self):
        output = format_json(_make_report())
        data = json.loads(output)
        for cat in data["categories"]:
            self.assertIn("issues", cat)
            self.assertIn("score", cat)
            self.assertIn("grade", cat)


class TestFormatReportRich(unittest.TestCase):
    """Tests for the rich-formatted report."""

    def setUp(self):
        try:
            import rich  # noqa: F401
            self.rich_available = True
        except ImportError:
            self.rich_available = False

    def test_rich_returns_string(self):
        if not self.rich_available:
            self.skipTest("rich not installed")
        from vibescore.report import format_report_rich
        text = format_report_rich(_make_report())
        self.assertIsInstance(text, str)

    def test_rich_contains_project_name(self):
        if not self.rich_available:
            self.skipTest("rich not installed")
        from vibescore.report import format_report_rich
        report = _make_report()
        text = format_report_rich(report)
        self.assertIn(report.project_name, text)

    def test_rich_contains_categories(self):
        if not self.rich_available:
            self.skipTest("rich not installed")
        from vibescore.report import format_report_rich
        text = format_report_rich(_make_report())
        self.assertIn("Code Quality", text)
        self.assertIn("Security", text)
        self.assertIn("Dependencies", text)
        self.assertIn("Testing", text)

    def test_rich_contains_overall(self):
        if not self.rich_available:
            self.skipTest("rich not installed")
        from vibescore.report import format_report_rich
        text = format_report_rich(_make_report())
        self.assertIn("Overall", text)

    def test_rich_contains_vibe_check_header(self):
        if not self.rich_available:
            self.skipTest("rich not installed")
        from vibescore.report import format_report_rich
        text = format_report_rich(_make_report())
        self.assertIn("Vibe Check", text)

    def test_rich_import_error_fallback(self):
        """format_report_rich raises ImportError when rich is missing."""
        import unittest.mock
        import vibescore.report as mod
        with unittest.mock.patch.dict("sys.modules", {"rich": None, "rich.console": None, "rich.panel": None, "rich.table": None, "rich.text": None}):
            with self.assertRaises(ImportError):
                mod.format_report_rich(_make_report())


if __name__ == "__main__":
    unittest.main()
