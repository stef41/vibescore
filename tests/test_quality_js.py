from __future__ import annotations

import os
import tempfile

import pytest

from vibescore._types import FileInfo
from vibescore.quality_js import analyze_quality_js


def _make_files(tmp: str, files: dict[str, str]) -> list[FileInfo]:
    """Write files into *tmp* and return FileInfo list."""
    infos: list[FileInfo] = []
    for name, content in files.items():
        path = os.path.join(tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        ext = os.path.splitext(name)[1].lower()
        lang = {"js": "javascript", ".js": "javascript", ".ts": "typescript",
                ".tsx": "typescript", ".jsx": "javascript"}.get(ext, "unknown")
        lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        infos.append(FileInfo(path=name, language=lang, lines=lines, size_bytes=len(content)))
    return infos


# ── VC211: Function too long ────────────────────────────────────────

def test_vc211_long_function():
    body = "\n".join(f"  const x{i} = {i};" for i in range(60))
    src = f"function longFunc() {{\n{body}\n}}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC211" in codes


def test_vc211_short_function_ok():
    src = "function short() {\n  return 1;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC211" not in codes


# ── VC212: Deep nesting ─────────────────────────────────────────────

def test_vc212_deep_nesting():
    # 5 levels of indentation (10 spaces = depth 5)
    src = "function deep() {\n" + "          if (true) {\n            x = 1;\n          }\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC212" in codes


def test_vc212_shallow_nesting_ok():
    src = "function ok() {\n  if (true) {\n    x = 1;\n  }\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    vc212 = [i for i in result.issues if i.code == "VC212"]
    assert len(vc212) == 0


# ── VC213: console.log in non-test files ────────────────────────────

def test_vc213_console_log_detected():
    src = "function run() {\n  console.log('debug');\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"src/app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC213" in codes


def test_vc213_console_log_ignored_in_test():
    src = "function run() {\n  console.log('ok in tests');\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"tests/app.test.js": src})
        result = analyze_quality_js(infos, tmp)
    vc213 = [i for i in result.issues if i.code == "VC213"]
    assert len(vc213) == 0


# ── VC214: Missing JSDoc on exported function ───────────────────────

def test_vc214_missing_jsdoc():
    src = "export function doStuff() {\n  return 1;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"lib.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC214" in codes


def test_vc214_has_jsdoc_ok():
    src = "/**\n * Does stuff.\n */\nexport function doStuff() {\n  return 1;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"lib.js": src})
        result = analyze_quality_js(infos, tmp)
    vc214 = [i for i in result.issues if i.code == "VC214"]
    assert len(vc214) == 0


# ── VC215: Use of var ───────────────────────────────────────────────

def test_vc215_var_detected():
    src = "var x = 1;\nvar y = 2;"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC215" in codes
    assert len([i for i in result.issues if i.code == "VC215"]) == 2


def test_vc215_let_const_ok():
    src = "let x = 1;\nconst y = 2;"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    vc215 = [i for i in result.issues if i.code == "VC215"]
    assert len(vc215) == 0


# ── VC216: Loose equality ───────────────────────────────────────────

def test_vc216_loose_equality():
    src = "if (x == y) {\n  return true;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC216" in codes


def test_vc216_strict_equality_ok():
    src = "if (x === y) {\n  return true;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    vc216 = [i for i in result.issues if i.code == "VC216"]
    assert len(vc216) == 0


# ── VC217: any type in TypeScript ───────────────────────────────────

def test_vc217_any_type_detected():
    src = "function foo(x: any): void {\n  return;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.ts": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC217" in codes


def test_vc217_not_triggered_for_js():
    src = "function foo(x: any): void {\n  return;\n}"
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    vc217 = [i for i in result.issues if i.code == "VC217"]
    assert len(vc217) == 0


# ── VC218: Callback hell ────────────────────────────────────────────

def test_vc218_callback_hell():
    src = (
        "function hell() {\n"
        "  fetch(url, function(res) {\n"
        "    res.json(function(data) {\n"
        "      process(data, function(result) {\n"
        "        save(result, function(ok) {\n"
        "          console.log(ok);\n"
        "        });\n"
        "      });\n"
        "    });\n"
        "  });\n"
        "}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    codes = [i.code for i in result.issues]
    assert "VC218" in codes


# ── Clean / messy overall ───────────────────────────────────────────

def test_clean_js_high_score():
    src = (
        "/**\n * Adds two numbers.\n */\n"
        "export function add(a, b) {\n  return a + b;\n}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"math.js": src})
        result = analyze_quality_js(infos, tmp)
    assert result.score >= 90


def test_messy_js_low_score():
    body = "\n".join(f"  var x{i} = {i};" for i in range(60))
    src = (
        f"function messy() {{\n{body}\n}}\n"
        "if (a == b) {}\n"
        "console.log('leak');\n"
        "export function noDoc() { return 1; }\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"app.js": src})
        result = analyze_quality_js(infos, tmp)
    assert result.score < 70


# ── Empty file ──────────────────────────────────────────────────────

def test_empty_file():
    with tempfile.TemporaryDirectory() as tmp:
        infos = _make_files(tmp, {"empty.js": ""})
        result = analyze_quality_js(infos, tmp)
    assert result.score == 100.0
    assert result.issues == []


# ── No JS files passed ─────────────────────────────────────────────

def test_no_js_files():
    result = analyze_quality_js([], "/tmp")
    assert result.score == 100.0
    assert result.issues == []
