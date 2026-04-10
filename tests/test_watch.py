from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest

from vibescore.watch import get_file_mtimes, watch


class TestGetFileMtimesFindsFiles(unittest.TestCase):
    def test_get_file_mtimes_finds_py_files(self):
        with tempfile.TemporaryDirectory() as d:
            py_file = os.path.join(d, "app.py")
            with open(py_file, "w") as f:
                f.write("x = 1\n")
            mtimes = get_file_mtimes(d)
            self.assertEqual(len(mtimes), 1)
            self.assertIn(py_file, mtimes)


class TestGetFileMtimesSkipsHidden(unittest.TestCase):
    def test_get_file_mtimes_skips_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            hidden = os.path.join(d, ".hidden")
            os.makedirs(hidden)
            with open(os.path.join(hidden, "secret.py"), "w") as f:
                f.write("x = 1\n")
            mtimes = get_file_mtimes(d)
            self.assertEqual(len(mtimes), 0)


class TestGetFileMtimesSkipsNodeModules(unittest.TestCase):
    def test_get_file_mtimes_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            nm = os.path.join(d, "node_modules")
            os.makedirs(nm)
            with open(os.path.join(nm, "index.js"), "w") as f:
                f.write("module.exports = {};\n")
            mtimes = get_file_mtimes(d)
            self.assertEqual(len(mtimes), 0)


class TestGetFileMtimesEmptyDir(unittest.TestCase):
    def test_get_file_mtimes_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            mtimes = get_file_mtimes(d)
            self.assertEqual(len(mtimes), 0)


class TestWatchDetectsNewFile(unittest.TestCase):
    def test_watch_detects_new_file(self):
        with tempfile.TemporaryDirectory() as d:
            changed: list[str] = []

            def _create_file():
                time.sleep(0.3)
                with open(os.path.join(d, "new.py"), "w") as f:
                    f.write("y = 2\n")

            t = threading.Thread(target=_create_file)
            t.start()
            watch(d, changed.append, interval=0.2, max_iterations=3)
            t.join()
            self.assertTrue(len(changed) >= 1)


class TestWatchMaxIterationsStops(unittest.TestCase):
    def test_watch_max_iterations_stops(self):
        with tempfile.TemporaryDirectory() as d:
            calls: list[str] = []
            start = time.monotonic()
            watch(d, calls.append, interval=0.05, max_iterations=2)
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 5.0)
            self.assertEqual(len(calls), 0)


class TestGetFileMtimesCustomExtensions(unittest.TestCase):
    def test_get_file_mtimes_custom_extensions(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "data.csv"), "w") as f:
                f.write("a,b\n")
            with open(os.path.join(d, "app.py"), "w") as f:
                f.write("x = 1\n")
            mtimes = get_file_mtimes(d, extensions=(".csv",))
            self.assertEqual(len(mtimes), 1)
            self.assertTrue(any("data.csv" in k for k in mtimes))


class TestWatchCallbackCalledOnChange(unittest.TestCase):
    def test_watch_callback_called_on_change(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "mod.py")
            with open(target, "w") as f:
                f.write("a = 1\n")

            changed: list[str] = []

            def _modify():
                time.sleep(0.3)
                with open(target, "w") as f:
                    f.write("a = 2\n")

            t = threading.Thread(target=_modify)
            t.start()
            watch(d, changed.append, interval=0.2, max_iterations=3)
            t.join()
            self.assertTrue(len(changed) >= 1)
            self.assertTrue(any("mod.py" in p for p in changed))
