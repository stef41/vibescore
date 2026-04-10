from __future__ import annotations

import os
import tempfile
import unittest

from vibescore.quality import analyze_quality
from vibescore._types import FileInfo


def _make_project(code: str, filename: str = "mod.py") -> tuple[str, list[FileInfo]]:
    """Write *code* to a temp dir and build a FileInfo list."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, filename)
    with open(path, "w") as f:
        f.write(code)
    lines = code.count("\n") + (1 if code and not code.endswith("\n") else 0)
    fi = FileInfo(path=filename, language="python", lines=lines, size_bytes=len(code.encode()))
    return d, [fi]


class TestVC201FunctionTooLong(unittest.TestCase):
    def test_long_function_flagged(self):
        body = "\n".join(f"    x{i} = {i}" for i in range(60))
        code = f"def big():\n{body}\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC201", codes)

    def test_short_function_ok(self):
        code = "def small():\n    return 1\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC201", codes)


class TestVC202HighComplexity(unittest.TestCase):
    def test_high_complexity_flagged(self):
        branches = "\n".join(f"    if x == {i}: pass" for i in range(15))
        code = f"def complex_func(x):\n{branches}\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC202", codes)

    def test_low_complexity_ok(self):
        code = "def simple(x):\n    if x: return 1\n    return 2\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC202", codes)


class TestVC203TooManyParams(unittest.TestCase):
    def test_many_params_flagged(self):
        code = "def many(a, b, c, d, e, f, g):\n    pass\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC203", codes)

    def test_self_excluded(self):
        code = "class C:\n    def ok(self, a, b, c, d, e):\n        pass\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC203", codes)


class TestVC204MissingTypeAnnotations(unittest.TestCase):
    def test_no_annotations_flagged(self):
        code = "def add(a, b):\n    return a + b\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC204", codes)

    def test_annotated_ok(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC204", codes)


class TestVC205DeepNesting(unittest.TestCase):
    def test_deep_nesting_flagged(self):
        code = (
            "def deep(x):\n"
            "    if x:\n"
            "        if x:\n"
            "            if x:\n"
            "                if x:\n"
            "                    if x:\n"
            "                        return 1\n"
        )
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC205", codes)

    def test_shallow_ok(self):
        code = "def flat(x):\n    if x:\n        return 1\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC205", codes)


class TestVC206FileTooLong(unittest.TestCase):
    def test_long_file_flagged(self):
        code = "\n".join(f"x{i} = {i}" for i in range(510)) + "\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC206", codes)

    def test_short_file_ok(self):
        code = "x = 1\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC206", codes)


class TestVC207StarImports(unittest.TestCase):
    def test_star_import_flagged(self):
        code = "from os import *\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC207", codes)

    def test_normal_import_ok(self):
        code = "from os import path\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC207", codes)


class TestVC208MissingDocstring(unittest.TestCase):
    def test_missing_docstring_flagged(self):
        code = "def public_func():\n    return 1\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC208", codes)

    def test_has_docstring_ok(self):
        code = 'def public_func():\n    """Does stuff."""\n    return 1\n'
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        vc208 = [i for i in result.issues if i.code == "VC208"]
        self.assertEqual(len(vc208), 0)

    def test_private_ignored(self):
        code = "def _private():\n    return 1\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        vc208 = [i for i in result.issues if i.code == "VC208"]
        self.assertEqual(len(vc208), 0)


class TestVC209MutableDefault(unittest.TestCase):
    def test_list_default_flagged(self):
        code = "def bad(x=[]):\n    return x\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC209", codes)

    def test_dict_default_flagged(self):
        code = "def bad(x={}):\n    return x\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertIn("VC209", codes)

    def test_none_default_ok(self):
        code = "def ok(x=None):\n    return x\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        codes = [i.code for i in result.issues]
        self.assertNotIn("VC209", codes)


class TestQualityScoring(unittest.TestCase):
    def test_clean_code_high_score(self):
        code = (
            'def greet(name: str) -> str:\n'
            '    """Return greeting."""\n'
            '    return f"Hello, {name}"\n'
        )
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        self.assertGreaterEqual(result.score, 90)

    def test_terrible_code_low_score(self):
        body = "\n".join(f"    x{i} = {i}" for i in range(60))
        branches = "\n".join(f"    if x == {i}: pass" for i in range(15))
        code = (
            "from os import *\n"
            f"def bad_func(a, b, c, d, e, f, g, x=[]):\n{body}\n{branches}\n"
        )
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        self.assertLess(result.score, 90)

    def test_empty_file(self):
        code = ""
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        self.assertEqual(result.score, 100.0)

    def test_syntax_error_no_crash(self):
        code = "def broken(\n    x = :\n"
        d, files = _make_project(code)
        result = analyze_quality(files, d)
        self.assertIsNotNone(result)

    def test_non_python_ignored(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "app.js"), "w") as f:
            f.write("eval('danger')\n")
        fi = FileInfo(path="app.js", language="javascript", lines=1, size_bytes=15)
        result = analyze_quality([fi], d)
        self.assertEqual(result.score, 100.0)


if __name__ == "__main__":
    unittest.main()
