# 🎵 vibescore

**Grade your vibe-coded project. One command. Instant letter grade.**

[![PyPI](https://img.shields.io/pypi/v/vibescore?color=blue)](https://pypi.org/project/vibescore/)
[![Downloads](https://img.shields.io/pypi/dm/vibescore)](https://pypi.org/project/vibescore/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/vibescore)](https://pypi.org/project/vibescore/)
[![CI](https://github.com/stef41/vibescore/actions/workflows/ci.yml/badge.svg)](https://github.com/stef41/vibescore/actions)
[![Tests](https://img.shields.io/badge/tests-201%20passed-brightgreen)]()

> "Vibe coding" is the new reality — you prompt, AI writes, you ship.  
> But **is your vibe-coded project actually good?**  
> Find out in 10 seconds.

```
$ vibescore .

🎵 Vibe Check  v0.1.0
══════════════════════════════════════════════

  Project:   tokonomics
  Files:     40 (32 Python, 8 other)
  Lines:     4,658
  Scanned in 0.12s

┌──────────────────┬────────┬───────┐
│ Category         │ Score  │ Grade │
├──────────────────┼────────┼───────┤
│ Code Quality     │   52.0 │ F     │
│ Security         │  100.0 │ A+    │
│ Dependencies     │   98.0 │ A+    │
│ Testing          │  100.0 │ A+    │
├──────────────────┼────────┼───────┤
│ Overall          │   87.6 │ B+    │
└──────────────────┴────────┴───────┘

🟡 Warnings (11)
  VC201  Function 'export_svg_chart' too long (102 lines)
  VC202  Function '_build_cli' high complexity (30)
  VC203  Function 'export_svg_chart' has 6 parameters (>5)
  ...

💡 Tips
  • Reduce function complexity and add type annotations
```

## Install

```bash
pip install vibescore
```

That's it. Zero dependencies. Works with Python 3.9+.

## Usage

```bash
# Grade the current directory
vibescore .

# Grade a specific project
vibescore /path/to/project

# JSON output (for CI pipelines)
vibescore . --format json

# Fail CI if score is below threshold
vibescore . --min-score 70
```

### As a Python library

```python
from vibescore import scan

report = scan(".")
print(f"Grade: {report.overall_grade} ({report.overall_score:.0f}/100)")

for category in report.categories:
    print(f"  {category.name}: {category.grade}")
```

## What It Checks

| Category | Checks | Codes |
|----------|--------|-------|
| **Code Quality** | Function length, cyclomatic complexity, parameter count, type annotations, nesting depth, star imports, docstrings, mutable defaults | VC201–VC209 |
| **Security** | Hardcoded secrets, AWS keys, SQL injection, shell injection, unsafe deserialization, eval/exec, debug mode, private keys | VC301–VC309 |
| **Dependencies** | Version pinning, lock files, deprecated setup.py, wildcard pins | VC401–VC405 |
| **Testing** | Test file presence, test count, CI configuration, conftest.py, test-to-code ratio | VC501–VC506 |

## Grading Scale

| Grade | Score | Grade | Score |
|-------|-------|-------|-------|
| A+    | 97–100 | C+   | 77–79 |
| A     | 93–96  | C    | 73–76 |
| A-    | 90–92  | C-   | 70–72 |
| B+    | 87–89  | D+   | 67–69 |
| B     | 83–86  | D    | 63–66 |
| B-    | 80–82  | D-   | 60–62 |
|       |        | F    | 0–59  |

## CI Integration

### GitHub Actions

```yaml
- name: Vibe Check
  run: |
    pip install vibescore
    vibescore . --min-score 70
```

### Pre-commit (manual)

```bash
# In your Makefile or CI script
vibescore . --min-score 70 --format json > vibe-report.json
```

### Pre-commit

```yaml
repos:
  - repo: https://github.com/stef41/vibescore
    rev: v0.1.0
    hooks:
      - id: vibescore
        args: ["--min-score", "70"]
```

## How Scoring Works

Each category is scored 0–100 independently. The overall score is a weighted average:

| Category | Weight |
|----------|--------|
| Security | 30% |
| Code Quality | 25% |
| Testing | 25% |
| Dependencies | 20% |

Security is weighted highest because a security bug in vibe-coded projects can be catastrophic.

## Why vibescore?

Vibe coding means AI writes most of your code. That's fast, but it introduces risks:

- **AI hallucinates long functions** that are hard to debug
- **AI skips security basics** like input validation and secret management
- **AI often omits tests** or writes superficial ones
- **AI uses loose dependency pins** that break on updates

`vibescore` catches these patterns in seconds, so you can ship fast *and* ship safe.

## FAQ

**Q: Does this only work with Python?**  
A: Currently Python-focused for code quality and testing analysis. Security and dependency checks work with any project type. More languages coming soon.

**Q: Does it phone home or require an API key?**  
A: No. Zero network requests. Zero dependencies. Runs entirely offline.

**Q: How is this different from pylint/ruff/flake8?**  
A: Those are line-level linters. `vibescore` gives you a project-level grade across security, quality, testing, and dependencies — a holistic view of your vibe-coded project's health. Use both.

## See Also

Tools in the same ecosystem:

- [tokonomics](https://github.com/stef41/tokonomix) — LLM token cost management
- [injectionguard](https://github.com/stef41/injectionguard) — Prompt injection detection
- [vibesafe](https://github.com/stef41/vibesafex) — AI code safety scanner
- [castwright](https://github.com/stef41/castwright) — Synthetic training data generator
- [infermark](https://github.com/stef41/infermark) — LLM inference benchmarking

## License

Apache-2.0
