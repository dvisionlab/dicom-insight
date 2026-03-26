from __future__ import annotations

from collections import Counter

from .models import DicomInsightReport, DicomSeriesReport, DicomStudyReport


# ---------------------------------------------------------------------------
# Body-part / anatomy helpers
# ---------------------------------------------------------------------------

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


# Keyword → canonical anatomical region (checked in tag text)
_ANATOMY_KEYWORDS: dict[str, list[str]] = {
    "Head": ["HEAD", "BRAIN", "SKULL", "NEURO", "CRANIAL", "CEREBR", "CRANIO"],
    "Neck": ["NECK", "CERVICAL", "THYROID", "LARYNX"],
    "Chest": ["CHEST", "THORAX", "THORACIC", "LUNG", "PULMON", "CARDIAC", "HEART", "MEDIASTIN"],
    "Abdomen": ["ABDOMEN", "ABDOMIN", "LIVER", "PANCREAS", "RENAL", "HEPAT", "GASTRIC", "STOMACH", "BOWEL"],
    "Abdomen and Pelvis": ["ABDOMENPELVIS", "ABDOMINOPELVIC", "PELVIABDOMEN"],
    "Pelvis": ["PELVIS", "PELVIC", "BLADDER", "PROSTATE", "UTERUS", "OVARY"],
    "Spine": ["SPINE", "SPINAL", "VERTEBR", "LUMBAR", "THORACIC SPINE", "SACR", "DISC"],
    "Extremity": ["KNEE", "SHOULDER", "ANKLE", "WRIST", "ELBOW", "FOOT", "HAND", "TIBIA", "FEMUR", "HUMERUS"],
    "Kidney": ["KIDNEY", "RENAL"],
}

# Priority order when resolving conflicts: more specific wins
_REGION_PRIORITY = [
    "Abdomen and Pelvis", "Spine", "Extremity", "Kidney",
    "Head", "Neck", "Chest", "Abdomen", "Pelvis",
]


def _classify_anatomy(text: str) -> str | None:
    """Return the canonical anatomical region for a free-text tag value, or None."""
    upper = text.upper()
    for region in _REGION_PRIORITY:
        if any(kw in upper for kw in _ANATOMY_KEYWORDS[region]):
            return region
    return None


def explain_anatomy_heuristic(report: DicomInsightReport) -> str | None:
    """Return a short anatomy/projection statement derived from DICOM tags.

    When the tags are discordant the result includes a ``> [!NOTE]`` callout.
    Returns *None* when none of the relevant tags carry recognisable anatomy.
    """
    # Collect per-series data depending on report kind
    series_list: list[DicomSeriesReport] = []
    if report.series:
        series_list = [report.series]
    elif report.study:
        series_list = report.study.series

    # Gather (tag_name, value, region) tuples for all available tags across series
    tag_regions: dict[str, str] = {}  # tag_name → most common region
    for s in series_list:
        for tag_name, value in [
            ("BodyPartExamined", s.body_part_examined),
            ("SeriesDescription", s.description),
            ("ProtocolName", s.protocol_name),
        ]:
            if value:
                region = _classify_anatomy(value)
                if region:
                    tag_regions[tag_name] = region

    if not tag_regions:
        return None

    unique_regions = set(tag_regions.values())

    # Determine projection (take from first non-None orientation in series list)
    orientation: str | None = next(
        (s.orientation for s in series_list if s.orientation), None
    )
    projection_text = f" — projection: **{orientation.capitalize()}**" if orientation else ""

    if len(unique_regions) == 1:
        region = next(iter(unique_regions))
        return f"Anatomical region: **{region}**{projection_text}."

    # Discordant tags — pick best candidate in priority order or fall back to
    # BodyPartExamined (most authoritative DICOM tag).
    best_region: str
    if "BodyPartExamined" in tag_regions:
        best_region = tag_regions["BodyPartExamined"]
    else:
        # Prefer the region that appears earliest in the priority list
        all_regions = list(tag_regions.values())
        best_region = min(all_regions, key=lambda r: _REGION_PRIORITY.index(r) if r in _REGION_PRIORITY else 99)

    discordant_summary = ", ".join(f"{tag} → {region}" for tag, region in tag_regions.items())
    return (
        f"> [!NOTE]\n"
        f"> Tag discordance detected ({discordant_summary}). "
        f"Most likely anatomical region: **{best_region}**{projection_text}."
    )


# ---------------------------------------------------------------------------
# Text explanation helpers
# ---------------------------------------------------------------------------



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

    return "\n\n".join(parts)



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

    return "\n\n".join(parts)



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
