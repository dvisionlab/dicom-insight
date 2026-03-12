from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.errors import InvalidDicomError


SUPPORTED_SUFFIXES = {".dcm", ".dicom", ""}


class DicomInsightError(RuntimeError):
    pass



def is_probably_dicom(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in SUPPORTED_SUFFIXES:
        return True
    return True



def iter_dicom_files(path: str | Path) -> Iterable[Path]:
    root = Path(path)
    if root.is_file():
        yield root
        return
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    for file_path in sorted(root.rglob("*")):
        if is_probably_dicom(file_path):
            yield file_path



def load_dataset(path: str | Path, stop_before_pixels: bool = True) -> Dataset:
    try:
        return dcmread(str(path), stop_before_pixels=stop_before_pixels, force=True)
    except InvalidDicomError as exc:
        raise DicomInsightError(f"Invalid DICOM file: {path}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise DicomInsightError(f"Unable to read DICOM file: {path}") from exc
