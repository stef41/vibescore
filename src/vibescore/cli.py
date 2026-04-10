from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="vibescore",
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
        "--threshold",
        default=None,
        help="Minimum passing grade (A+, A, B, C, D, F)",
    )
    parser.add_argument(
        "--init-ci",
        action="store_true",
        help="Generate a GitHub Actions workflow at .github/workflows/vibescore.yml",
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Watch for file changes and re-scan automatically",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args(argv)

    # --init-ci: generate workflow and exit
    if args.init_ci:
        from .actions import generate_workflow

        threshold = args.threshold or "C"
        workflow = generate_workflow(threshold=threshold)
        workflow_dir = os.path.join(args.path, ".github", "workflows")
        os.makedirs(workflow_dir, exist_ok=True)
        workflow_path = os.path.join(workflow_dir, "vibescore.yml")
        with open(workflow_path, "w") as f:
            f.write(workflow)
        print(f"Created {workflow_path}")
        print("Commit this file to enable vibescore in CI.")
        return 0

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
        try:
            from .report import format_report_rich
            output = format_report_rich(report)
        except ImportError:
            output = format_report(report)
        print(output)

    if report.overall_score < args.min_score:
        return 1

    # --watch: enter watch loop
    if args.watch:
        import datetime
        from .watch import watch as _watch

        def _on_change(fpath: str) -> None:
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] File changed: {fpath} \u2192 re-scanning...")
            r = scan(path)
            if args.format == "json":
                print(format_json(r))
            else:
                try:
                    from .report import format_report_rich
                    print(format_report_rich(r))
                except ImportError:
                    print(format_report(r))

        print("\n\U0001f440 Watching for changes... (Ctrl+C to stop)")
        try:
            _watch(path, _on_change)
        except KeyboardInterrupt:
            print("\nStopped watching.")

    return 0


def _entry() -> None:
    """Wrapper for console_scripts entry-point."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
