from __future__ import annotations

from pathlib import Path

from .explainer import explain_series, explain_study, make_summary
from .heuristics import summarize_series, summarize_study
from .llm import ExplanationProvider
from .models import DicomInsightReport
from .reader import iter_dicom_files, load_dataset
from typing import Callable



def analyze_file(path: str | Path, provider: ExplanationProvider | None = None) -> DicomInsightReport:
    ds = load_dataset(path)
    series_report = summarize_series([ds])
    report = DicomInsightReport(source=str(path), kind="file", series=series_report)
    report.summary = make_summary(report)
    report.explanation = provider.explain(report) if provider else explain_series(series_report)
    report.warnings = list(series_report.warnings)
    return report



def analyze_path(
    path: str | Path, 
    provider: ExplanationProvider | None = None,
    on_progress: Callable[[int, int], None] | None = None
) -> DicomInsightReport:
    path_obj = Path(path)
    if path_obj.is_file():
        return analyze_file(path_obj, provider=provider)

    # Collect files to get total count for progress reporting
    files = list(iter_dicom_files(path_obj))
    total = len(files)
    
    if not files:
        raise FileNotFoundError(f"No readable DICOM files found in {path_obj}")

    datasets = []
    seen = 0
    for i, file_path in enumerate(files):
        try:
            datasets.append(load_dataset(file_path))
            seen += 1
        except Exception:
            continue
        
        if on_progress:
            on_progress(i + 1, total)

    if not datasets:
        raise FileNotFoundError(f"No readable DICOM files found in {path_obj}")

    study_report = summarize_study(datasets)
    report = DicomInsightReport(source=str(path), kind="path", study=study_report)
    report.summary = make_summary(report)
    report.explanation = provider.explain(report) if provider else explain_study(study_report)
    report.warnings = list(study_report.warnings)
    if seen != len(datasets):
        report.warnings.append("Some files could not be parsed")
    return report



def explain_file(path: str | Path, provider: ExplanationProvider | None = None) -> str:
    return analyze_file(path, provider=provider).explanation



def explain_path(path: str | Path, provider: ExplanationProvider | None = None) -> str:
    return analyze_path(path, provider=provider).explanation
