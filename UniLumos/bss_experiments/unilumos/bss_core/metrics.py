"""Lightweight reference metrics for UniLumos outputs."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def _read_media(path: str | Path, max_frames: int | None = None) -> np.ndarray:
    source = Path(path)
    try:
        import imageio.v3 as iio

        if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            arr = iio.imread(source)
            return arr[None, ...].astype(np.float32) / 255.0

        frames = []
        for index, frame in enumerate(iio.imiter(source)):
            if max_frames is not None and index >= max_frames:
                break
            frames.append(np.asarray(frame, dtype=np.float32) / 255.0)
        if not frames:
            raise ValueError(f"No frames read from {source}")
        return np.stack(frames, axis=0)
    except ImportError as exc:
        raise RuntimeError("imageio is required for media metrics") from exc


def align_frame_count(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    count = min(len(a), len(b))
    return a[:count], b[:count]


def rgb_l1(a: np.ndarray, b: np.ndarray) -> float:
    a, b = align_frame_count(a, b)
    return float(np.mean(np.abs(a - b)))


def rgb_l2(a: np.ndarray, b: np.ndarray) -> float:
    a, b = align_frame_count(a, b)
    return float(np.mean((a - b) ** 2))


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = rgb_l2(a, b)
    if mse <= 0.0:
        return float("inf")
    return float(20.0 * math.log10(1.0 / math.sqrt(mse)))


def temporal_diff_l1(video: np.ndarray) -> float:
    if len(video) < 2:
        return 0.0
    return float(np.mean(np.abs(video[1:] - video[:-1])))


def temporal_diff_l1_to_ref(video: np.ndarray, ref: np.ndarray) -> float:
    video, ref = align_frame_count(video, ref)
    if len(video) < 2:
        return 0.0
    return rgb_l1(video[1:] - video[:-1], ref[1:] - ref[:-1])


def compute_against_reference(output_path: str | Path, reference_path: str | Path, max_frames: int | None = None) -> dict:
    output = _read_media(output_path, max_frames=max_frames)
    reference = _read_media(reference_path, max_frames=max_frames)
    return {
        "rgb_l1": rgb_l1(output, reference),
        "rgb_l2": rgb_l2(output, reference),
        "psnr": psnr(output, reference),
        "temporal_diff_l1": temporal_diff_l1(output),
        "temporal_diff_l1_to_ref": temporal_diff_l1_to_ref(output, reference),
    }
