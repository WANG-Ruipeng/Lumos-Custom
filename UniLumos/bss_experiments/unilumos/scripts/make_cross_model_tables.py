#!/usr/bin/env python
"""Generate support-aware paper tables for UniLumos official-demo BSS runs."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


TARGETS = [0.2, 0.4, 0.6, 0.8]
MAIN_TARGETS = [0.4, 0.6, 0.8]
THRESHOLDS = [0.50, 0.70, 0.80]
METHOD_ORDER = ["uniform8", "uniform10", "uniform12", "uniform16", "uniform20", "uniform24", "reference_uniform25", "bss10", "bss12", "bss16", "bss20", "bss24"]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def write_md(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("| " + " | ".join(fields) + " |\n")
        handle.write("|" + "|".join(["---"] * len(fields)) + "|\n")
        for row in rows:
            handle.write("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |\n")


def fnum(value, digits: int = 3) -> str:
    try:
        number = float(value)
    except Exception:
        return ""
    if not math.isfinite(number):
        return ""
    return f"{number:.{digits}f}"


def mean(values: list[float]) -> float | None:
    values = [value for value in values if value is not None and math.isfinite(value)]
    if not values:
        return None
    return sum(values) / len(values)


def sem(values: list[float]) -> float | None:
    values = [value for value in values if value is not None and math.isfinite(value)]
    if len(values) <= 1:
        return 0.0 if values else None
    m = mean(values)
    variance = sum((value - m) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) / math.sqrt(len(values))


def as_float(row: dict, key: str) -> float | None:
    try:
        return float(row.get(key, ""))
    except Exception:
        return None


def method_nfe(method: str) -> int | None:
    digits = "".join(ch for ch in method if ch.isdigit())
    return int(digits) if digits else None


def method_summary(rows: list[dict]) -> dict[str, dict]:
    by_method: dict[str, list[dict]] = {}
    for row in rows:
        by_method.setdefault(row.get("method", ""), []).append(row)
    summary = {}
    for method, method_rows in by_method.items():
        rgb = [as_float(row, "rgb_l1_closure") for row in method_rows]
        runtime = [as_float(row, "runtime_sec") for row in method_rows]
        summary[method] = {
            "method": method,
            "nfe": as_float(method_rows[0], "actual_nfe") or method_nfe(method),
            "rows": method_rows,
            "cases": len({row.get("scenario_id") or row.get("case_id") for row in method_rows}),
            "rgb_mean": mean(rgb),
            "rgb_sem": sem(rgb),
            "runtime_mean": mean(runtime),
            "model_id": method_rows[0].get("model_id") or method_rows[0].get("model_name") or "UniLumos",
            "model_family": method_rows[0].get("model_family", "flow_transformer_relighting"),
            "modality": method_rows[0].get("modality", "video"),
            "task": method_rows[0].get("task", "relighting"),
            "protocol": method_rows[0].get("protocol", "official_demos"),
            "mode": method_rows[0].get("mode", "abc"),
            "reference_method": method_rows[0].get("reference_method", "reference_uniform25"),
            "reference_nfe": as_float(method_rows[0], "reference_nfe") or 25.0,
        }
    return summary


def paired_points(summary: dict[str, dict], rows: list[dict]) -> list[dict]:
    points = []
    by_case_method = {(row.get("scenario_id") or row.get("case_id"), row.get("method")): row for row in rows}
    for method, bss in summary.items():
        if not method.startswith("bss"):
            continue
        nfe = int(bss["nfe"])
        uniform_method = f"uniform{nfe}"
        if uniform_method not in summary:
            continue
        uniform = summary[uniform_method]
        deltas = []
        wins = []
        for bss_row in bss["rows"]:
            scenario = bss_row.get("scenario_id") or bss_row.get("case_id")
            uniform_row = by_case_method.get((scenario, uniform_method))
            if not uniform_row:
                continue
            bss_value = as_float(bss_row, "rgb_l1_closure")
            uniform_value = as_float(uniform_row, "rgb_l1_closure")
            if bss_value is None or uniform_value is None:
                continue
            deltas.append(bss_value - uniform_value)
            wins.append(1.0 if bss_value > uniform_value else 0.0)
        points.append(
            {
                "nfe": nfe,
                "compute_fraction": nfe / (bss["reference_nfe"] or 25.0),
                "uniform_method": uniform_method,
                "bss_method": method,
                "uniform_rgb": uniform["rgb_mean"],
                "bss_rgb": bss["rgb_mean"],
                "delta": mean(deltas),
                "win_rate": mean(wins),
                "sem_uniform": uniform["rgb_sem"],
                "sem_bss": bss["rgb_sem"],
                "sem_delta": sem(deltas),
            }
        )
    return sorted(points, key=lambda point: point["nfe"])


def interp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def support_value(points: list[dict], target_fraction: float, reference_nfe: float) -> dict:
    target_nfe = target_fraction * reference_nfe
    if not points:
        return {"target_compute_fraction": target_fraction, "target_nfe": target_nfe, "support_mode": "OOS", "display_cell": "OOS"}
    for point in points:
        if abs(point["nfe"] - target_nfe) < 1e-9:
            return make_support_row(point, target_fraction, target_nfe, "E", True)
    if target_nfe < points[0]["nfe"]:
        return make_support_row(points[0], target_fraction, target_nfe, "F", False)
    if target_nfe > points[-1]["nfe"]:
        return make_support_row(points[-1], target_fraction, target_nfe, "C", False)
    for left, right in zip(points, points[1:]):
        if left["nfe"] <= target_nfe <= right["nfe"]:
            t = (target_nfe - left["nfe"]) / (right["nfe"] - left["nfe"])
            point = {
                "nfe": target_nfe,
                "compute_fraction": target_fraction,
                "uniform_method": f"interp_{left['uniform_method']}_{right['uniform_method']}",
                "bss_method": f"interp_{left['bss_method']}_{right['bss_method']}",
                "uniform_rgb": interp(left["uniform_rgb"], right["uniform_rgb"], t),
                "bss_rgb": interp(left["bss_rgb"], right["bss_rgb"], t),
                "delta": interp(left["delta"], right["delta"], t),
                "win_rate": interp(left["win_rate"], right["win_rate"], t),
                "sem_uniform": "",
                "sem_bss": "",
                "sem_delta": "",
            }
            return make_support_row(point, target_fraction, target_nfe, "I", True)
    return {"target_compute_fraction": target_fraction, "target_nfe": target_nfe, "support_mode": "OOS", "display_cell": "OOS"}


def make_support_row(point: dict, target_fraction: float, target_nfe: float, tag: str, include: bool) -> dict:
    actual_fraction = point["compute_fraction"]
    display = f"{fnum(point['bss_rgb'])} / {float(point['delta']):+.3f} [{tag}@{round(actual_fraction * 100):.0f}%]"
    return {
        "target_compute_fraction": target_fraction,
        "target_nfe": target_nfe,
        "actual_nfe_used": point["nfe"],
        "actual_compute_fraction": actual_fraction,
        "support_mode": tag,
        "include_in_mean_auc": str(include).lower(),
        "uniform_method": point["uniform_method"],
        "bss_method": point["bss_method"],
        "uniform_rgb_l1_closure": point["uniform_rgb"],
        "bss_rgb_l1_closure": point["bss_rgb"],
        "delta_rgb_l1_closure": point["delta"],
        "win_rate_rgb": point["win_rate"],
        "sem_uniform": point["sem_uniform"],
        "sem_bss": point["sem_bss"],
        "sem_delta": point["sem_delta"],
        "display_cell": display,
        "status": "ok",
    }


def monotone_reach_nfe(points: list[tuple[float, float]], threshold: float) -> float | None:
    points = sorted((nfe, value) for nfe, value in points if value is not None and math.isfinite(value))
    if not points:
        return None
    best_points = []
    best = -float("inf")
    for nfe, value in points:
        best = max(best, value)
        best_points.append((nfe, best))
    if best_points[0][1] >= threshold:
        return best_points[0][0]
    for (nfe0, value0), (nfe1, value1) in zip(best_points, best_points[1:]):
        if value1 >= threshold:
            if value1 == value0:
                return nfe1
            t = (threshold - value0) / (value1 - value0)
            return nfe0 + (nfe1 - nfe0) * t
    return None


def saving_cell(uniform_nfe: float | None, bss_nfe: float | None) -> tuple[str, float | None]:
    if uniform_nfe is None and bss_nfe is None:
        return "not reached", None
    if uniform_nfe is None:
        return "uniform not reached", None
    if bss_nfe is None:
        return "bss not reached", None
    saved = uniform_nfe - bss_nfe
    pct = saved / uniform_nfe if uniform_nfe else 0.0
    return f"{saved:.2f} NFE / {pct * 100:.1f}%", pct


def make_tables(metrics_csv: Path, output_dir: Path) -> dict[str, Path]:
    rows = read_csv(metrics_csv)
    rows = [row for row in rows if row.get("status", "done") == "done"]
    summary = method_summary(rows)
    if not summary:
        raise RuntimeError(f"No completed metric rows found in {metrics_csv}")
    meta = next(iter(summary.values()))
    reference_nfe = meta["reference_nfe"] or 25.0
    cases = len({row.get("scenario_id") or row.get("case_id") for row in rows})
    points = paired_points(summary, rows)
    support_rows = [support_value(points, target, reference_nfe) for target in TARGETS]
    included = [row for row in support_rows if row.get("include_in_mean_auc") == "true"]
    deltas = [float(row["delta_rgb_l1_closure"]) for row in included if row.get("delta_rgb_l1_closure") not in (None, "")]
    win_rates = [float(row["win_rate_rgb"]) for row in included if row.get("win_rate_rgb") not in (None, "")]
    mean_delta = mean(deltas)
    delta_auc = mean(deltas)
    win_rate = mean(win_rates)
    low_point = points[0] if points else None
    low_cell = ""
    if low_point:
        low_cell = make_support_row(low_point, low_point["compute_fraction"], low_point["nfe"], "E", False)["display_cell"]

    def cell_for(target: float) -> str:
        row = next(item for item in support_rows if abs(item["target_compute_fraction"] - target) < 1e-9)
        return row.get("display_cell", "")

    base = {
        "model_id": meta["model_id"],
        "modality": meta["modality"],
        "task": meta["task"],
        "protocol": meta["protocol"],
        "mode": meta["mode"],
        "reference_method": meta["reference_method"],
        "reference_nfe": int(reference_nfe),
        "cases": cases,
        "mean_rgb_delta": fnum(mean_delta),
        "rgb_delta_auc": fnum(delta_auc),
        "rgb_win_rate_same_compute": fnum(win_rate),
        "status": "complete" if points else "no_same_nfe_pairs",
        "notes": "support-aware; closure is reference-normalized RGB-L1 closure",
    }
    table1a = [{**base, "rgb_at_low": low_cell, "rgb_at_40pct": cell_for(0.4), "rgb_at_60pct": cell_for(0.6), "rgb_at_80pct": cell_for(0.8)}]
    table1b = [{**base, "rgb_at_20pct": cell_for(0.2), "rgb_at_40pct": cell_for(0.4), "rgb_at_60pct": cell_for(0.6), "rgb_at_80pct": cell_for(0.8)}]

    by_method = method_summary(rows)
    uniform_points = []
    bss_points = []
    for method, item in by_method.items():
        nfe = item["nfe"]
        if item["rgb_mean"] is None or nfe is None:
            continue
        if method.startswith("uniform"):
            uniform_points.append((float(nfe), item["rgb_mean"]))
        elif method == "reference_uniform25":
            uniform_points.append((float(nfe), item["rgb_mean"]))
        elif method.startswith("bss"):
            bss_points.append((float(nfe), item["rgb_mean"]))

    saving_details = []
    saving_cells = {}
    saving_pcts = []
    for threshold in THRESHOLDS:
        uniform_nfe = monotone_reach_nfe(uniform_points, threshold)
        bss_nfe = monotone_reach_nfe(bss_points, threshold)
        cell, pct = saving_cell(uniform_nfe, bss_nfe)
        saving_cells[f"save_at_rgb{int(threshold * 100)}"] = cell
        if pct is not None:
            saving_pcts.append(pct)
        saving_details.append(
            {
                "threshold": threshold,
                "uniform_nfe": "" if uniform_nfe is None else uniform_nfe,
                "bss_nfe": "" if bss_nfe is None else bss_nfe,
                "saving_cell": cell,
                "compute_saved_pct": "" if pct is None else pct,
            }
        )
    best_saving = max(saving_pcts) if saving_pcts else None
    table2 = [
        {
            "model_id": meta["model_id"],
            "reference_nfe": int(reference_nfe),
            "cases": cases,
            "save_at_rgb50": saving_cells["save_at_rgb50"],
            "save_at_rgb70": saving_cells["save_at_rgb70"],
            "save_at_rgb80": saving_cells["save_at_rgb80"],
            "best_tested_saving_pct": "" if best_saving is None else f"{best_saving * 100:.1f}%",
            "status": "complete" if saving_pcts else "threshold_not_reached",
            "notes": "monotone-envelope interpolation over tested official-demo means",
        }
    ]

    summary_row = [
        {
            "model_id": meta["model_id"],
            "model_family": meta["model_family"],
            "modality": meta["modality"],
            "task": meta["task"],
            "protocol": meta["protocol"],
            "mode": meta["mode"],
            "reference_method": meta["reference_method"],
            "reference_nfe": int(reference_nfe),
            "cases": cases,
            "status": base["status"],
            "rgb_at_low": low_cell,
            "rgb_at_20pct": cell_for(0.2),
            "rgb_at_40pct": cell_for(0.4),
            "rgb_at_60pct": cell_for(0.6),
            "rgb_at_80pct": cell_for(0.8),
            "mean_rgb_delta": fnum(mean_delta),
            "rgb_delta_auc": fnum(delta_auc),
            "rgb_win_rate_same_compute": fnum(win_rate),
            "rgb_save_at_50pct": saving_cells["save_at_rgb50"],
            "rgb_save_at_70pct": saving_cells["save_at_rgb70"],
            "rgb_save_at_80pct": saving_cells["save_at_rgb80"],
            "best_tested_rgb_saving_pct": "" if best_saving is None else f"{best_saving * 100:.1f}%",
            "notes": base["notes"],
        }
    ]

    paths = {
        "table1a_csv": output_dir / "table1a_same_compute_rgb_closure_main.csv",
        "table1a_md": output_dir / "table1a_same_compute_rgb_closure_main.md",
        "table1b_csv": output_dir / "table1b_same_compute_rgb_closure_support_aware.csv",
        "table1b_md": output_dir / "table1b_same_compute_rgb_closure_support_aware.md",
        "detailed_csv": output_dir / "table1_same_compute_rgb_closure_detailed.csv",
        "table2_csv": output_dir / "table2_matched_quality_compute_saving.csv",
        "table2_md": output_dir / "table2_matched_quality_compute_saving.md",
        "table2_detailed_csv": output_dir / "table2_matched_quality_compute_saving_detailed.csv",
        "summary_csv": output_dir / "cross_model_summary_row.csv",
        "summary_md": output_dir / "cross_model_summary_row.md",
    }
    write_csv(paths["table1a_csv"], table1a)
    write_md(paths["table1a_md"], table1a, list(table1a[0].keys()))
    write_csv(paths["table1b_csv"], table1b)
    write_md(paths["table1b_md"], table1b, list(table1b[0].keys()))
    write_csv(paths["detailed_csv"], support_rows)
    write_csv(paths["table2_csv"], table2)
    write_md(paths["table2_md"], table2, list(table2[0].keys()))
    write_csv(paths["table2_detailed_csv"], saving_details)
    write_csv(paths["summary_csv"], summary_row)
    write_md(paths["summary_md"], summary_row, list(summary_row[0].keys()))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics_csv", required=True, type=Path)
    parser.add_argument("--output_dir", type=Path, default=None)
    args = parser.parse_args()
    output_dir = args.output_dir or args.metrics_csv.parent.parent / "tables"
    paths = make_tables(args.metrics_csv, output_dir)
    for key, path in paths.items():
        print(f"{key}={path}")


if __name__ == "__main__":
    main()
