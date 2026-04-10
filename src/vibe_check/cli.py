from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="vibe-check",
        description="\U0001f3b5 Grade your vibe-coded project",
    )
    parser.add_argument(
        "path", nargs="?", default=".", help="Project directory to scan (default: .)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=0,
        help="Exit with code 1 if overall score is below this threshold",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args(argv)

    path = args.path
    if not os.path.isdir(path):
        print(f"Error: '{path}' is not a directory", file=sys.stderr)
        return 1

    from .scanner import scan
    from .report import format_report, format_json

    report = scan(path)

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_report(report))

    if report.overall_score < args.min_score:
        return 1
    return 0


def _entry() -> None:
    """Wrapper for console_scripts entry-point."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
