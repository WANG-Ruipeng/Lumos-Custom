#!/usr/bin/env python
"""Convenience wrapper for creating and optionally running the one-case smoke."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment_root", type=Path, default=None)
    parser.add_argument("--weights_root", type=Path, default=None)
    parser.add_argument("--dry_run", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    manifest_cmd = [sys.executable, str(SCRIPT_DIR / "make_manifest_unilumos_official_smoke.py"), "--max_cases", "1"]
    if args.experiment_root:
        manifest_cmd.extend(["--experiment_root", str(args.experiment_root)])
    manifest = subprocess.check_output(manifest_cmd, text=True).strip()
    print(manifest)

    if args.dry_run or args.run:
        run_cmd = [sys.executable, str(SCRIPT_DIR / "run_manifest.py"), "--manifest", manifest]
        if args.weights_root:
            run_cmd.extend(["--weights_root", str(args.weights_root)])
        if args.dry_run:
            run_cmd.append("--dry_run")
        subprocess.check_call(run_cmd)


if __name__ == "__main__":
    main()
