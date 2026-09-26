"""dicom_insight: lightweight DICOM metadata interpreter.

The package focuses on making DICOM metadata easier to inspect and explain.
It provides:
- safe DICOM loading helpers
- structured summaries via dataclasses
- heuristic study explanations without external services
- optional hooks for LLM-powered explanations
"""

from importlib.metadata import PackageNotFoundError, version

from .api import analyze_file, analyze_path, explain_file, explain_path
from .models import DicomInsightReport, DicomSeriesReport, DicomStudyReport

__all__ = [
    "analyze_file",
    "analyze_path",
    "explain_file",
    "explain_path",
    "DicomInsightReport",
    "DicomSeriesReport",
    "DicomStudyReport",
]

try:
    __version__ = version("dicom-insight")
except PackageNotFoundError:  # pragma: no cover - package not installed
    __version__ = "0.0.0"
