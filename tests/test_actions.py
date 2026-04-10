from __future__ import annotations

import os
import tempfile
import unittest

from vibescore.actions import generate_workflow
from vibescore.cli import main


class TestGenerateWorkflowDefault(unittest.TestCase):
    def test_generate_workflow_default(self):
        yml = generate_workflow()
        self.assertIn("name: Vibe Check", yml)
        self.assertIn("threshold C", yml)
        self.assertIn('python-version: "3.12"', yml)
        self.assertIn("push:", yml)
        self.assertIn("pull_request:", yml)


class TestGenerateWorkflowCustomThreshold(unittest.TestCase):
    def test_generate_workflow_custom_threshold(self):
        yml = generate_workflow(threshold="A")
        self.assertIn("threshold A", yml)
        self.assertNotIn("threshold C", yml)


class TestGenerateWorkflowCustomPython(unittest.TestCase):
    def test_generate_workflow_custom_python(self):
        yml = generate_workflow(python_version="3.11")
        self.assertIn('python-version: "3.11"', yml)
        self.assertNotIn("3.12", yml)


class TestGenerateWorkflowPushOnly(unittest.TestCase):
    def test_generate_workflow_push_only(self):
        yml = generate_workflow(on_push=True, on_pull_request=False)
        self.assertIn("push:", yml)
        self.assertNotIn("pull_request:", yml)


class TestGenerateWorkflowPROnly(unittest.TestCase):
    def test_generate_workflow_pr_only(self):
        yml = generate_workflow(on_push=False, on_pull_request=True)
        self.assertNotIn("push:", yml)
        self.assertIn("pull_request:", yml)


class TestWorkflowContainsCheckout(unittest.TestCase):
    def test_workflow_contains_checkout(self):
        yml = generate_workflow()
        self.assertIn("actions/checkout@v4", yml)


class TestWorkflowContainsVibescore(unittest.TestCase):
    def test_workflow_contains_vibescore(self):
        yml = generate_workflow()
        self.assertIn("pip install vibescore", yml)
        self.assertIn("vibescore --threshold", yml)


class TestInitCiCreatesFile(unittest.TestCase):
    def test_init_ci_creates_file(self):
        import io
        import contextlib

        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ret = main(["--init-ci", d])
            self.assertEqual(ret, 0)
            wf = os.path.join(d, ".github", "workflows", "vibescore.yml")
            self.assertTrue(os.path.isfile(wf))
            with open(wf) as f:
                content = f.read()
            self.assertIn("name: Vibe Check", content)
            output = buf.getvalue()
            self.assertIn("vibescore.yml", output)
            self.assertIn("Commit", output)
