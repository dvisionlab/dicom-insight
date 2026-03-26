"""Markdown formatting helpers for dicom-insight CLI output."""
from __future__ import annotations

import os
from typing import Any

from tabulate import tabulate

from .models import DicomInsightReport, DicomSeriesReport, DicomStudyReport


def format_report_header(folder_name: str) -> str:
    """Return a top-level Markdown header for the report."""
    return f"# DICOM Insight Report - {folder_name}"


def format_series_table(series_list: list[DicomSeriesReport]) -> str:
    """Return a GitHub-flavoured Markdown table summarizing each series."""
    rows = []
    for s in series_list:
        series_num = str(s.series_number) if s.series_number is not None else "-"
        description = s.description or "-"
        modality = s.modality or "-"
        instances = str(s.image_count)
        thickness = f"{s.slice_thickness:g} mm" if s.slice_thickness is not None else "-"
        spacing_parts: list[str] = []
        if s.pixel_spacing:
            spacing_parts.append(f"{s.pixel_spacing[0]:g}×{s.pixel_spacing[1]:g} mm")
        if s.spacing_between_slices is not None:
            spacing_parts.append(f"(z: {s.spacing_between_slices:g} mm)")
        spacing = " ".join(spacing_parts) if spacing_parts else "-"
        kernel = s.kernel or "-"
        rows.append([series_num, description, modality, instances, thickness, spacing, kernel])

    headers = ["Series #", "Description", "Modality", "Instances", "Slice Thickness", "Spacing", "Kernel"]
    return tabulate(rows, headers=headers, tablefmt="github")


def format_tags_table(raw_metadata: dict[str, Any]) -> str:
    """Return a GitHub-flavoured Markdown table of raw DICOM tag key/value pairs."""
    rows = [[key, str(value)] for key, value in sorted(raw_metadata.items())]
    headers = ["Tag / Keyword", "Value"]
    return tabulate(rows, headers=headers, tablefmt="github")


def format_markdown_report(report: DicomInsightReport, show_tags: bool = False) -> str:
    """Render the full DicomInsightReport as a Markdown string."""
    lines: list[str] = []

    # --- Header (folder/study level) ---
    source_path = report.source
    if os.path.isdir(source_path):
        folder_name = os.path.basename(os.path.abspath(source_path))
        lines.append(format_report_header(folder_name))
        lines.append("")

    # --- Summary line ---
    lines.append(f"**{report.summary}**")
    lines.append("")

    # --- AI Content Summary (from LLM) ---
    if report.ai_summary:
        lines.append(report.ai_summary)
        lines.append("")

    # --- Series table ---
    series_list: list[DicomSeriesReport] = []
    if report.study:
        series_list = report.study.series
    elif report.series:
        series_list = [report.series]

    if series_list:
        lines.append("## Series")
        lines.append("")
        lines.append(format_series_table(series_list))
        lines.append("")

    # --- Explanation text ---
    lines.append("## Details")
    lines.append("")
    lines.append(report.explanation)
    lines.append("")

    # --- AI Technical Insights ---
    if report.technical_anomalies:
        lines.append("## AI Technical Insights")
        lines.append("")
        for anomaly in report.technical_anomalies:
            # Anomalies may already be Markdown callout blocks (e.g. "> [!CAUTION]")
            # produced by the LLM; emit them verbatim, not as list items.
            lines.append(anomaly)
            lines.append("")

    # --- Warnings ---
    if report.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in report.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    # --- Tag detail tables (opt-in) ---
    if show_tags:
        lines.append("## Tag Detail")
        lines.append("")
        if report.study:
            for s in report.study.series:
                if s.raw_metadata:
                    title = s.description or s.series_instance_uid or "Series"
                    lines.append(f"### {title}")
                    lines.append("")
                    lines.append(format_tags_table(s.raw_metadata))
                    lines.append("")
        elif report.series and report.series.raw_metadata:
            lines.append(format_tags_table(report.series.raw_metadata))
            lines.append("")

    return "\n".join(lines)
