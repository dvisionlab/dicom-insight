"""Helpers to keep direct patient/institution identifiers away from third-party LLMs.

`dicom_insight` can optionally send report data to a cloud LLM provider (see
`dicom_insight.llm.GeminiProvider`). DICOM headers routinely carry Protected
Health Information (PHI): patient name, patient ID, birth date, accession
number, referring physician, etc. This module strips the tags that most
directly identify a patient or a care episode before any payload leaves the
process, independently of what is shown locally (e.g. via ``--tags``).
"""

from __future__ import annotations

import re
from typing import Any

from .models import DicomInsightReport

# Matches the "(GGGG,EEEE)" fallback key that dataset_to_dict_safe() uses when
# a tag has no pydicom keyword — true of any private/vendor tag. Private tags
# are a common place for vendors to stash patient- or site-identifying data,
# so they are dropped wholesale rather than allow-listed tag by tag.
_UNNAMED_TAG_RE = re.compile(r"^\([0-9A-Fa-f]{4},[0-9A-Fa-f]{4}\)$")

# DICOM keywords that directly identify a patient, an episode of care, or the
# staff/institution involved. This is intentionally conservative (favouring
# over-redaction) rather than an exhaustive de-identification profile such as
# DICOM PS3.15 Annex E — it is not a substitute for a proper de-identification
# pipeline when handling real patient data.
PHI_KEYWORDS: frozenset[str] = frozenset(
    {
        "PatientName",
        "PatientID",
        "PatientBirthDate",
        "PatientBirthTime",
        "PatientAddress",
        "PatientTelephoneNumbers",
        "PatientMotherBirthName",
        "OtherPatientIDs",
        "OtherPatientNames",
        "OtherPatientIDsSequence",
        "IssuerOfPatientID",
        "AccessionNumber",
        "InstitutionName",
        "InstitutionAddress",
        "InstitutionalDepartmentName",
        "ReferringPhysicianName",
        "RequestingPhysician",
        "PerformingPhysicianName",
        "OperatorsName",
        "StationName",
        "PersonName",
    }
)

# Top-level report fields (outside of raw_metadata) that are also considered
# direct identifiers and get redacted alongside the raw tag dump.
_STUDY_LEVEL_PHI_FIELDS = ("accession_number",)


def _redact_raw_metadata(raw_metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in raw_metadata.items()
        if key not in PHI_KEYWORDS and not _UNNAMED_TAG_RE.match(key)
    }


def redact_report_for_llm(report: DicomInsightReport) -> dict[str, Any]:
    """Return a JSON-serialisable dict of `report`, stripped of direct identifiers.

    This is what must be sent to any external LLM provider — never
    `report.to_dict()` / `report.to_json()` directly, which include the full
    (unredacted) raw metadata tag dump when `deep_context=True`.
    """
    data = report.to_dict()

    # The input file/folder path is user-controlled and can itself carry
    # identifiers (e.g. an export named after a patient); never forward it.
    data["source"] = None

    if data.get("study") is not None:
        for field_name in _STUDY_LEVEL_PHI_FIELDS:
            data["study"][field_name] = None
        data["study"]["raw_metadata"] = _redact_raw_metadata(data["study"].get("raw_metadata") or {})
        for series in data["study"].get("series", []):
            series["raw_metadata"] = _redact_raw_metadata(series.get("raw_metadata") or {})

    if data.get("series") is not None:
        data["series"]["raw_metadata"] = _redact_raw_metadata(data["series"].get("raw_metadata") or {})

    return data
