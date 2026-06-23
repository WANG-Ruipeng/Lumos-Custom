#!/usr/bin/env python
"""Create a one-case UniLumos official-protocol BSS smoke manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[3]
CODE_ROOT = TASK_ROOT / "UniLumos"
DEFAULT_RUN_NAME = "model_b_unilumos_official_bss_smoke_v1"
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from bss_experiments.unilumos.bss_core.manifest import write_manifest


def default_experiment_root() -> Path:
    drive = Path("/content/drive/MyDrive")
    if drive.exists():
        return drive / "Colab_Projects" / "UniLumos-BSS-Runs" / DEFAULT_RUN_NAME
    if Path("/content").exists():
        return Path("/content/UniLumos-BSS-Runs") / DEFAULT_RUN_NAME
    return TASK_ROOT / "bss_runs" / DEFAULT_RUN_NAME


def git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(TASK_ROOT.parent), *args], text=True).strip()
    except Exception:
        return ""


def dirty_flag() -> str:
    return "true" if git_value(["status", "--short"]) else "false"


def load_cases(data_path: Path, max_cases: int) -> list[dict]:
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"No cases found in {data_path}")
    return rows[:max_cases]


def write_case_csv(path: Path, fieldnames: list[str], row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def method_rows(ladder: bool) -> list[dict]:
    rows = [
        {"method": "uniform8", "family": "uniform", "sampler_mode": "uniform", "steps": 8, "base": ""},
        {"method": "uniform10", "family": "uniform", "sampler_mode": "uniform", "steps": 10, "base": ""},
        {"method": "bss10", "family": "bss", "sampler_mode": "bss", "steps": 10, "base": 8},
        {"method": "reference_uniform25", "family": "reference", "sampler_mode": "uniform", "steps": 25, "base": ""},
    ]
    if ladder:
        for steps in (12, 16, 20, 24):
            rows.append({"method": f"uniform{steps}", "family": "uniform", "sampler_mode": "uniform", "steps": steps, "base": ""})
            rows.append({"method": f"bss{steps}", "family": "bss", "sampler_mode": "bss", "steps": steps, "base": steps - 2})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("abc", "ab", "ac", "a", "image"), default="abc")
    parser.add_argument("--data_path", type=Path, default=CODE_ROOT / "examples" / "examples_refined.csv")
    parser.add_argument("--experiment_root", type=Path, default=default_experiment_root())
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--max_cases", type=int, default=1)
    parser.add_argument("--sample_shift", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ladder", action="store_true")
    args = parser.parse_args()

    exp_root = args.experiment_root
    manifest_path = args.manifest or exp_root / "manifests" / "unilumos_official_smoke_manifest.csv"
    for rel in [
        "manifests/cases",
        "logs",
        "outputs",
        "schedules",
        "metrics",
        "tables",
        "figures/side_by_side",
        "reports",
        "patches",
        "scripts",
    ]:
        (exp_root / rel).mkdir(parents=True, exist_ok=True)

    cases = load_cases(args.data_path, args.max_cases)
    with args.data_path.open("r", encoding="utf-8", newline="") as handle:
        fieldnames = list(csv.DictReader(handle).fieldnames or [])

    rows = []
    commit = git_value(["rev-parse", "HEAD"])
    for case_index, case in enumerate(cases):
        foreground = case.get("path", "")
        background = case.get("bg_path", "")
        example = case.get("example_folder") or Path(foreground).stem or f"case_{case_index}"
        bg_id = Path(background).stem if background else "no_bg"
        case_id = f"{example}_{bg_id}"
        prompt_hash = hashlib.sha1((case.get("text") or "").encode("utf-8")).hexdigest()[:12]

        for method in method_rows(args.ladder):
            run_id = f"{case_id}_{method['method']}_seed{args.seed}"
            case_csv = exp_root / "manifests" / "cases" / f"{run_id}.csv"
            write_case_csv(case_csv, fieldnames, case)
            output_stem = exp_root / "outputs" / method["method"] / f"{case_id}_gen"
            schedule_json = exp_root / "schedules" / f"{run_id}_schedule.json"
            rows.append(
                {
                    "run_id": run_id,
                    "model_name": "UniLumos",
                    "protocol": "unilumos_official_protocol_smoke",
                    "mode": args.mode,
                    "case_id": case_id,
                    "foreground_id": Path(foreground).stem,
                    "background_id": bg_id,
                    "prompt_hash": prompt_hash,
                    "method": method["method"],
                    "method_family": method["family"],
                    "sampler_mode": method["sampler_mode"],
                    "sample_steps": method["steps"],
                    "base_sample_steps": method["base"],
                    "actual_nfe": method["steps"],
                    "sample_shift": args.sample_shift,
                    "split_pairs": "0,-1",
                    "seed": args.seed,
                    "input_paths": json.dumps(
                        {
                            "path": foreground,
                            "mask_path": case.get("mask_path", ""),
                            "deg_path": case.get("deg_path", ""),
                            "bg_path": background,
                        },
                        sort_keys=True,
                    ),
                    "checkpoint_paths": json.dumps({"weights_root": "UniLumos/weights"}, sort_keys=True),
                    "case_data_path": str(case_csv),
                    "output_path": str(output_stem),
                    "schedule_json_path": str(schedule_json),
                    "stdout_log_path": str(exp_root / "logs" / f"{run_id}.stdout.log"),
                    "stderr_log_path": str(exp_root / "logs" / f"{run_id}.stderr.log"),
                    "runtime_json_path": str(exp_root / "logs" / f"{run_id}.runtime.json"),
                    "status": "pending",
                    "error_message": "",
                    "git_commit": commit,
                    "code_dirty_flag": dirty_flag(),
                }
            )

    write_manifest(manifest_path, rows)
    print(manifest_path)


if __name__ == "__main__":
    main()
