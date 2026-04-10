from __future__ import annotations

import json
import os
import tempfile
import unittest

from vibescore.cli import main


class TestCLIVersion(unittest.TestCase):
    def test_version_flag(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)


class TestCLIJsonFormat(unittest.TestCase):
    def test_json_output(self):
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "app.py"), "w") as f:
                f.write("x = 1\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = main([d, "--format", "json"])
            output = buf.getvalue()
            data = json.loads(output)
            self.assertIn("overall_score", data)
            self.assertIn("overall_grade", data)
            self.assertEqual(ret, 0)


class TestCLIDefault(unittest.TestCase):
    def test_default_directory(self):
        import io
        import contextlib

        # Scan the vibe-check project itself
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ret = main([project_dir])
        output = buf.getvalue()
        self.assertIn("Vibe Check", output)
        self.assertIsInstance(ret, int)


class TestCLIMinScore(unittest.TestCase):
    def test_min_score_pass(self):
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = main([d, "--min-score", "0"])
            self.assertEqual(ret, 0)

    def test_min_score_fail(self):
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = main([d, "--min-score", "101"])
            self.assertEqual(ret, 1)


class TestCLINonExistentDir(unittest.TestCase):
    def test_nonexistent_returns_1(self):
        import io
        import contextlib

        buf_err = io.StringIO()
        with contextlib.redirect_stderr(buf_err):
            ret = main(["/nonexistent/path/that/does/not/exist"])
        self.assertEqual(ret, 1)
        self.assertIn("Error", buf_err.getvalue())


class TestCLITextFormat(unittest.TestCase):
    def test_text_has_categories(self):
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "mod.py"), "w") as f:
                f.write("x = 1\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                main([d, "--format", "text"])
            output = buf.getvalue()
            self.assertIn("Code Quality", output)
            self.assertIn("Security", output)
            self.assertIn("Dependencies", output)
            self.assertIn("Testing", output)


if __name__ == "__main__":
    unittest.main()
