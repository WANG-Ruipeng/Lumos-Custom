#!/usr/bin/env python
"""Create a lightweight quality ladder table from metrics CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics_csv", required=True, type=Path)
    parser.add_argument("--output_md", type=Path, default=None)
    args = parser.parse_args()

    with args.metrics_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out = args.output_md or args.metrics_csv.parent.parent / "tables" / "quality_ladder_table.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        handle.write("| Method | Family | NFE | RGB L1 | Temporal ref-error | Notes |\n")
        handle.write("|---|---|---:|---:|---:|---|\n")
        for row in sorted(rows, key=lambda item: (int(item.get("actual_nfe") or 0), item["method"])):
            handle.write(
                f"| {row['method']} | {row['method_family']} | {row['actual_nfe']} | "
                f"{row.get('rgb_l1', '')} | {row.get('temporal_diff_l1_to_ref', '')} | |\n"
            )
    print(out)


if __name__ == "__main__":
    main()
