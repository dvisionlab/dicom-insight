from __future__ import annotations

from .models import DicomInsightReport, DicomSeriesReport, DicomStudyReport



def _human_body_part(body_part: str | None) -> str | None:
    if not body_part:
        return None
    mapping = {
        "CHEST": "chest",
        "HEAD": "head",
        "BRAIN": "brain",
        "ABDOMEN": "abdomen",
        "ABDOMENPELVIS": "abdomen and pelvis",
        "SPINE": "spine",
        "KNEE": "knee",
        "SHOULDER": "shoulder",
    }
    return mapping.get(body_part.upper(), body_part.lower().replace("_", " "))



def explain_series(series: DicomSeriesReport) -> str:
    parts: list[str] = []
    modality = series.modality or "Unknown modality"
    body_part = _human_body_part(series.body_part_examined)

    intro = modality
    if body_part:
        intro += f" series of the {body_part}"
    else:
        intro += " imaging series"
    parts.append(intro)

    if series.description:
        parts.append(f"Series description: {series.description}.")

    geometry: list[str] = []
    if series.image_count:
        geometry.append(f"{series.image_count} instance{'s' if series.image_count != 1 else ''}")
    if series.rows and series.columns:
        geometry.append(f"matrix {series.rows}×{series.columns}")
    if series.slice_thickness is not None:
        geometry.append(f"slice thickness {series.slice_thickness:g} mm")
    if geometry:
        parts.append("Acquisition summary: " + ", ".join(geometry) + ".")

    if series.orientation:
        parts.append(f"Likely viewing plane: {series.orientation}.")

    if series.contrast_suspected is True:
        parts.append("The metadata suggests a contrast-enhanced acquisition.")
    elif series.contrast_suspected is False:
        parts.append("No clear sign of contrast usage was found in the available metadata.")

    if series.warnings:
        parts.append("Warnings: " + "; ".join(series.warnings) + ".")

    return " ".join(parts)



def explain_study(study: DicomStudyReport) -> str:
    parts: list[str] = []
    modality_text = ", ".join(study.modalities) if study.modalities else "unknown modality"
    parts.append(f"This study contains {len(study.series)} series across modality set: {modality_text}.")

    if study.study_description:
        parts.append(f"Study description: {study.study_description}.")

    if study.body_parts:
        body_text = ", ".join(_human_body_part(x) or x for x in study.body_parts)
        parts.append(f"Body region hints from metadata: {body_text}.")

    total_images = sum(series.image_count for series in study.series)
    parts.append(f"Total instances found: {total_images}.")

    contrast_count = sum(1 for s in study.series if s.contrast_suspected is True)
    if contrast_count:
        parts.append(f"{contrast_count} series appear to be contrast-enhanced based on metadata cues.")

    if study.warnings:
        parts.append("Warnings: " + "; ".join(study.warnings) + ".")

    return " ".join(parts)



def make_summary(report: DicomInsightReport) -> str:
    if report.series:
        s = report.series
        pieces = [p for p in [s.modality, _human_body_part(s.body_part_examined)] if p]
        title = " ".join(pieces) if pieces else "DICOM series"
        meta: list[str] = []
        if s.image_count:
            meta.append(f"{s.image_count} images")
        if s.rows and s.columns:
            meta.append(f"{s.rows}×{s.columns}")
        if s.slice_thickness is not None:
            meta.append(f"{s.slice_thickness:g} mm")
        return f"{title} — " + ", ".join(meta) if meta else title
    if report.study:
        st = report.study
        modalities = "/".join(st.modalities) if st.modalities else "unknown modality"
        return f"Study with {len(st.series)} series ({modalities})"
    return "DICOM report"
