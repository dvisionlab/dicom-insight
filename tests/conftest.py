from __future__ import annotations

from pathlib import Path

import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def make_dataset(
    path: Path,
    *,
    instance_number: int = 1,
    series_uid: str | None = None,
    study_uid: str | None = None,
    **overrides: object,
) -> Path:
    """Write a minimal-but-valid CT DICOM file to `path` and return it."""
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = generate_uid()
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = study_uid or generate_uid()
    ds.SeriesInstanceUID = series_uid or generate_uid()
    ds.Modality = "CT"
    ds.SeriesDescription = "HEAD W/O CONTRAST"
    ds.StudyDescription = "CT Head"
    ds.BodyPartExamined = "HEAD"
    ds.PatientName = "Doe^John"
    ds.PatientID = "PID12345"
    ds.PatientSex = "M"
    ds.PatientAge = "045Y"
    ds.AccessionNumber = "ACC00042"
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
    for key, value in overrides.items():
        setattr(ds, key, value)
    ds.save_as(str(path), write_like_original=False)
    return path


@pytest.fixture
def dicom_file(tmp_path: Path) -> Path:
    return make_dataset(tmp_path / "one.dcm")


@pytest.fixture
def dicom_study_dir(tmp_path: Path) -> Path:
    study_uid = generate_uid()
    series_uid = generate_uid()
    for i in range(3):
        make_dataset(
            tmp_path / f"slice_{i}.dcm",
            instance_number=i + 1,
            series_uid=series_uid,
            study_uid=study_uid,
        )
    return tmp_path
