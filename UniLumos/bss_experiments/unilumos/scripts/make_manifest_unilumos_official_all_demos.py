#!/usr/bin/env python
"""Create UniLumos official-demo all-scenarios BSS manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[3]
CODE_ROOT = TASK_ROOT / "UniLumos"
DEFAULT_RUN_NAME = "model_b_unilumos_official_all_demos_bss_v1"
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from bss_experiments.unilumos.bss_core.manifest import write_manifest


METHODS_ALL = [
    {"method": "uniform8", "family": "uniform", "sampler_mode": "uniform", "steps": 8, "base": ""},
    {"method": "uniform10", "family": "uniform", "sampler_mode": "uniform", "steps": 10, "base": ""},
    {"method": "uniform12", "family": "uniform", "sampler_mode": "uniform", "steps": 12, "base": ""},
    {"method": "uniform16", "family": "uniform", "sampler_mode": "uniform", "steps": 16, "base": ""},
    {"method": "uniform20", "family": "uniform", "sampler_mode": "uniform", "steps": 20, "base": ""},
    {"method": "uniform24", "family": "uniform", "sampler_mode": "uniform", "steps": 24, "base": ""},
    {"method": "reference_uniform25", "family": "reference", "sampler_mode": "uniform", "steps": 25, "base": ""},
    {"method": "bss10", "family": "bss", "sampler_mode": "bss", "steps": 10, "base": 8},
    {"method": "bss12", "family": "bss", "sampler_mode": "bss", "steps": 12, "base": 10},
    {"method": "bss16", "family": "bss", "sampler_mode": "bss", "steps": 16, "base": 14},
    {"method": "bss20", "family": "bss", "sampler_mode": "bss", "steps": 20, "base": 18},
    {"method": "bss24", "family": "bss", "sampler_mode": "bss", "steps": 24, "base": 22},
]
METHODS_SMOKE = [
    {"method": "uniform8", "family": "uniform", "sampler_mode": "uniform", "steps": 8, "base": ""},
    {"method": "uniform10", "family": "uniform", "sampler_mode": "uniform", "steps": 10, "base": ""},
    {"method": "bss10", "family": "bss", "sampler_mode": "bss", "steps": 10, "base": 8},
    {"method": "reference_uniform25", "family": "reference", "sampler_mode": "uniform", "steps": 25, "base": ""},
]


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


def dirty_status() -> str:
    return "true" if git_value(["status", "--short"]) else "false"


def load_cases(data_path: Path, max_cases: int | None = None) -> tuple[list[dict], list[str]]:
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    if max_cases is not None:
        rows = rows[:max_cases]
    if not rows:
        raise RuntimeError(f"No official demo rows found: {data_path}")
    return rows, fields


def write_case_csv(path: Path, fieldnames: list[str], row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def scenario_id_for(row: dict, index: int) -> str:
    foreground = row.get("path", "")
    background = row.get("bg_path", "")
    example = row.get("example_folder") or Path(foreground).stem or f"case_{index}"
    bg_id = Path(background).stem if background else "no_bg"
    return f"{example}_{bg_id}"


def mkdirs(exp_root: Path) -> None:
    for rel in [
        "manifests/cases",
        "logs",
        "outputs/uniform",
        "outputs/bss",
        "outputs/reference",
        "schedules",
        "metrics",
        "tables",
        "figures/side_by_side",
        "reports",
        "patches",
        "scripts",
    ]:
        (exp_root / rel).mkdir(parents=True, exist_ok=True)


def row_for_method(
    *,
    case: dict,
    case_index: int,
    fieldnames: list[str],
    method: dict,
    exp_root: Path,
    data_path: Path,
    mode: str,
    seed: int,
    sample_shift: float,
    commit: str,
    dirty: str,
) -> dict:
    scenario_id = scenario_id_for(case, case_index)
    prompt = case.get("text", "")
    foreground = case.get("path", "")
    background = case.get("bg_path", "")
    prompt_hash = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]
    run_id = f"{scenario_id}_{method['method']}_seed{seed}"
    case_csv = exp_root / "manifests" / "cases" / f"{run_id}.csv"
    write_case_csv(case_csv, fieldnames, case)

    family_dir = "reference" if method["family"] == "reference" else method["family"]
    output_stem = exp_root / "outputs" / family_dir / method["method"] / f"{scenario_id}_gen"
    schedule_json = exp_root / "schedules" / f"{run_id}_schedule.json"
    modality = "image" if mode == "image" else "video"
    conditioning = {
        "mask_path": case.get("mask_path", ""),
        "deg_path": case.get("deg_path", ""),
        "bg_path": background,
    }

    return {
        "run_id": run_id,
        "model_name": "UniLumos",
        "model_id": "UniLumos",
        "model_family": "flow_transformer_relighting",
        "modality": modality,
        "task": "relighting",
        "protocol": "official_demos",
        "mode": mode,
        "case_id": scenario_id,
        "scenario_id": scenario_id,
        "official_source_file": str(data_path),
        "prompt_or_caption": prompt,
        "foreground_path": foreground,
        "background_path": background,
        "input_image_path": case.get("image_path", ""),
        "conditioning_paths": json.dumps(conditioning, sort_keys=True),
        "foreground_id": Path(foreground).stem,
        "background_id": Path(background).stem if background else "no_bg",
        "prompt_hash": prompt_hash,
        "method": method["method"],
        "method_family": method["family"],
        "sampler_mode": method["sampler_mode"],
        "sample_steps": method["steps"],
        "base_sample_steps": method["base"],
        "actual_nfe": method["steps"],
        "sample_shift": sample_shift,
        "split_pairs": "0,-1",
        "reference_method": "reference_uniform25",
        "reference_nfe": 25,
        "low_baseline_method": "uniform8",
        "low_baseline_nfe": 8,
        "seed": seed,
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
        "dirty_status": dirty,
        "code_dirty_flag": dirty,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("abc", "ab", "ac", "a", "image"), default="abc")
    parser.add_argument("--data_path", type=Path, default=CODE_ROOT / "examples" / "examples_refined.csv")
    parser.add_argument("--experiment_root", type=Path, default=default_experiment_root())
    parser.add_argument("--max_cases", type=int, default=None)
    parser.add_argument("--sample_shift", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    exp_root = args.experiment_root
    mkdirs(exp_root)
    cases, fieldnames = load_cases(args.data_path, args.max_cases)
    commit = git_value(["rev-parse", "HEAD"])
    dirty = dirty_status()

    all_rows = []
    for case_index, case in enumerate(cases):
        for method in METHODS_ALL:
            all_rows.append(
                row_for_method(
                    case=case,
                    case_index=case_index,
                    fieldnames=fieldnames,
                    method=method,
                    exp_root=exp_root,
                    data_path=args.data_path,
                    mode=args.mode,
                    seed=args.seed,
                    sample_shift=args.sample_shift,
                    commit=commit,
                    dirty=dirty,
                )
            )

    smoke_rows = []
    for method in METHODS_SMOKE:
        smoke_rows.append(
            row_for_method(
                case=cases[0],
                case_index=0,
                fieldnames=fieldnames,
                method=method,
                exp_root=exp_root,
                data_path=args.data_path,
                mode=args.mode,
                seed=args.seed,
                sample_shift=args.sample_shift,
                commit=commit,
                dirty=dirty,
            )
        )

    manifest_csv = exp_root / "manifests" / "unilumos_official_all_demos_manifest.csv"
    manifest_jsonl = exp_root / "manifests" / "unilumos_official_all_demos_manifest.jsonl"
    smoke_csv = exp_root / "manifests" / "unilumos_official_smoke_manifest.csv"
    write_manifest(manifest_csv, all_rows)
    write_jsonl(manifest_jsonl, all_rows)
    write_manifest(smoke_csv, smoke_rows)

    print(manifest_csv)
    print(manifest_jsonl)
    print(smoke_csv)
    print(f"official_scenarios={len(cases)} all_rows={len(all_rows)} smoke_rows={len(smoke_rows)}")


if __name__ == "__main__":
    main()
