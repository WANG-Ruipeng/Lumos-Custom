#!/usr/bin/env python
"""Compute lightweight output metrics against the reference row."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

TASK_ROOT = Path(__file__).resolve().parents[3]
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from bss_experiments.unilumos.bss_core.manifest import read_manifest
from bss_experiments.unilumos.bss_core.metrics import compute_against_reference


def existing_output(stem: str) -> Path | None:
    base = Path(stem)
    for suffix in ("", ".mp4", ".png", ".jpg", ".jpeg"):
        candidate = Path(str(base) + suffix)
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output_csv", type=Path, default=None)
    parser.add_argument("--max_frames", type=int, default=None)
    args = parser.parse_args()

    rows = read_manifest(args.manifest)
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], []).append(row)

    metric_rows = []
    for case_id, case_rows in by_case.items():
        ref_row = next((row for row in case_rows if row["method_family"] == "reference"), None)
        if ref_row is None:
            continue
        ref_path = existing_output(ref_row["output_path"])
        if ref_path is None:
            continue
        baseline_row = next((row for row in case_rows if row["method"] == "uniform8"), None)
        baseline_path = existing_output(baseline_row["output_path"]) if baseline_row else None
        baseline_metrics = None
        if baseline_path:
            baseline_metrics = compute_against_reference(baseline_path, ref_path, max_frames=args.max_frames)

        for row in case_rows:
            out_path = existing_output(row["output_path"])
            if out_path is None:
                continue
            metrics = compute_against_reference(out_path, ref_path, max_frames=args.max_frames)
            if baseline_metrics:
                metrics["rgb_l1_closure"] = 1.0 - metrics["rgb_l1"] / max(baseline_metrics["rgb_l1"], 1e-12)
                metrics["temporal_closure"] = 1.0 - metrics["temporal_diff_l1_to_ref"] / max(
                    baseline_metrics["temporal_diff_l1_to_ref"], 1e-12
                )
            metric_rows.append({**row, **metrics, "resolved_output_path": str(out_path), "reference_path": str(ref_path)})

    output_csv = args.output_csv or args.manifest.parent.parent / "metrics" / "metrics_against_ref.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    if metric_rows:
        fields = list(metric_rows[0].keys())
        with output_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(metric_rows)
    output_json = output_csv.with_suffix(".json")
    output_json.write_text(json.dumps(metric_rows, indent=2) + "\n", encoding="utf-8")
    print(output_csv)


if __name__ == "__main__":
    main()
