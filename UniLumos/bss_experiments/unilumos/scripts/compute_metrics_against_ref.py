#!/usr/bin/env python
"""Compute UniLumos output metrics against the official reference row."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

TASK_ROOT = Path(__file__).resolve().parents[3]
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from bss_experiments.unilumos.bss_core.manifest import read_manifest
from bss_experiments.unilumos.bss_core.metrics import compute_against_reference


METRIC_NAMES = ["rgb_l1", "rgb_l2", "psnr", "temporal_diff_l1", "temporal_diff_l1_to_ref"]


def existing_output(stem: str) -> Path | None:
    base = Path(stem)
    for suffix in ("", ".mp4", ".gif", ".png", ".jpg", ".jpeg"):
        candidate = Path(str(base) + suffix)
        if candidate.exists():
            return candidate
    return None


def read_runtime_seconds(path: str | Path) -> float | None:
    source = Path(path)
    if not source.exists():
        return None
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        return float(data.get("runtime_seconds"))
    except Exception:
        return None


def schedule_valid(row: dict) -> str:
    path = Path(row.get("schedule_json_path", ""))
    if not path.exists():
        return "false"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        final_sigmas = payload.get("final_sigmas") or []
        return str(len(final_sigmas) == int(row.get("actual_nfe", 0))).lower()
    except Exception:
        return "false"


def as_float(value, default: float | None = None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def closure(distance: float, baseline_distance: float | None) -> float | None:
    if baseline_distance is None or baseline_distance <= 0:
        return None
    return 1.0 - distance / max(baseline_distance, 1e-12)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output_csv", type=Path, default=None)
    parser.add_argument("--per_case_csv", type=Path, default=None)
    parser.add_argument("--master_long_csv", type=Path, default=None)
    parser.add_argument("--max_frames", type=int, default=None)
    args = parser.parse_args()

    rows = read_manifest(args.manifest)
    by_case: dict[str, list[dict]] = {}
    for row in rows:
        case_id = row.get("scenario_id") or row.get("case_id")
        by_case.setdefault(case_id, []).append(row)

    metric_rows: list[dict] = []
    for case_id, case_rows in by_case.items():
        ref_row = next((row for row in case_rows if row.get("method") == row.get("reference_method", "reference_uniform25")), None)
        if ref_row is None:
            ref_row = next((row for row in case_rows if row.get("method_family") == "reference"), None)
        if ref_row is None:
            continue
        ref_path = existing_output(ref_row["output_path"])
        if ref_path is None:
            continue

        baseline_method = ref_row.get("low_baseline_method") or "uniform8"
        baseline_row = next((row for row in case_rows if row.get("method") == baseline_method), None)
        baseline_path = existing_output(baseline_row["output_path"]) if baseline_row else None
        baseline_metrics = compute_against_reference(baseline_path, ref_path, max_frames=args.max_frames) if baseline_path else None

        for row in case_rows:
            if row.get("status") and row.get("status") != "done":
                continue
            out_path = existing_output(row["output_path"])
            if out_path is None:
                continue
            metrics = compute_against_reference(out_path, ref_path, max_frames=args.max_frames)
            rgb_closure = closure(metrics["rgb_l1"], baseline_metrics["rgb_l1"] if baseline_metrics else None)
            temporal_closure = closure(
                metrics["temporal_diff_l1_to_ref"],
                baseline_metrics["temporal_diff_l1_to_ref"] if baseline_metrics else None,
            )
            runtime_sec = read_runtime_seconds(row.get("runtime_json_path", ""))
            reference_nfe = as_float(row.get("reference_nfe"), 25.0) or 25.0
            actual_nfe = as_float(row.get("actual_nfe"), as_float(row.get("sample_steps"), 0.0)) or 0.0
            metric_rows.append(
                {
                    **row,
                    **metrics,
                    "rgb_l1_closure": "" if rgb_closure is None else rgb_closure,
                    "temporal_closure": "" if temporal_closure is None else temporal_closure,
                    "runtime_sec": "" if runtime_sec is None else runtime_sec,
                    "compute_fraction": actual_nfe / reference_nfe if reference_nfe else "",
                    "schedule_valid": schedule_valid(row),
                    "resolved_output_path": str(out_path),
                    "reference_path": str(ref_path),
                }
            )

    output_csv = args.output_csv or args.manifest.parent.parent / "metrics" / "metrics_against_ref.csv"
    per_case_csv = args.per_case_csv or args.manifest.parent.parent / "metrics" / "per_case_metrics.csv"
    master_long_csv = args.master_long_csv or args.manifest.parent.parent / "metrics" / "master_long_metrics.csv"

    if metric_rows:
        write_csv(output_csv, metric_rows)
        write_csv(per_case_csv, metric_rows)
    else:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        output_csv.write_text("\n", encoding="utf-8")
        per_case_csv.parent.mkdir(parents=True, exist_ok=True)
        per_case_csv.write_text("\n", encoding="utf-8")

    long_rows: list[dict] = []
    for row in metric_rows:
        actual_nfe = as_float(row.get("actual_nfe"), 0.0) or 0.0
        reference_nfe = as_float(row.get("reference_nfe"), 25.0) or 25.0
        for metric_name in METRIC_NAMES:
            metric_closure = ""
            if metric_name == "rgb_l1":
                metric_closure = row.get("rgb_l1_closure", "")
            elif metric_name == "temporal_diff_l1_to_ref":
                metric_closure = row.get("temporal_closure", "")
            long_rows.append(
                {
                    "model_id": row.get("model_id") or row.get("model_name") or "UniLumos",
                    "model_family": row.get("model_family", "flow_transformer_relighting"),
                    "modality": row.get("modality", "video"),
                    "task": row.get("task", "relighting"),
                    "protocol": row.get("protocol", "official_demos"),
                    "mode": row.get("mode", "abc"),
                    "scenario_id": row.get("scenario_id") or row.get("case_id"),
                    "method": row.get("method"),
                    "method_family": row.get("method_family"),
                    "actual_nfe": actual_nfe,
                    "reference_nfe": reference_nfe,
                    "compute_fraction": actual_nfe / reference_nfe if reference_nfe else "",
                    "metric_name": metric_name,
                    "raw_distance": row.get(metric_name, ""),
                    "closure": metric_closure,
                    "runtime_sec": row.get("runtime_sec", ""),
                    "schedule_valid": row.get("schedule_valid", ""),
                    "status": row.get("status", ""),
                }
            )
    if long_rows:
        write_csv(master_long_csv, long_rows)
    else:
        master_long_csv.parent.mkdir(parents=True, exist_ok=True)
        master_long_csv.write_text("\n", encoding="utf-8")

    output_json = output_csv.with_suffix(".json")
    output_json.write_text(json.dumps(metric_rows, indent=2) + "\n", encoding="utf-8")
    print(output_csv)
    print(per_case_csv)
    print(master_long_csv)


if __name__ == "__main__":
    main()
