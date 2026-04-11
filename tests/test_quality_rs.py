"""Tests for Rust quality analyser."""
from __future__ import annotations

import os
import tempfile

from vibescore._types import FileInfo
from vibescore.quality_rs import analyze_quality_rs


def _make_rs_file(content: str) -> tuple[str, str, FileInfo]:
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "main.rs")
    with open(path, "w") as f:
        f.write(content)
    fi = FileInfo(path=path, language="rust", lines=content.count("\n") + 1, size_bytes=len(content))
    return tmpdir, path, fi


class TestRustQuality:
    def test_clean_code(self) -> None:
        code = '''\
/// A simple greeting function.
pub fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}
'''
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        assert result.score >= 90.0
        assert result.grade in ("A+", "A", "A-")

    def test_unwrap_detection(self) -> None:
        code = '''\
fn process() {
    let a = "123".parse::<i32>().unwrap();
    let b = "456".parse::<i32>().unwrap();
    let c = "789".parse::<i32>().unwrap();
    let d = some_fn().unwrap();
    let e = other_fn().unwrap();
    let f = third_fn().unwrap();
}
'''
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC221" in codes

    def test_unsafe_detection(self) -> None:
        code = '''\
fn dangerous() {
    unsafe {
        let ptr = 0 as *const i32;
    }
}
'''
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC222" in codes

    def test_long_function(self) -> None:
        lines = ["fn long_fn() {"] + ["    let x = 1;"] * 55 + ["}"]
        code = "\n".join(lines)
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC223" in codes

    def test_missing_doc_comment(self) -> None:
        code = '''\
use std::io;

pub fn undocumented() -> i32 {
    42
}
'''
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC224" in codes

    def test_clone_detection(self) -> None:
        lines = ["fn clone_heavy() {"]
        for i in range(12):
            lines.append(f"    let x{i} = data.clone();")
        lines.append("}")
        code = "\n".join(lines)
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC225" in codes

    def test_todo_macro(self) -> None:
        code = '''\
fn incomplete() {
    todo!("implement this")
}
'''
        tmpdir, _, fi = _make_rs_file(code)
        result = analyze_quality_rs([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC226" in codes

    def test_skip_test_files(self) -> None:
        tmpdir = tempfile.mkdtemp()
        test_dir = os.path.join(tmpdir, "tests")
        os.makedirs(test_dir)
        path = os.path.join(test_dir, "test_main.rs")
        with open(path, "w") as f:
            f.write("fn test_something() { panic!(); let x = bad.unwrap(); }")
        fi = FileInfo(path=path, language="rust", lines=1, size_bytes=50)
        result = analyze_quality_rs([fi], tmpdir)
        assert result.issues == []

    def test_empty_file_list(self) -> None:
        result = analyze_quality_rs([], "/tmp")
        assert result.score == 100.0
        assert result.grade == "A+"
