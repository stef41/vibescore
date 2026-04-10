"""Generate GitHub Actions workflow that runs vibescore in CI."""

from __future__ import annotations


def generate_workflow(
    threshold: str = "C",
    python_version: str = "3.12",
    on_push: bool = True,
    on_pull_request: bool = True,
) -> str:
    """Generate a GitHub Actions workflow YAML string.

    Args:
        threshold: Minimum passing grade (A+, A, B, C, D, F).
        python_version: Python version to use.
        on_push: Run on push events.
        on_pull_request: Run on pull_request events.

    Returns:
        Complete workflow YAML as a string.
    """
    triggers = []
    if on_push:
        triggers.append("  push:\n    branches: [main, master]")
    if on_pull_request:
        triggers.append("  pull_request:")

    trigger_block = "\n".join(triggers)

    return f"""name: Vibe Check
on:
{trigger_block}

jobs:
  vibescore:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "{python_version}"
      - run: pip install vibescore
      - run: vibescore --threshold {threshold} .
"""
