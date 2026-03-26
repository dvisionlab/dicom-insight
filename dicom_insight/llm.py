from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import DicomInsightReport


class GeminiError(Exception):
    """Raised when the Gemini API returns an error or is unreachable."""


class ExplanationProvider(Protocol):
    def explain(self, report: DicomInsightReport) -> str: ...
    def summarize(self, report: DicomInsightReport, deep_context: bool = False) -> str: ...
    def detect_anomalies(self, report: DicomInsightReport, deep_context: bool = False) -> list[str]: ...


@dataclass(slots=True)
class TemplateLLMProvider:
    """Small placeholder provider.

    This keeps the library functional without external APIs. It can be replaced
    with OpenAI / Azure / local models by implementing the same protocol.
    """

    style: str = "technical"

    def explain(self, report: DicomInsightReport) -> str:
        if report.series:
            s = report.series
            return (
                f"[{self.style}] {s.modality or 'Unknown'} series, "
                f"{s.image_count} instances, description={s.description!r}, "
                f"contrast={s.contrast_suspected}."
            )
        if report.study:
            st = report.study
            return (
                f"[{self.style}] Study with {len(st.series)} series and modalities "
                f"{', '.join(st.modalities) or 'unknown'}."
            )
        return f"[{self.style}] Empty report."

    def summarize(self, report: DicomInsightReport, deep_context: bool = False) -> str:
        return self.explain(report)

    def detect_anomalies(self, report: DicomInsightReport, deep_context: bool = False) -> list[str]:
        return []


@dataclass(slots=True)
class GeminiProvider:
    """Provider for Google Gemini models (2.0-flash, 3.1-pro, etc.)"""
    api_key: str
    model: str = "gemini-3.1-pro-preview"

    def _query_gemini(self, system_instruction: str, user_prompt: str) -> str:
        # This is a 'Lite' implementation using httpx to avoid heavy SDKs
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": user_prompt}]}]
        }
        try:
            resp = httpx.post(url, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise GeminiError(str(e)) from e

    def explain(self, report: DicomInsightReport) -> str:
        # Default behavior: basic explanation
        return self.summarize(report, deep_context=False)

    def summarize(self, report: DicomInsightReport, deep_context: bool = False) -> str:
        system = (
            "You are a Radiology Metadata Analyst. "
            "Provide a concise, clinical summary of the DICOM data provided. "
            "Format your response as a GitHub Markdown callout block: use '> [!NOTE]' "
            "when the study appears normal or unremarkable, or '> [!CAUTION]' when you "
            "identify potential issues, unexpected findings, or items requiring attention. "
            "Start the block immediately with the callout marker and keep the summary brief."
        )
        user = f"DICOM Metadata: {report.to_json()}"
        return self._query_gemini(system, user)

    def detect_anomalies(self, report: DicomInsightReport, deep_context: bool = False) -> list[str]:
        system = (
            "You are a PACS Quality Assurance specialist. "
            "Identify technical inconsistencies in the DICOM metadata. "
            "For each anomaly found, format it as a GitHub Markdown callout block using "
            "'> [!CAUTION]' for serious issues and '> [!NOTE]' for minor observations. "
            "Return one callout block per anomaly, separated by a blank line."
        )
        user = f"DICOM Metadata: {report.to_json()}"
        resp = self._query_gemini(system, user)
        # Split on blank lines to separate callout blocks; fall back to line-by-line
        blocks = [block.strip() for block in resp.split("\n\n") if block.strip()]
        if not blocks:
            blocks = [line.strip("- *").strip() for line in resp.splitlines() if line.strip()]
        return blocks

