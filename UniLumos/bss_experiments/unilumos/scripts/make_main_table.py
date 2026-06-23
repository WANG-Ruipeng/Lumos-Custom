#!/usr/bin/env python
"""Create the main one-case smoke markdown table."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


METHOD_ORDER = ["uniform8", "uniform10", "bss10", "reference_uniform25"]


def fmt(value: str, digits: int = 6) -> str:
    try:
        return f"{float(value):.{digits}g}"
    except Exception:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics_csv", required=True, type=Path)
    parser.add_argument("--output_md", type=Path, default=None)
    args = parser.parse_args()

    with args.metrics_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows.sort(key=lambda row: METHOD_ORDER.index(row["method"]) if row["method"] in METHOD_ORDER else 999)
    out = args.output_md or args.metrics_csv.parent.parent / "tables" / "main_smoke_table.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    uniform10 = next((row for row in rows if row["method"] == "uniform10"), None)
    bss10 = next((row for row in rows if row["method"] == "bss10"), None)
    bss_win = ""
    if uniform10 and bss10:
        bss_win = str(
            float(bss10.get("rgb_l1", "inf")) < float(uniform10.get("rgb_l1", "inf"))
            or float(bss10.get("temporal_diff_l1_to_ref", "inf"))
            < float(uniform10.get("temporal_diff_l1_to_ref", "inf"))
        )

    with out.open("w", encoding="utf-8") as handle:
        handle.write("| Method | NFE | RGB L1 low | RGB L2 low | PSNR high | Temporal ref-error low | RGB closure high | Temporal closure high | BSS win vs uniform10 |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for row in rows:
            handle.write(
                f"| {row['method']} | {row['actual_nfe']} | {fmt(row.get('rgb_l1', ''))} | "
                f"{fmt(row.get('rgb_l2', ''))} | {fmt(row.get('psnr', ''))} | "
                f"{fmt(row.get('temporal_diff_l1_to_ref', ''))} | {fmt(row.get('rgb_l1_closure', ''))} | "
                f"{fmt(row.get('temporal_closure', ''))} | {bss_win if row['method'] == 'bss10' else ''} |\n"
            )
    print(out)


if __name__ == "__main__":
    main()
