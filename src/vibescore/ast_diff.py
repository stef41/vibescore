"""AST-based structural diff between two Python source versions.

Goes beyond text-level diff to identify meaningful structural changes:
function add/remove/rename, class changes, signature modifications,
decorator changes, docstring mutations, complexity delta.

Uses the standard library `ast` module — no external dependencies.

Reference: Falleri et al. 2014, "Fine-grained and Accurate Source Code
Differencing" (GumTree); simplified to Python AST node-level comparison.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from enum import Enum


class ChangeKind(Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    UNCHANGED = "unchanged"


@dataclass
class SignatureInfo:
    """Extracted function/method signature."""
    name: str
    args: list[str]
    defaults: int
    has_varargs: bool
    has_kwargs: bool
    returns: str | None
    decorators: list[str]

    @property
    def arity(self) -> int:
        return len(self.args)


@dataclass
class NodeInfo:
    """Extracted info about an AST node (function or class)."""
    kind: str           # "function", "class", "method"
    name: str
    lineno: int
    end_lineno: int | None
    signature: SignatureInfo | None
    body_hash: str      # Hash of the normalized body source
    docstring: str | None
    complexity: int      # McCabe-like complexity estimate
    children: list[str]  # For classes: list of method names


@dataclass
class StructuralChange:
    """A single structural change between two versions."""
    kind: ChangeKind
    node_kind: str       # "function", "class", "method"
    name: str
    old_name: str | None = None  # For renames
    details: list[str] = field(default_factory=list)


@dataclass
class ASTDiffResult:
    """Result of comparing two Python source versions."""
    changes: list[StructuralChange]
    added_count: int
    removed_count: int
    modified_count: int
    renamed_count: int
    unchanged_count: int
    old_node_count: int
    new_node_count: int
    complexity_delta: int  # + means more complex, - means simpler

    @property
    def churn_rate(self) -> float:
        """Fraction of nodes that changed (0-1)."""
        total = max(self.old_node_count, self.new_node_count, 1)
        changed = self.added_count + self.removed_count + self.modified_count + self.renamed_count
        return min(1.0, changed / total)


# ── AST Analysis ─────────────────────────────────────────────────────────

def _estimate_complexity(node: ast.AST) -> int:
    """Estimate McCabe cyclomatic complexity of an AST node.

    Counts decision points: if, elif, for, while, except, with, and, or,
    assert, ternary (IfExp), comprehensions.
    """
    complexity = 1  # base complexity
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.IfExp)):
            complexity += 1
        elif isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, (ast.With, ast.AsyncWith)):
            complexity += 1
        elif isinstance(child, ast.Assert):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # Each additional and/or adds a decision
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            complexity += len(child.generators)
    return complexity


def _extract_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> SignatureInfo:
    """Extract function signature information."""
    args_info = node.args
    arg_names = [a.arg for a in args_info.args]
    # Filter out 'self' and 'cls'
    if arg_names and arg_names[0] in ("self", "cls"):
        arg_names = arg_names[1:]

    # Return annotation
    returns = None
    if node.returns:
        returns = ast.dump(node.returns)

    decorators = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            decorators.append(ast.dump(dec))
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)

    return SignatureInfo(
        name=node.name,
        args=arg_names,
        defaults=len(args_info.defaults),
        has_varargs=args_info.vararg is not None,
        has_kwargs=args_info.kwarg is not None,
        returns=returns,
        decorators=decorators,
    )


def _body_hash(node: ast.AST) -> str:
    """Compute a hash of the AST body, ignoring line numbers and formatting."""
    dumped = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(dumped.encode()).hexdigest()[:16]


def _extract_docstring(node: ast.AST) -> str | None:
    """Extract docstring from a function or class node."""
    if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.body):
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                return first.value.value
    return None


def extract_nodes(source: str) -> dict[str, NodeInfo]:
    """Parse Python source and extract structural nodes.

    Returns a dict mapping qualified names to NodeInfo objects.
    Top-level functions: "func_name"
    Classes: "ClassName"
    Methods: "ClassName.method_name"
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    nodes: dict[str, NodeInfo] = {}

    for top in ast.iter_child_nodes(tree):
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = top.name
            nodes[name] = NodeInfo(
                kind="function",
                name=name,
                lineno=top.lineno,
                end_lineno=getattr(top, "end_lineno", None),
                signature=_extract_signature(top),
                body_hash=_body_hash(top),
                docstring=_extract_docstring(top),
                complexity=_estimate_complexity(top),
                children=[],
            )
        elif isinstance(top, ast.ClassDef):
            class_name = top.name
            methods: list[str] = []
            for item in ast.iter_child_nodes(top):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{class_name}.{item.name}"
                    methods.append(item.name)
                    nodes[qname] = NodeInfo(
                        kind="method",
                        name=item.name,
                        lineno=item.lineno,
                        end_lineno=getattr(item, "end_lineno", None),
                        signature=_extract_signature(item),
                        body_hash=_body_hash(item),
                        docstring=_extract_docstring(item),
                        complexity=_estimate_complexity(item),
                        children=[],
                    )
            nodes[class_name] = NodeInfo(
                kind="class",
                name=class_name,
                lineno=top.lineno,
                end_lineno=getattr(top, "end_lineno", None),
                signature=None,
                body_hash=_body_hash(top),
                docstring=_extract_docstring(top),
                complexity=_estimate_complexity(top),
                children=methods,
            )

    return nodes


