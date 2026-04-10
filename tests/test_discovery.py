from __future__ import annotations

import os
import tempfile
import unittest

from vibescore.discovery import discover_files, detect_project_type


class TestDiscoverFiles(unittest.TestCase):
    def test_finds_py_files(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "main.py"), "w") as f:
                f.write("print('hello')\n")
            files = discover_files(d)
            py = [fi for fi in files if fi.language == "python"]
            self.assertEqual(len(py), 1)
            self.assertEqual(py[0].lines, 1)

    def test_skips_pycache(self):
        with tempfile.TemporaryDirectory() as d:
            cache_dir = os.path.join(d, "__pycache__")
            os.makedirs(cache_dir)
            with open(os.path.join(cache_dir, "mod.cpython-311.pyc"), "w") as f:
                f.write("bytecode")
            with open(os.path.join(d, "app.py"), "w") as f:
                f.write("x = 1\n")
            files = discover_files(d)
            paths = [fi.path for fi in files]
            self.assertTrue(all("__pycache__" not in p for p in paths))

    def test_skips_git(self):
        with tempfile.TemporaryDirectory() as d:
            git_dir = os.path.join(d, ".git")
            os.makedirs(git_dir)
            with open(os.path.join(git_dir, "config"), "w") as f:
                f.write("[core]\n")
            with open(os.path.join(d, "a.py"), "w") as f:
                f.write("pass\n")
            files = discover_files(d)
            paths = [fi.path for fi in files]
            self.assertTrue(all(".git" not in p for p in paths))

    def test_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            nm = os.path.join(d, "node_modules")
            os.makedirs(nm)
            with open(os.path.join(nm, "index.js"), "w") as f:
                f.write("module.exports = {}\n")
            with open(os.path.join(d, "app.js"), "w") as f:
                f.write("console.log('hi')\n")
            files = discover_files(d)
            paths = [fi.path for fi in files]
            self.assertTrue(all("node_modules" not in p for p in paths))

    def test_counts_lines(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "code.py"), "w") as f:
                f.write("a = 1\nb = 2\nc = 3\n")
            files = discover_files(d)
            py = [fi for fi in files if fi.language == "python"]
            self.assertEqual(py[0].lines, 3)

    def test_language_detection_js(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "app.js"), "w") as f:
                f.write("// js\n")
            files = discover_files(d)
            js = [fi for fi in files if fi.language == "javascript"]
            self.assertEqual(len(js), 1)

    def test_language_detection_ts(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "app.ts"), "w") as f:
                f.write("// ts\n")
            files = discover_files(d)
            ts = [fi for fi in files if fi.language == "typescript"]
            self.assertEqual(len(ts), 1)

    def test_max_files_limit(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(20):
                with open(os.path.join(d, f"f{i}.py"), "w") as f:
                    f.write("pass\n")
            files = discover_files(d, max_files=5)
            self.assertLessEqual(len(files), 5)

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            files = discover_files(d)
            self.assertEqual(len(files), 0)

    def test_unknown_extension(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "data.csv"), "w") as f:
                f.write("a,b,c\n")
            files = discover_files(d)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].language, "unknown")
            # unknown files get 0 lines
            self.assertEqual(files[0].lines, 0)


class TestDetectProjectType(unittest.TestCase):
    def test_python_pyproject(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "pyproject.toml"), "w") as f:
                f.write("[project]\n")
            self.assertEqual(detect_project_type(d), "python")

    def test_node_package_json(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "package.json"), "w") as f:
                f.write("{}\n")
            self.assertEqual(detect_project_type(d), "node")

    def test_mixed(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "pyproject.toml"), "w") as f:
                f.write("[project]\n")
            with open(os.path.join(d, "package.json"), "w") as f:
                f.write("{}\n")
            self.assertEqual(detect_project_type(d), "mixed")

    def test_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(detect_project_type(d), "unknown")


if __name__ == "__main__":
    unittest.main()
