from __future__ import annotations

import os
import tempfile
import unittest

from vibe_check.testing import analyze_testing
from vibe_check._types import FileInfo


def _make_project(src_files: dict[str, str], test_files: dict[str, str]) -> tuple[str, list[FileInfo]]:
    """Create temp project with src and test files, return root and FileInfo list."""
    d = tempfile.mkdtemp()
    infos: list[FileInfo] = []
    for name, content in src_files.items():
        path = os.path.join(d, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        infos.append(FileInfo(path=name, language="python", lines=lines, size_bytes=len(content.encode())))
    for name, content in test_files.items():
        path = os.path.join(d, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        infos.append(FileInfo(path=name, language="python", lines=lines, size_bytes=len(content.encode())))
    return d, infos


class TestVC501NoTestFiles(unittest.TestCase):
    def test_no_tests_flagged(self):
        d, files = _make_project({"app.py": "x = 1\n"}, {})
        result = analyze_testing(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC501", codes)

    def test_no_tests_score_zero(self):
        d, files = _make_project({"app.py": "x = 1\n"}, {})
        result = analyze_testing(files, d)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.grade, "F")


class TestWithTestFiles(unittest.TestCase):
    def test_has_tests_better_score(self):
        tests = {
            "test_app.py": "\n".join(
                [f"def test_case_{i}():\n    assert True" for i in range(12)]
            ) + "\n"
        }
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        result = analyze_testing(files, d)
        self.assertGreater(result.score, 0)

    def test_test_function_count(self):
        tests = {
            "test_app.py": "def test_a():\n    assert 1\ndef test_b():\n    assert 2\n"
        }
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        result = analyze_testing(files, d)
        self.assertEqual(result.details["test_function_count"], 2)


class TestVC502LowTestCount(unittest.TestCase):
    def test_few_tests_flagged(self):
        tests = {"test_one.py": "def test_a():\n    assert True\n"}
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        result = analyze_testing(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC502", codes)


class TestVC503NoCIConfig(unittest.TestCase):
    def test_no_ci_flagged(self):
        tests = {
            "test_app.py": "\n".join(
                [f"def test_{i}():\n    assert True" for i in range(12)]
            ) + "\n"
        }
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        result = analyze_testing(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC503", codes)

    def test_with_github_actions_ok(self):
        tests = {
            "test_app.py": "\n".join(
                [f"def test_{i}():\n    assert True" for i in range(12)]
            ) + "\n"
        }
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        wf = os.path.join(d, ".github", "workflows")
        os.makedirs(wf)
        with open(os.path.join(wf, "ci.yml"), "w") as f:
            f.write("name: CI\n")
        result = analyze_testing(files, d)
        vc503 = [i for i in result.issues if i.code == "VC503"]
        self.assertEqual(len(vc503), 0)


class TestVC504NoConftest(unittest.TestCase):
    def test_no_conftest_flagged(self):
        tests = {
            "test_app.py": "\n".join(
                [f"def test_{i}():\n    assert True" for i in range(12)]
            ) + "\n"
        }
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        result = analyze_testing(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC504", codes)

    def test_with_conftest_ok(self):
        tests = {
            "test_app.py": "\n".join(
                [f"def test_{i}():\n    assert True" for i in range(12)]
            ) + "\n"
        }
        d, files = _make_project({"app.py": "x = 1\n"}, tests)
        # Add conftest to files list
        conftest_path = os.path.join(d, "conftest.py")
        with open(conftest_path, "w") as f:
            f.write("# conftest\n")
        files.append(FileInfo(path="conftest.py", language="python", lines=1, size_bytes=12))
        result = analyze_testing(files, d)
        vc504 = [i for i in result.issues if i.code == "VC504"]
        self.assertEqual(len(vc504), 0)


class TestTestToCodeRatio(unittest.TestCase):
    def test_low_ratio_flagged(self):
        src = {f"mod{i}.py": "x = 1\n" for i in range(10)}
        tests = {"test_one.py": "def test_a():\n    assert True\n"}
        d, files = _make_project(src, tests)
        result = analyze_testing(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC506", codes)

    def test_details_ratio(self):
        src = {"app.py": "x = 1\n"}
        tests = {"test_app.py": "def test_a():\n    assert True\n"}
        d, files = _make_project(src, tests)
        result = analyze_testing(files, d)
        self.assertGreater(result.details["test_ratio"], 0)


if __name__ == "__main__":
    unittest.main()
