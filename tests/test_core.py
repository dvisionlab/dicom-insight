from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dicom_insight import analyze_file, analyze_path
from dicom_insight.llm import GeminiError
from dicom_insight.models import DicomInsightReport



def _make_dataset(path: Path, *, instance_number: int, series_uid: str, study_uid: str) -> None:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = generate_uid()
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid
    ds.Modality = "CT"
    ds.SeriesDescription = "HEAD W/O CONTRAST"
    ds.StudyDescription = "CT Head"
    ds.BodyPartExamined = "HEAD"
    ds.PatientSex = "M"
    ds.PatientAge = "045Y"
    ds.Rows = 512
    ds.Columns = 512
    ds.PixelSpacing = [0.5, 0.5]
    ds.SliceThickness = 1.0
    ds.SpacingBetweenSlices = 1.0
    ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    ds.SeriesNumber = 1
    ds.InstanceNumber = instance_number
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(str(path), write_like_original=False)



def test_analyze_file() -> None:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.dcm"
        _make_dataset(path, instance_number=1, series_uid=generate_uid(), study_uid=generate_uid())

        report = analyze_file(path)
        assert report.series is not None
        assert report.series.modality == "CT"
        assert report.series.orientation == "axial"
        assert "contrast" in report.explanation.lower()



def test_analyze_path() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        study_uid = generate_uid()
        series_uid = generate_uid()
        for i in range(3):
            _make_dataset(root / f"slice_{i}.dcm", instance_number=i + 1, series_uid=series_uid, study_uid=study_uid)

        report = analyze_path(root)
        assert report.study is not None
        assert len(report.study.series) == 1
        assert report.study.series[0].image_count == 3
        assert report.summary.startswith("Study with 1 series")



def test_hidden_files_are_skipped() -> None:
    """Dotfiles and files inside hidden directories must not be parsed."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        study_uid = generate_uid()
        series_uid = generate_uid()
        for i in range(2):
            _make_dataset(root / f"slice_{i}.dcm", instance_number=i + 1, series_uid=series_uid, study_uid=study_uid)

        # Create hidden files that should be ignored
        (root / "._resource_fork").write_bytes(b"\x00" * 4)
        (root / ".DS_Store").write_bytes(b"\x00" * 16)
        hidden_dir = root / ".hidden"
        hidden_dir.mkdir()
        _make_dataset(hidden_dir / "slice_0.dcm", instance_number=3, series_uid=series_uid, study_uid=study_uid)

        report = analyze_path(root)
        assert report.study is not None
        # Only the 2 visible slices should be counted; hidden dir file excluded
        assert report.study.series[0].image_count == 2



class _FailingProvider:
    """Stub that always raises GeminiError (simulates 429 / network failure)."""

    def explain(self, report: DicomInsightReport) -> str:
        raise GeminiError("429 Resource has been exhausted")

    def summarize(self, report: DicomInsightReport, deep_context: bool = False) -> str:
        raise GeminiError("429 Resource has been exhausted")

    def detect_anomalies(self, report: DicomInsightReport, deep_context: bool = False) -> list[str]:
        raise GeminiError("429 Resource has been exhausted")



def test_gemini_failure_falls_back_to_heuristics_file() -> None:
    """When the LLM provider raises GeminiError the report must still be complete."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.dcm"
        _make_dataset(path, instance_number=1, series_uid=generate_uid(), study_uid=generate_uid())

        report = analyze_file(path, provider=_FailingProvider())

        # Heuristic explanation must be present (not an error string)
        assert report.explanation
        assert "Error" not in report.explanation
        assert "contrast" in report.explanation.lower()
        # No LLM content
        assert report.ai_summary is None
        assert report.technical_anomalies == []
        # Warning must mention the LLM failure
        assert any("LLM" in w for w in report.warnings)



def test_gemini_failure_falls_back_to_heuristics_path() -> None:
    """Same fallback check for folder analysis."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        study_uid = generate_uid()
        series_uid = generate_uid()
        for i in range(3):
            _make_dataset(root / f"slice_{i}.dcm", instance_number=i + 1, series_uid=series_uid, study_uid=study_uid)

        report = analyze_path(root, provider=_FailingProvider())

        assert report.study is not None
        assert report.explanation
        assert "Error" not in report.explanation
        assert report.ai_summary is None
        assert report.technical_anomalies == []
        assert any("LLM" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# Anatomy analysis tests
# ---------------------------------------------------------------------------

def test_anatomy_heuristic_consistent_tags() -> None:
    """HEAD BodyPartExamined + matching SeriesDescription → clean region line."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.dcm"
        _make_dataset(path, instance_number=1, series_uid=generate_uid(), study_uid=generate_uid())

        report = analyze_file(path)
        assert report.anatomy_analysis is not None
        # Should mention Head (consistent tags, no discordance callout expected)
        assert "Head" in report.anatomy_analysis
        assert "[!NOTE]" not in report.anatomy_analysis


def test_anatomy_heuristic_discordant_tags() -> None:
    """Discordant BodyPartExamined vs SeriesDescription triggers a [!NOTE] callout."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.dcm"
        _make_dataset(path, instance_number=1, series_uid=generate_uid(), study_uid=generate_uid())

        # Overwrite the DICOM file with mismatched tags
        from pydicom import dcmread
        ds = dcmread(str(path))
        ds.BodyPartExamined = "CHEST"       # says chest
        ds.SeriesDescription = "BRAIN MRI"  # says head/brain
        ds.save_as(str(path), write_like_original=False)

        report = analyze_file(path)
        assert report.anatomy_analysis is not None
        # Discordance must be flagged
        assert "[!NOTE]" in report.anatomy_analysis


def test_anatomy_heuristic_no_recognisable_tags() -> None:
    """When tags carry no anatomy keywords, anatomy_analysis is None."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.dcm"
        _make_dataset(path, instance_number=1, series_uid=generate_uid(), study_uid=generate_uid())

        from pydicom import dcmread
        ds = dcmread(str(path))
        del ds.BodyPartExamined
        ds.SeriesDescription = "SCOUT"  # no anatomy keyword
        ds.save_as(str(path), write_like_original=False)

        report = analyze_file(path)
        assert report.anatomy_analysis is None


def test_details_paragraph_breaks() -> None:
    """explain_series should produce multi-paragraph text, not a single long line."""
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "one.dcm"
        _make_dataset(path, instance_number=1, series_uid=generate_uid(), study_uid=generate_uid())

        report = analyze_file(path)
        # Paragraph break between each logical sentence
        assert "\n\n" in report.explanation
