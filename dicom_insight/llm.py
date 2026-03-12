from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import DicomInsightReport


class ExplanationProvider(Protocol):
    def explain(self, report: DicomInsightReport) -> str: ...


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
