"""Tests for Go quality analyser."""
from __future__ import annotations

import os
import tempfile

from vibescore._types import FileInfo
from vibescore.quality_go import analyze_quality_go


def _make_go_file(content: str, name: str = "main.go") -> tuple[str, str, FileInfo]:
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    fi = FileInfo(path=path, language="go", lines=content.count("\n") + 1, size_bytes=len(content))
    return tmpdir, path, fi


class TestGoQuality:
    def test_clean_code(self) -> None:
        code = '''\
package main

// Greet returns a greeting string.
func Greet(name string) string {
    return "Hello, " + name
}
'''
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        assert result.score >= 85.0

    def test_unchecked_errors(self) -> None:
        code = '''\
package main

import "os"

func process() {
    f, err := os.Open("file.txt")
    data, err := os.ReadFile("other.txt")
    buf, err := os.ReadFile("third.txt")
    _ = f
    _ = data
    _ = buf
}
'''
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC231" in codes

    def test_goroutine_leak(self) -> None:
        code = '''\
package main

func runAll() {
    go processA()
    go processB()
}
'''
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC232" in codes

    def test_long_function(self) -> None:
        lines = ["package main", "", "func longFunc() {"]
        lines += ["    x := 1"] * 55
        lines += ["}"]
        code = "\n".join(lines)
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC233" in codes

    def test_missing_doc_comment(self) -> None:
        code = '''\
package main

func ExportedFunc() {
}
'''
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC234" in codes

    def test_naked_returns(self) -> None:
        lines = ["package main", "", "func compute() (int, error) {"]
        for _ in range(5):
            lines.append("    return")
        lines.append("}")
        code = "\n".join(lines)
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC235" in codes

    def test_panic_in_library(self) -> None:
        code = '''\
package mylib

func Init() {
    panic("not implemented")
}
'''
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC237" in codes

    def test_panic_in_main_ok(self) -> None:
        code = '''\
package main

func main() {
    panic("fatal error")
}
'''
        tmpdir, _, fi = _make_go_file(code)
        result = analyze_quality_go([fi], tmpdir)
        codes = [i.code for i in result.issues]
        assert "VC237" not in codes

    def test_skip_test_files(self) -> None:
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "main_test.go")
        with open(path, "w") as f:
            f.write("package main\nfunc TestSomething() { panic(\"test\") }")
        fi = FileInfo(path=path, language="go", lines=2, size_bytes=50)
        result = analyze_quality_go([fi], tmpdir)
        assert result.issues == []

    def test_empty_file_list(self) -> None:
        result = analyze_quality_go([], "/tmp")
        assert result.score == 100.0
