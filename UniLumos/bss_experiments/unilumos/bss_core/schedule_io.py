"""JSON IO for UniLumos schedule metadata."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def to_float_list(values: Iterable[float] | None) -> list[float] | None:
    if values is None:
        return None
    return [float(value) for value in values]


def to_int_list(values) -> list[int] | None:
    if values is None:
        return None
    if hasattr(values, "detach"):
        values = values.detach().cpu().tolist()
    return [int(value) for value in values]


def find_git_root(start: str | os.PathLike | None = None) -> Path | None:
    current = Path(start or os.getcwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def git_commit(start: str | os.PathLike | None = None) -> str | None:
    root = find_git_root(start)
    if root is None:
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def git_dirty(start: str | os.PathLike | None = None) -> bool | None:
    root = find_git_root(start)
    if root is None:
        return None
    try:
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return bool(status.strip())
    except Exception:
        return None


def load_custom_sigmas(path: str | os.PathLike) -> list[float]:
    source = Path(path)
    if source.suffix.lower() == ".npy":
        import numpy as np

        return [float(value) for value in np.load(source).tolist()]

    with source.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        values = data.get("final_sigmas") or data.get("sigmas") or data.get("base_sigmas")
    else:
        values = data
    if values is None:
        raise ValueError(f"No sigmas found in custom schedule: {source}")
    return [float(value) for value in values]


def build_schedule_payload(
    *,
    method: str,
    sampler_mode: str,
    sample_steps: int,
    sample_shift: float,
    base_sample_steps: int | None,
    actual_nfe: int,
    split_pairs,
    terminal_coord: float,
    base_sigmas,
    final_sigmas,
    timesteps,
    inserted_midpoints,
    seed,
    output_path,
    metadata: dict | None = None,
) -> dict:
    return {
        "model_name": "UniLumos",
        "method": method,
        "sampler_mode": sampler_mode,
        "sample_steps": int(sample_steps),
        "sample_shift": float(sample_shift),
        "base_sample_steps": None if base_sample_steps is None else int(base_sample_steps),
        "actual_nfe": int(actual_nfe),
        "split_pairs": split_pairs,
        "terminal_coord": float(terminal_coord),
        "base_sigmas": to_float_list(base_sigmas),
        "final_sigmas": to_float_list(final_sigmas),
        "timesteps": to_int_list(timesteps),
        "inserted_midpoints": inserted_midpoints or [],
        "seed": seed,
        "output_path": output_path,
        "git_commit": git_commit(),
        "code_dirty_flag": git_dirty(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }


def dump_schedule_json(path: str | os.PathLike, payload: dict) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(target)
