# Contributing to vibescore

Thanks for your interest! vibescore grades vibe-coded projects and we welcome contributions.

## Quick Start

```bash
git clone https://github.com/stef41/vibescore.git
cd vibescore
pip install -e .
python -m pytest tests/ -q
```

## What We're Looking For

- **New language analyzers** — Rust, Go, Java, Ruby (see `src/vibescore/quality.py` for the pattern)
- **New security checks** — More vulnerability patterns to detect
- **Bug reports** — Projects that get unfair grades
- **Documentation** — Tutorials, CI integration guides

## Running Tests

```bash
python -m pytest tests/ -q  # 175 tests must pass
ruff check src/ tests/
```

## Pull Request Process

1. Fork → branch → change → test → PR
2. All tests must pass
3. We review within 48 hours
