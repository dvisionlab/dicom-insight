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
    parser.add_argument("--deep-context", action="store_true", help="Provide full metadata to the LLM (if used)")
    return parser



def main(argv: list[str] | None = None) -> int:
    import os
    parser = build_parser()
    args = parser.parse_args(argv)

    # Simple provider auto-discovery
    provider = None
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        from .llm import GeminiProvider
        provider = GeminiProvider(api_key=api_key)

    if args.json:
        # Don't show progress bar for JSON output to avoid polluting stdout
        report = analyze_path(args.path, provider=provider, deep_context=args.deep_context)
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

            report = analyze_path(args.path, on_progress=update_progress, provider=provider, deep_context=args.deep_context)

        print(report.summary)
        print()
        
        if report.ai_summary:
            from rich.panel import Panel
            print(Panel(report.ai_summary, title="[bold blue]AI Content Summary[/]", border_style="blue"))
            print()
        
        print(report.explanation)

        if report.technical_anomalies:
            print()
            print("[bold yellow]AI Technical Insights:[/]")
            for anomaly in report.technical_anomalies:
                print(f"- {anomaly}")

        if report.warnings:
            print()
            print("[bold red]Warnings:[/]")
            for warning in report.warnings:
                print(f"- {warning}")
    return 0



if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