# ── Diffing ──────────────────────────────────────────────────────────────

def _detect_renames(
    removed: dict[str, NodeInfo],
    added: dict[str, NodeInfo],
    similarity_threshold: float = 0.7,
) -> list[tuple[str, str]]:
    """Detect renames by matching body hashes of removed → added nodes.

    Two nodes are considered a rename if they have the same body hash
    and the same kind.  This catches simple renames without body changes.

    For body-changed renames, we use signature similarity.
    """
    renames: list[tuple[str, str]] = []
    used_added: set[str] = set()

    # Phase 1: exact body hash match
    for old_name, old_node in list(removed.items()):
        for new_name, new_node in list(added.items()):
            if new_name in used_added:
                continue
            if old_node.kind == new_node.kind and old_node.body_hash == new_node.body_hash:
                renames.append((old_name, new_name))
                used_added.add(new_name)
                break

    # Phase 2: signature similarity for remaining
    remaining_removed = {k: v for k, v in removed.items() if k not in {r[0] for r in renames}}
    remaining_added = {k: v for k, v in added.items() if k not in used_added}

    for old_name, old_node in remaining_removed.items():
        if old_node.signature is None:
            continue
        best_match = None
        best_score = 0.0
        for new_name, new_node in remaining_added.items():
            if new_name in used_added:
                continue
            if new_node.kind != old_node.kind or new_node.signature is None:
                continue
            # Compare signatures
            old_sig = old_node.signature
            new_sig = new_node.signature
            score = 0.0
            # Same arity
            if old_sig.arity == new_sig.arity:
                score += 0.4
            # Same args
            common_args = len(set(old_sig.args) & set(new_sig.args))
            if old_sig.args or new_sig.args:
                score += 0.3 * common_args / max(len(old_sig.args), len(new_sig.args), 1)
            # Same return type
            if old_sig.returns == new_sig.returns:
                score += 0.2
            # Same complexity
            if old_node.complexity == new_node.complexity:
                score += 0.1
            if score > best_score:
                best_score = score
                best_match = new_name

        if best_match and best_score >= similarity_threshold:
            renames.append((old_name, best_match))
            used_added.add(best_match)

    return renames


