from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
import json


@dataclass(slots=True)
class DicomSeriesReport:
    series_instance_uid: str | None
    series_number: int | None
    description: str | None
    modality: str | None
    body_part_examined: str | None
    laterality: str | None
    image_count: int
    rows: int | None
    columns: int | None
    pixel_spacing: list[float] | None
    slice_thickness: float | None
    spacing_between_slices: float | None
    contrast_suspected: bool | None
    orientation: str | None
    warnings: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DicomStudyReport:
    study_instance_uid: str | None
    study_description: str | None
    accession_number: str | None
    study_date: str | None
    modalities: list[str]
    body_parts: list[str]
    patient_sex: str | None
    patient_age: str | None
    series: list[DicomSeriesReport]
    warnings: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DicomInsightReport:
    source: str
    kind: str
    study: DicomStudyReport | None = None
    series: DicomSeriesReport | None = None
    summary: str = ""
    explanation: str = ""
    ai_summary: str | None = None
    technical_anomalies: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
