"""Manifest helpers for UniLumos smoke runs."""

from __future__ import annotations

import csv
from pathlib import Path


MANIFEST_FIELDS = [
    "run_id",
    "model_name",
    "protocol",
    "mode",
    "case_id",
    "foreground_id",
    "background_id",
    "prompt_hash",
    "method",
    "method_family",
    "sampler_mode",
    "sample_steps",
    "base_sample_steps",
    "actual_nfe",
    "sample_shift",
    "split_pairs",
    "seed",
    "input_paths",
    "checkpoint_paths",
    "case_data_path",
    "output_path",
    "schedule_json_path",
    "stdout_log_path",
    "stderr_log_path",
    "runtime_json_path",
    "status",
    "error_message",
    "git_commit",
    "code_dirty_flag",
]


def read_manifest(path: str | Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_manifest(path: str | Path, rows: list[dict]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fields = list(MANIFEST_FIELDS)
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
