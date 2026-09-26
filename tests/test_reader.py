from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_dataset

from dicom_insight.reader import DicomInsightError, is_probably_dicom, iter_dicom_files, load_dataset


def test_is_probably_dicom_accepts_supported_suffixes(tmp_path: Path) -> None:
    dcm = make_dataset(tmp_path / "a.dcm")
    no_suffix = tmp_path / "b"
    no_suffix.write_bytes(b"not really dicom")
    assert is_probably_dicom(dcm) is True
    assert is_probably_dicom(no_suffix) is True


def test_is_probably_dicom_rejects_other_suffixes(tmp_path: Path) -> None:
    other = tmp_path / "notes.txt"
    other.write_text("hello")
    assert is_probably_dicom(other) is False


def test_is_probably_dicom_rejects_missing_or_directory(tmp_path: Path) -> None:
    assert is_probably_dicom(tmp_path / "missing.dcm") is False
    assert is_probably_dicom(tmp_path) is False


def test_iter_dicom_files_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(iter_dicom_files(tmp_path / "does-not-exist"))


def test_iter_dicom_files_skips_unsupported_suffixes(tmp_path: Path) -> None:
    make_dataset(tmp_path / "a.dcm")
    (tmp_path / "readme.txt").write_text("not dicom")
    files = list(iter_dicom_files(tmp_path))
    assert [f.name for f in files] == ["a.dcm"]


def test_load_dataset_invalid_file_raises(tmp_path: Path) -> None:
    # A directory is not a readable DICOM stream: dcmread raises IsADirectoryError,
    # which load_dataset wraps into a DicomInsightError.
    with pytest.raises(DicomInsightError):
        load_dataset(tmp_path)


def test_load_dataset_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(DicomInsightError):
        load_dataset(tmp_path / "missing.dcm")
