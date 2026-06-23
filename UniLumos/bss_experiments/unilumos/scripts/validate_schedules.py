#!/usr/bin/env python
"""Validate dumped UniLumos schedule JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TASK_ROOT = Path(__file__).resolve().parents[3]
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from bss_experiments.unilumos.bss_core.validate import validate_schedule_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--fail_fast", action="store_true")
    args = parser.parse_args()

    all_ok = True
    for path in args.paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result = validate_schedule_payload(payload)
        all_ok = all_ok and result["ok"]
        print(f"{path}: {'ok' if result['ok'] else 'failed'}")
        for check in result["checks"]:
            status = "ok" if check["passed"] else "failed"
            print(f"  {status} {check['name']} {check['detail']}")
        if args.fail_fast and not result["ok"]:
            raise SystemExit(1)
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
