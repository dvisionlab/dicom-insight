from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .api import analyze_path



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dicom-insight",
        description="Explain DICOM metadata in a structured and human-readable way.",
    )
    parser.add_argument("path", type=Path, help="Path to a DICOM file or folder")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser



def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.json:
        # Don't show progress bar for JSON output to avoid polluting stdout
        report = analyze_path(args.path)
        print(report.to_json())
    else:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Reading DICOM files...", total=None)

            def update_progress(current: int, total: int):
                progress.update(task, completed=current, total=total, description=f"Reading DICOM files ({current}/{total})")

            report = analyze_path(args.path, on_progress=update_progress)

        print(report.summary)
        print()
        print(report.explanation)
        if report.warnings:
            print()
            print("Warnings:")
            for warning in report.warnings:
                print(f"- {warning}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
