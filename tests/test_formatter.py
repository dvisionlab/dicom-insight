from __future__ import annotations

from pathlib import Path

from dicom_insight import analyze_file, analyze_path
from dicom_insight.formatter import (
    format_markdown_report,
    format_report_header,
    format_series_table,
    format_tags_table,
)


def test_format_report_header() -> None:
    assert format_report_header("my_study") == "# DICOM Insight Report - my_study"


def test_format_tags_table_sorted_and_stringified() -> None:
    table = format_tags_table({"PatientSex": "M", "BodyPartExamined": "HEAD"})
    lines = table.splitlines()
    # BodyPartExamined sorts before PatientSex
    assert "BodyPartExamined" in lines[2]
    assert "PatientSex" in lines[3]


def test_format_series_table_includes_series_fields(dicom_file: Path) -> None:
    report = analyze_file(dicom_file)
    assert report.series is not None
    table = format_series_table([report.series])
    assert "CT" in table
    assert "HEAD W/O CONTRAST" in table


def test_format_markdown_report_file_without_tags(dicom_file: Path) -> None:
    report = analyze_file(dicom_file)
    md = format_markdown_report(report, show_tags=False)
    assert "## Details" in md
    assert "## Tag Detail" not in md


def test_format_markdown_report_path_with_tags(dicom_study_dir: Path) -> None:
    report = analyze_path(dicom_study_dir, deep_context=True)
    md = format_markdown_report(report, show_tags=True)
    assert format_report_header(dicom_study_dir.name) in md
    assert "## Series" in md
    assert "## Tag Detail" in md


def test_format_markdown_report_includes_warnings(dicom_file: Path) -> None:
    report = analyze_file(dicom_file)
    report.warnings.append("Something looks off")
    md = format_markdown_report(report)
    assert "## Warnings" in md
    assert "- Something looks off" in md
