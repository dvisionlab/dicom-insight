"""Pixel data intensity statistics (opt-in, requires decoded PixelData)."""

from __future__ import annotations

from pydicom.dataset import Dataset

from .models import PixelStats


def compute_pixel_stats(ds: Dataset) -> PixelStats | None:
    """Compute basic intensity statistics from a dataset's pixel data.

    Returns None when the dataset has no PixelData, or the pixel data
    cannot be decoded (e.g. a compressed transfer syntax without the
    matching codec installed).
    """
    if "PixelData" not in ds:
        return None
    try:
        array = ds.pixel_array
    except Exception:
        return None

    values = array.astype("float64")
    min_value = float(values.min())
    max_value = float(values.max())
    return PixelStats(
        shape=tuple(int(dim) for dim in array.shape),
        dtype=str(array.dtype),
        min=min_value,
        max=max_value,
        mean=float(values.mean()),
        std=float(values.std()),
        is_constant=min_value == max_value,
    )
