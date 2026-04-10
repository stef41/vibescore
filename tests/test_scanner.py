from __future__ import annotations

import os
import tempfile
import unittest

from vibescore.scanner import scan


class TestScan(unittest.TestCase):
    def test_scan_returns_report(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "main.py"), "w") as f:
                f.write("print('hello')\n")
            report = scan(d)
            self.assertIsNotNone(report)
            self.assertIsInstance(report.overall_score, float)
            self.assertIsInstance(report.overall_grade, str)

    def test_scan_has_all_categories(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "app.py"), "w") as f:
                f.write("x = 1\n")
            report = scan(d)
            names = [c.name for c in report.categories]
            self.assertIn("Code Quality", names)
            self.assertIn("Security", names)
            self.assertIn("Dependencies", names)
            self.assertIn("Testing", names)

    def test_overall_score_computed(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "app.py"), "w") as f:
                f.write("x = 1\n")
            report = scan(d)
            self.assertGreaterEqual(report.overall_score, 0)
            self.assertLessEqual(report.overall_score, 100)

    def test_scan_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            report = scan(d)
            self.assertEqual(report.total_files, 0)
            self.assertEqual(report.total_lines, 0)

    def test_scan_project_name(self):
        with tempfile.TemporaryDirectory() as d:
            report = scan(d)
            self.assertEqual(report.project_name, os.path.basename(d))

    def test_scan_counts_files(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                with open(os.path.join(d, f"m{i}.py"), "w") as f:
                    f.write(f"x = {i}\n")
            report = scan(d)
            self.assertGreaterEqual(report.total_files, 3)

    def test_scan_languages(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.py"), "w") as f:
                f.write("pass\n")
            with open(os.path.join(d, "b.js"), "w") as f:
                f.write("//js\n")
            report = scan(d)
            self.assertIn("python", report.languages)
            self.assertIn("javascript", report.languages)

    def test_scan_records_time(self):
        with tempfile.TemporaryDirectory() as d:
            report = scan(d)
            self.assertGreaterEqual(report.scan_time_s, 0)


if __name__ == "__main__":
    unittest.main()
