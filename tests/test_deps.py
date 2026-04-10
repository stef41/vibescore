from __future__ import annotations

import os
import tempfile
import unittest

from vibe_check.deps import analyze_deps


class TestVC401UnpinnedDeps(unittest.TestCase):
    def test_unpinned_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("requests\nflask\n")
            result = analyze_deps(d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC401", codes)

    def test_pinned_ok(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("requests==2.31.0\nflask>=2.0.0\n")
            result = analyze_deps(d)
            vc401 = [i for i in result.issues if i.code == "VC401"]
            self.assertEqual(len(vc401), 0)

    def test_pinned_good_score(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("requests==2.31.0\nflask>=2.0.0\n")
            result = analyze_deps(d)
            self.assertGreaterEqual(result.score, 80)


class TestVC403NoDepsFile(unittest.TestCase):
    def test_no_deps_file_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            result = analyze_deps(d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC403", codes)

    def test_no_deps_file_low_score(self):
        with tempfile.TemporaryDirectory() as d:
            result = analyze_deps(d)
            self.assertEqual(result.score, 50.0)


class TestPyprojectDeps(unittest.TestCase):
    def test_pyproject_with_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "pyproject.toml"), "w") as f:
                f.write('[project]\ndependencies = [\n  "requests>=2.28",\n  "click>=8.0",\n]\n')
            result = analyze_deps(d)
            self.assertGreaterEqual(result.score, 80)

    def test_pyproject_with_unpinned(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "pyproject.toml"), "w") as f:
                f.write('[project]\ndependencies = [\n  "requests",\n  "click",\n]\n')
            result = analyze_deps(d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC401", codes)


class TestVC404SetupPyWithoutPyproject(unittest.TestCase):
    def test_setup_py_only_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "setup.py"), "w") as f:
                f.write("from setuptools import setup\nsetup()\n")
            result = analyze_deps(d)
            codes = [i.code for i in result.issues]
            self.assertIn("VC404", codes)

    def test_setup_py_with_pyproject_ok(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "setup.py"), "w") as f:
                f.write("from setuptools import setup\nsetup()\n")
            with open(os.path.join(d, "pyproject.toml"), "w") as f:
                f.write("[project]\n")
            result = analyze_deps(d)
            vc404 = [i for i in result.issues if i.code == "VC404"]
            self.assertEqual(len(vc404), 0)


class TestRequirementsTxtEdgeCases(unittest.TestCase):
    def test_empty_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("")
            result = analyze_deps(d)
            # No unpinned deps warnings
            vc401 = [i for i in result.issues if i.code == "VC401"]
            self.assertEqual(len(vc401), 0)

    def test_comments_and_blanks_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("# This is a comment\n\nrequests==2.31.0\n\n# Another comment\n")
            result = analyze_deps(d)
            vc401 = [i for i in result.issues if i.code == "VC401"]
            self.assertEqual(len(vc401), 0)

    def test_flag_lines_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("-r base.txt\n--index-url https://example.com\nrequests==2.31.0\n")
            result = analyze_deps(d)
            vc401 = [i for i in result.issues if i.code == "VC401"]
            self.assertEqual(len(vc401), 0)

    def test_details_counts(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "requirements.txt"), "w") as f:
                f.write("requests==2.31.0\nflask\n")
            result = analyze_deps(d)
            self.assertEqual(result.details["dependency_count"], 2)
            self.assertEqual(result.details["pinned_count"], 1)
            self.assertEqual(result.details["unpinned_count"], 1)


if __name__ == "__main__":
    unittest.main()
