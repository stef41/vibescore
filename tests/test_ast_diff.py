"""Tests for AST-based structural diff."""

from __future__ import annotations

import pytest

from vibescore.ast_diff import (
    ASTDiffResult,
    ChangeKind,
    NodeInfo,
    SignatureInfo,
    StructuralChange,
    _estimate_complexity,
    diff_ast,
    extract_nodes,
)
import ast


class TestEstimateComplexity:
    def test_simple_function(self):
        code = "def f(): pass"
        tree = ast.parse(code).body[0]
        assert _estimate_complexity(tree) == 1

    def test_if_else(self):
        code = "def f(x):\n  if x:\n    return 1\n  else:\n    return 0"
        tree = ast.parse(code).body[0]
        assert _estimate_complexity(tree) == 2  # base + 1 if

    def test_nested_loops(self):
        code = "def f():\n  for i in r:\n    for j in r:\n      pass"
        tree = ast.parse(code).body[0]
        assert _estimate_complexity(tree) == 3  # base + 2 for

    def test_boolean_ops(self):
        code = "def f(a, b, c):\n  if a and b or c:\n    pass"
        tree = ast.parse(code).body[0]
        # base + if + and(1 extra) + or(1 extra) = 4
        assert _estimate_complexity(tree) >= 3

    def test_try_except(self):
        code = "def f():\n  try:\n    pass\n  except ValueError:\n    pass\n  except TypeError:\n    pass"
        tree = ast.parse(code).body[0]
        assert _estimate_complexity(tree) == 3  # base + 2 except

    def test_comprehension(self):
        code = "def f():\n  return [x for x in range(10) if x > 5]"
        tree = ast.parse(code).body[0]
        assert _estimate_complexity(tree) >= 2


class TestExtractNodes:
    def test_functions(self):
        code = "def foo(): pass\ndef bar(): pass"
        nodes = extract_nodes(code)
        assert "foo" in nodes
        assert "bar" in nodes
        assert nodes["foo"].kind == "function"

    def test_classes(self):
        code = "class Foo:\n  def method(self): pass"
        nodes = extract_nodes(code)
        assert "Foo" in nodes
        assert "Foo.method" in nodes
        assert nodes["Foo"].kind == "class"
        assert nodes["Foo.method"].kind == "method"

    def test_docstrings(self):
        code = 'def f():\n  """My doc."""\n  pass'
        nodes = extract_nodes(code)
        assert nodes["f"].docstring == "My doc."

    def test_no_docstring(self):
        code = "def f(): pass"
        nodes = extract_nodes(code)
        assert nodes["f"].docstring is None

    def test_signature_extraction(self):
        code = "def f(x, y, z=1): pass"
        nodes = extract_nodes(code)
        sig = nodes["f"].signature
        assert sig is not None
        assert sig.args == ["x", "y", "z"]
        assert sig.defaults == 1

    def test_self_filtered(self):
        code = "class C:\n  def m(self, x): pass"
        nodes = extract_nodes(code)
        sig = nodes["C.m"].signature
        assert "self" not in sig.args
        assert sig.args == ["x"]

    def test_syntax_error(self):
        nodes = extract_nodes("def (broken")
        assert nodes == {}

    def test_body_hash_differs(self):
        code1 = "def f(): return 1"
        code2 = "def f(): return 2"
        n1 = extract_nodes(code1)
        n2 = extract_nodes(code2)
        assert n1["f"].body_hash != n2["f"].body_hash


class TestDiffAST:
    def test_identical(self):
        code = "def f(): pass"
        result = diff_ast(code, code)
        assert result.unchanged_count == 1
        assert result.added_count == 0
        assert result.removed_count == 0
        assert result.modified_count == 0

    def test_added_function(self):
        old = "def f(): pass"
        new = "def f(): pass\ndef g(): pass"
        result = diff_ast(old, new)
        assert result.added_count == 1
        added = [c for c in result.changes if c.kind == ChangeKind.ADDED]
        assert added[0].name == "g"

    def test_removed_function(self):
        old = "def f(): pass\ndef g(): pass"
        new = "def f(): pass"
        result = diff_ast(old, new)
        assert result.removed_count == 1

    def test_modified_function(self):
        old = "def f(): return 1"
        new = "def f(): return 2"
        result = diff_ast(old, new)
        assert result.modified_count == 1

    def test_renamed_function(self):
        old = "def foo():\n  x = 1\n  return x + 2"
        new = "def bar():\n  x = 1\n  return x + 2"
        result = diff_ast(old, new)
        assert result.renamed_count == 1
        renames = [c for c in result.changes if c.kind == ChangeKind.RENAMED]
        assert renames[0].old_name == "foo"
        assert renames[0].name == "bar"

    def test_complexity_delta(self):
        old = "def f(): pass"
        new = "def f():\n  if True:\n    for x in r:\n      pass"
        result = diff_ast(old, new)
        assert result.complexity_delta > 0

    def test_churn_rate(self):
        old = "def f(): pass\ndef g(): pass"
        new = "def f(): return 1\ndef h(): pass"
        result = diff_ast(old, new)
        assert 0.0 < result.churn_rate <= 1.0

    def test_empty_sources(self):
        result = diff_ast("", "")
        assert result.added_count == 0
        assert result.removed_count == 0

    def test_class_modification(self):
        old = "class C:\n  def m(self): return 1"
        new = "class C:\n  def m(self): return 2"
        result = diff_ast(old, new)
        modified = [c for c in result.changes if c.kind == ChangeKind.MODIFIED]
        assert len(modified) >= 1

    def test_docstring_change(self):
        old = 'def f():\n  """Old doc."""\n  pass'
        new = 'def f():\n  """New doc."""\n  pass'
        result = diff_ast(old, new)
        assert result.modified_count >= 1
        deets = result.changes[0].details
        assert any("docstring" in d for d in deets)

    def test_signature_change(self):
        old = "def f(x): pass"
        new = "def f(x, y): pass"
        result = diff_ast(old, new)
        assert result.modified_count >= 1
        deets = result.changes[0].details
        assert any("args" in d for d in deets)

    def test_multiple_changes(self):
        old = "def a(): pass\ndef b(): pass\ndef c(): pass"
        new = "def a(): return 1\ndef d(): pass"
        result = diff_ast(old, new)
        assert result.modified_count + result.added_count + result.removed_count >= 2