def diff_ast(old_source: str, new_source: str) -> ASTDiffResult:
    """Compute structural diff between two Python source versions.

    Identifies added, removed, modified, and renamed functions/classes/methods.
    Also tracks complexity delta.

    Args:
        old_source: Python source code (before).
        new_source: Python source code (after).

    Returns:
        ASTDiffResult with categorized structural changes.
    """
    old_nodes = extract_nodes(old_source)
    new_nodes = extract_nodes(new_source)

    old_names = set(old_nodes)
    new_names = set(new_nodes)

    # Names present in both
    common = old_names & new_names
    only_old = {n: old_nodes[n] for n in old_names - common}
    only_new = {n: new_nodes[n] for n in new_names - common}

    # Detect renames from only_old → only_new
    renames = _detect_renames(only_old, only_new)
    renamed_old = {r[0] for r in renames}
    renamed_new = {r[1] for r in renames}

    changes: list[StructuralChange] = []
    added = 0
    removed = 0
    modified = 0
    renamed_count = 0
    unchanged = 0
    complexity_delta = 0

    # Renames
    for old_name, new_name in renames:
        old_node = old_nodes[old_name]
        new_node = new_nodes[new_name]
        details = [f"renamed from '{old_name}' to '{new_name}'"]
        if old_node.body_hash != new_node.body_hash:
            details.append("body also changed")
        changes.append(StructuralChange(
            kind=ChangeKind.RENAMED,
            node_kind=old_node.kind,
            name=new_name,
            old_name=old_name,
            details=details,
        ))
        renamed_count += 1
        complexity_delta += new_node.complexity - old_node.complexity

    # Pure additions
    for name in only_new:
        if name in renamed_new:
            continue
        node = new_nodes[name]
        changes.append(StructuralChange(
            kind=ChangeKind.ADDED,
            node_kind=node.kind,
            name=name,
            details=[f"added at line {node.lineno}"],
        ))
        added += 1
        complexity_delta += node.complexity

    # Pure removals
    for name in only_old:
        if name in renamed_old:
            continue
        node = old_nodes[name]
        changes.append(StructuralChange(
            kind=ChangeKind.REMOVED,
            node_kind=node.kind,
            name=name,
            details=[f"removed (was at line {node.lineno})"],
        ))
        removed += 1
        complexity_delta -= node.complexity

    # Common names — check for modifications
    for name in common:
        old_node = old_nodes[name]
        new_node = new_nodes[name]
        if old_node.body_hash == new_node.body_hash:
            unchanged += 1
            continue
        details: list[str] = []
        # Signature changes
        if old_node.signature and new_node.signature:
            old_sig = old_node.signature
            new_sig = new_node.signature
            if old_sig.args != new_sig.args:
                details.append(f"args: {old_sig.args} → {new_sig.args}")
            if old_sig.returns != new_sig.returns:
                details.append(f"return type changed")
            if old_sig.decorators != new_sig.decorators:
                details.append(f"decorators changed")
        # Docstring changes
        if old_node.docstring != new_node.docstring:
            if old_node.docstring is None:
                details.append("docstring added")
            elif new_node.docstring is None:
                details.append("docstring removed")
            else:
                details.append("docstring modified")
        # Complexity
        cdiff = new_node.complexity - old_node.complexity
        if cdiff != 0:
            details.append(f"complexity {'+' if cdiff > 0 else ''}{cdiff}")
        if not details:
            details.append("body changed")
        changes.append(StructuralChange(
            kind=ChangeKind.MODIFIED,
            node_kind=old_node.kind,
            name=name,
            details=details,
        ))
        modified += 1
        complexity_delta += new_node.complexity - old_node.complexity

    return ASTDiffResult(
        changes=changes,
        added_count=added,
        removed_count=removed,
        modified_count=modified,
        renamed_count=renamed_count,
        unchanged_count=unchanged,
        old_node_count=len(old_nodes),
        new_node_count=len(new_nodes),
        complexity_delta=complexity_delta,
    )
