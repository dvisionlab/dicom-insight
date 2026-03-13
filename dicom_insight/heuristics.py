from __future__ import annotations

from collections import Counter
from typing import Iterable

from pydicom.dataset import Dataset

from .models import DicomSeriesReport, DicomStudyReport


CONTRAST_KEYWORDS = {
    "C+",
    "POST CONTRAST",
    "WITH CONTRAST",
    "CONTRAST",
    "ANGIO",
    "CTA",
    "MRA",
    "CE",
}

ORIENTATION_LABELS = {
    (1, 0, 0, 0, 1, 0): "axial",
    (1, 0, 0, 0, 0, -1): "coronal",
    (0, 1, 0, 0, 0, -1): "sagittal",
}



def _get_str(ds: Dataset, name: str) -> str | None:
    value = getattr(ds, name, None)
    if value in (None, ""):
        return None
    return str(value)



def _get_int(ds: Dataset, name: str) -> int | None:
    value = getattr(ds, name, None)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None



def _get_float(ds: Dataset, name: str) -> float | None:
    value = getattr(ds, name, None)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None



def _get_float_list(ds: Dataset, name: str) -> list[float] | None:
    value = getattr(ds, name, None)
    if value in (None, ""):
        return None
    try:
        return [float(x) for x in value]
    except Exception:
        return None



def guess_orientation(ds: Dataset) -> str | None:
    values = getattr(ds, "ImageOrientationPatient", None)
    if not values:
        return None
    try:
        rounded = tuple(int(round(float(x))) for x in values)
    except Exception:
        return None
    return ORIENTATION_LABELS.get(rounded)



def guess_contrast(ds: Dataset) -> bool | None:
    for attr in ("SeriesDescription", "ProtocolName", "StudyDescription"):
        text = _get_str(ds, attr)
        if text:
            upper = text.upper()
            if any(keyword in upper for keyword in CONTRAST_KEYWORDS):
                return True
    contrast_agent = _get_str(ds, "ContrastBolusAgent")
    if contrast_agent:
        return True
    modality = _get_str(ds, "Modality")
    if modality in {"XA", "RF", "NM", "PT"}:
        return None
    return False



def dataset_to_dict_safe(ds: Dataset) -> dict[str, Any]:
    """Convert dataset to a dict of string/numeric tags, skipping binary/pixels."""
    out = {}
    for elem in ds:
        if elem.VR in ("OB", "OW", "OF", "OD", "UN", "SQ"):
            continue
        try:
            val = elem.value
            if isinstance(val, (str, int, float)):
                out[elem.keyword or f"({elem.tag.group:04X},{elem.tag.element:04X})"] = val
            elif isinstance(val, list) and all(isinstance(x, (str, int, float)) for x in val):
                out[elem.keyword or f"({elem.tag.group:04X},{elem.tag.element:04X})"] = val
        except Exception:
            continue
    return out



def summarize_series(datasets: Iterable[Dataset], include_raw: bool = False) -> DicomSeriesReport:
    items = list(datasets)
    if not items:
        raise ValueError("Cannot summarize an empty series")

    first = items[0]
    warnings: list[str] = []

    rows = _get_int(first, "Rows")
    cols = _get_int(first, "Columns")
    slice_thickness = _get_float(first, "SliceThickness")
    spacing_between_slices = _get_float(first, "SpacingBetweenSlices")
    modality = _get_str(first, "Modality")
    pixel_spacing = _get_float_list(first, "PixelSpacing")
    body_part = _get_str(first, "BodyPartExamined")

    if rows is None or cols is None:
        warnings.append("Missing image dimensions")
    if modality is None:
        warnings.append("Missing modality")

    report = DicomSeriesReport(
        series_instance_uid=_get_str(first, "SeriesInstanceUID"),
        series_number=_get_int(first, "SeriesNumber"),
        description=_get_str(first, "SeriesDescription"),
        modality=modality,
        body_part_examined=body_part,
        laterality=_get_str(first, "Laterality"),
        image_count=len(items),
        rows=rows,
        columns=cols,
        pixel_spacing=pixel_spacing,
        slice_thickness=slice_thickness,
        spacing_between_slices=spacing_between_slices,
        contrast_suspected=guess_contrast(first),
        orientation=guess_orientation(first),
        warnings=warnings,
    )
    if include_raw:
        # Full first instance metadata as representative
        report.raw_metadata = dataset_to_dict_safe(first)
    return report



def summarize_study(datasets: Iterable[Dataset], include_raw: bool = False) -> DicomStudyReport:
    items = list(datasets)
    if not items:
        raise ValueError("Cannot summarize an empty study")

    first = items[0]
    by_series: dict[str, list[Dataset]] = {}
    for ds in items:
        key = _get_str(ds, "SeriesInstanceUID") or f"__series_{len(by_series)+1}"
        by_series.setdefault(key, []).append(ds)

    series_reports = [summarize_series(group, include_raw=include_raw) for group in by_series.values()]
    modalities = sorted({s.modality for s in series_reports if s.modality})
    body_parts = sorted({s.body_part_examined for s in series_reports if s.body_part_examined})
    warnings: list[str] = []

    if len(modalities) > 1:
        warnings.append("Study contains multiple modalities")

    patient_sexes = Counter(_get_str(ds, "PatientSex") for ds in items if _get_str(ds, "PatientSex"))
    patient_sex = patient_sexes.most_common(1)[0][0] if patient_sexes else None

    patient_ages = Counter(_get_str(ds, "PatientAge") for ds in items if _get_str(ds, "PatientAge"))
    patient_age = patient_ages.most_common(1)[0][0] if patient_ages else None

    report = DicomStudyReport(
        study_instance_uid=_get_str(first, "StudyInstanceUID"),
        study_description=_get_str(first, "StudyDescription"),
        accession_number=_get_str(first, "AccessionNumber"),
        study_date=_get_str(first, "StudyDate"),
        modalities=modalities,
        body_parts=body_parts,
        patient_sex=patient_sex,
        patient_age=patient_age,
        series=sorted(series_reports, key=lambda s: (s.series_number or 0, s.description or "")),
        warnings=warnings,
    )
    if include_raw:
        # Study-level tags are often constant in the first dataset
        # We also collect common hints specifically
        report.raw_metadata = dataset_to_dict_safe(first)
    return report

