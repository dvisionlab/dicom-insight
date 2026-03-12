from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dicom_insight import analyze_file, analyze_path



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
