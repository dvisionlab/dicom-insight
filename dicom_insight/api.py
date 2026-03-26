from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .explainer import explain_anatomy_heuristic, explain_series, explain_study, make_summary
from .heuristics import summarize_series, summarize_study
from .llm import ExplanationProvider, GeminiError
from .models import DicomInsightReport
from .reader import iter_dicom_files, load_dataset
from typing import Callable



def _apply_provider(
    report: DicomInsightReport,
    provider: ExplanationProvider,
    deep_context: bool,
) -> bool:
    """Call the LLM provider and populate the report's AI fields.

    Returns True on success, False when the provider raises a GeminiError
    so the caller can fall back to heuristic output and add a warning.
    """
    try:
        report.explanation = provider.explain(report)
        report.ai_summary = provider.summarize(report, deep_context=deep_context)
        report.technical_anomalies = provider.detect_anomalies(report, deep_context=deep_context)
        report.anatomy_analysis = provider.analyze_anatomy(report)
        return True
    except GeminiError as exc:
        report.warnings.append(f"LLM analysis unavailable: {exc}")
        return False



def analyze_file(
    path: str | Path, 
    provider: ExplanationProvider | None = None,
    deep_context: bool = False
) -> DicomInsightReport:
    ds = load_dataset(path)
    series_report = summarize_series([ds], include_raw=deep_context)
    report = DicomInsightReport(source=str(path), kind="file", series=series_report)
    report.summary = make_summary(report)
    
    if provider:
        if not _apply_provider(report, provider, deep_context):
            report.explanation = explain_series(series_report)
            report.anatomy_analysis = explain_anatomy_heuristic(report)
    else:
        report.explanation = explain_series(series_report)
        report.anatomy_analysis = explain_anatomy_heuristic(report)

    # Merge heuristic warnings; preserve any LLM-failure warning already in report.warnings
    for w in series_report.warnings:
        if w not in report.warnings:
            report.warnings.append(w)
    return report



def analyze_path(
    path: str | Path, 
    provider: ExplanationProvider | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    deep_context: bool = False
) -> DicomInsightReport:
    path_obj = Path(path)
    if path_obj.is_file():
        return analyze_file(path_obj, provider=provider, deep_context=deep_context)

    # Collect files to get total count for progress reporting
    files = list(iter_dicom_files(path_obj))
    total = len(files)
    
    if not files:
        raise FileNotFoundError(f"No readable DICOM files found in {path_obj}")

    progress_count = 0
    progress_lock = threading.Lock()

    def _load(file_path: Path):
        nonlocal progress_count
        result = None
        try:
            result = load_dataset(file_path)
        except Exception:
            pass
        with progress_lock:
            progress_count += 1
            if on_progress:
                on_progress(progress_count, total)
        return result

    with ThreadPoolExecutor(max_workers=min(len(files), 64)) as executor:
        results = list(executor.map(_load, files))

    datasets = [r for r in results if r is not None]
    seen = len(datasets)

    if not datasets:
        raise FileNotFoundError(f"No readable DICOM files found in {path_obj}")

    study_report = summarize_study(datasets, include_raw=deep_context)
    report = DicomInsightReport(source=str(path), kind="path", study=study_report)
    report.summary = make_summary(report)
    
    if provider:
        if not _apply_provider(report, provider, deep_context):
            report.explanation = explain_study(study_report)
            report.anatomy_analysis = explain_anatomy_heuristic(report)
    else:
        report.explanation = explain_study(study_report)
        report.anatomy_analysis = explain_anatomy_heuristic(report)

    # Merge heuristic warnings; preserve any LLM-failure warning already in report.warnings
    for w in study_report.warnings:
        if w not in report.warnings:
            report.warnings.append(w)
    if seen != len(files):
        report.warnings.append("Some files could not be parsed")
    return report




def explain_file(path: str | Path, provider: ExplanationProvider | None = None) -> str:
    return analyze_file(path, provider=provider).explanation



def explain_path(path: str | Path, provider: ExplanationProvider | None = None) -> str:
    return analyze_path(path, provider=provider).explanation
