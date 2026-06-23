#!/usr/bin/env python
"""Run UniLumos BSS manifest rows one at a time."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[3]
CODE_ROOT = TASK_ROOT / "UniLumos"
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from bss_experiments.unilumos.bss_core.manifest import read_manifest, write_manifest
SCRIPT_BY_MODE = {
    "abc": "unilumos_infer_abc.py",
    "ab": "unilumos_infer_ab.py",
    "ac": "unilumos_infer_ac.py",
    "a": "unilumos_infer_a.py",
    "image": "unilumos_infer_image.py",
}


def split_methods(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {piece.strip() for piece in value.split(",") if piece.strip()}


def row_command(row: dict, weights_root: Path, python_bin: str) -> list[str]:
    mode = row["mode"]
    script = SCRIPT_BY_MODE[mode]
    cmd = [
        python_bin,
        script,
        "--data_path",
        row["case_data_path"],
        "--save_dir",
        str(Path(row["output_path"]).parent),
        "--sample_steps",
        str(row["sample_steps"]),
        "--sample_shift",
        str(row["sample_shift"]),
        "--seed",
        str(row["seed"]),
        "--sampler_mode",
        row["sampler_mode"],
        "--split_pairs",
        row["split_pairs"],
        "--dump_schedule_json",
        row["schedule_json_path"],
        "--method",
        row["method"],
        "--max_cases",
        "1",
        "--t5_path",
        str(weights_root / "models_t5_umt5-xxl-enc-bf16.pth"),
        "--tokenizer_path",
        str(weights_root / "umt5-xxl"),
        "--vae_path",
        str(weights_root / "vae.pth"),
        "--unilumos_path",
        str(weights_root / "unilumos.pt"),
    ]
    if row.get("base_sample_steps"):
        cmd.extend(["--base_sample_steps", str(row["base_sample_steps"])])
    return cmd


def write_dry_run_report(path: Path, commands: list[tuple[str, list[str]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Dry Run Commands\n\n")
        handle.write("These commands are intended for the UniLumos code directory.\n\n")
        for run_id, cmd in commands:
            handle.write(f"## {run_id}\n\n")
            handle.write("```bash\n")
            handle.write(" ".join(cmd))
            handle.write("\n```\n\n")


def tail_text(path: Path, max_lines: int = 120) -> str:
    if not path.exists():
        return f"{path} does not exist."
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return f"{path} is empty."
    return "\n".join(lines[-max_lines:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--weights_root", type=Path, default=CODE_ROOT / "weights")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only_methods", type=str, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--sync_drive", action="store_true")
    parser.add_argument("--python_bin", type=str, default=sys.executable)
    args = parser.parse_args()

    rows = read_manifest(args.manifest)
    only_methods = split_methods(args.only_methods)
    selected = []
    for index, row in enumerate(rows):
        if only_methods and row["method"] not in only_methods:
            continue
        if args.resume and not args.force and row.get("status") == "done":
            continue
        selected.append((index, row))
        if args.limit is not None and len(selected) >= args.limit:
            break

    commands = [(row["run_id"], row_command(row, args.weights_root, args.python_bin)) for _, row in selected]
    exp_root = Path(rows[0]["stdout_log_path"]).parents[1] if rows else args.manifest.parent.parent
    if args.dry_run:
        write_dry_run_report(exp_root / "reports" / "01_dry_run_commands.md", commands)
        for _, cmd in commands:
            print(" ".join(cmd))
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(TASK_ROOT), str(CODE_ROOT), env.get("PYTHONPATH", "")])

    for row_index, row in selected:
        cmd = row_command(row, args.weights_root, args.python_bin)
        stdout_path = Path(row["stdout_log_path"])
        stderr_path = Path(row["stderr_log_path"])
        runtime_path = Path(row["runtime_json_path"])
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.time()
        row["status"] = "running"
        write_manifest(args.manifest, rows)
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            proc = subprocess.run(cmd, cwd=CODE_ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        elapsed = time.time() - start
        runtime_path.write_text(
            json.dumps({"run_id": row["run_id"], "runtime_seconds": elapsed, "returncode": proc.returncode}, indent=2) + "\n",
            encoding="utf-8",
        )
        if proc.returncode == 0:
            row["status"] = "done"
            row["error_message"] = ""
        else:
            row["status"] = "failed"
            row["error_message"] = f"returncode={proc.returncode}; see {stderr_path}"
            write_manifest(args.manifest, rows)
            print(f"Run failed: {row['run_id']}", file=sys.stderr)
            print(f"stderr log: {stderr_path}", file=sys.stderr)
            print(tail_text(stderr_path), file=sys.stderr)
            print(f"stdout log: {stdout_path}", file=sys.stderr)
            print(tail_text(stdout_path, max_lines=80), file=sys.stderr)
            raise SystemExit(proc.returncode)
        write_manifest(args.manifest, rows)

    if args.sync_drive:
        print("--sync_drive requested; no extra copy needed when experiment_root is already on Drive.")


if __name__ == "__main__":
    main()
