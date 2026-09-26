from __future__ import annotations

from pathlib import Path

from dicom_insight import analyze_file, analyze_path
from dicom_insight.privacy import PHI_KEYWORDS, redact_report_for_llm


def test_phi_keywords_cover_direct_identifiers() -> None:
    for keyword in ("PatientName", "PatientID", "PatientBirthDate", "AccessionNumber"):
        assert keyword in PHI_KEYWORDS


def test_redact_report_for_llm_strips_series_raw_metadata(dicom_file: Path) -> None:
    report = analyze_file(dicom_file, deep_context=True)
    assert report.series is not None
    assert report.series.raw_metadata.get("PatientID") == "PID12345"  # sanity: it *was* collected

    redacted = redact_report_for_llm(report)
    assert "PatientID" not in redacted["series"]["raw_metadata"]
    assert "AccessionNumber" not in redacted["series"]["raw_metadata"]
    # Non-identifying fields survive
    assert redacted["series"]["modality"] == "CT"


def test_redact_report_for_llm_strips_study_level_fields(dicom_study_dir: Path) -> None:
    report = analyze_path(dicom_study_dir, deep_context=True)
    assert report.study is not None
    assert report.study.accession_number == "ACC00042"  # sanity

    redacted = redact_report_for_llm(report)
    assert redacted["study"]["accession_number"] is None
    assert "PatientID" not in redacted["study"]["raw_metadata"]
    for series in redacted["study"]["series"]:
        assert "PatientID" not in series["raw_metadata"]
    # Clinically useful, non-identifying fields are preserved for the LLM
    assert redacted["study"]["patient_sex"] == "M"


def test_redact_report_for_llm_without_deep_context_is_noop_safe(dicom_file: Path) -> None:
    report = analyze_file(dicom_file, deep_context=False)
    redacted = redact_report_for_llm(report)
    assert redacted["series"]["raw_metadata"] == {}
