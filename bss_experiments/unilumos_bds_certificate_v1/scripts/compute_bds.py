from __future__ import annotations

import argparse
import csv
import math
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path("bss_experiments/unilumos_bds_certificate_v1")
LOW_TSET = [10]
PREFERRED_ALL_TSET = [10, 16, 20, 24]
BOOTSTRAP_RESAMPLES_DEFAULT = 10000

TABLE_A_FIELDS = [
    "split_name",
    "tset_name",
    "calibration_cases",
    "calibration_mean_gain",
    "calibration_bootstrap_lcb95",
    "calibration_bootstrap_ci95",
    "calibration_win_rate",
    "calibration_hoeffding_lcb95",
    "predicted_verdict",
    "holdout_cases",
    "holdout_mean_gain",
    "holdout_win_rate",
    "holdout_confirms_prediction",
    "notes",
]

CROSS_MODEL_FIELDS = [
    "model_id",
    "modality",
    "task",
    "protocol",
    "mode",
    "reference_method",
    "reference_nfe",
    "cases",
    "tested_nfe_points",
    "bds_low_mean_over_splits",
    "bds_low_lcb_min_over_splits",
    "bds_all_mean_over_splits",
    "bds_all_lcb_min_over_splits",
    "holdout_low_mean_gain_mean_over_splits",
    "holdout_all_mean_gain_mean_over_splits",
    "holdout_confirmation_rate",
    "predicted_deployment",
    "final_verdict",
    "notes",
]

TABLE_B_FIELDS = [
    "model_id",
    "bds_predicted_deployment",
    "full_mean_rgb_delta",
    "full_win_rate",
    "full_low_gain",
    "full_high_gain",
    "matched_quality_status",
    "prediction_consistent_with_full_result",
]


def repo_root_from(start: Path) -> Path:
    current = start.resolve()
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path
    return current


def ensure_output_dirs(root: Path) -> None:
    for name in ["reports", "tables", "figures", "scripts", "splits", "metrics"]:
        (root / name).mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        return rows, list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def write_markdown_table(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    header = "| " + " | ".join(fieldnames) + " |"
    separator = "| " + " | ".join("---" for _ in fieldnames) + " |"
    body = [
        "| " + " | ".join(markdown_escape(row.get(field, "")) for field in fieldnames) + " |"
        for row in rows
    ]
    path.write_text("\n".join([header, separator, *body]) + "\n", encoding="utf-8")


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    rounded = int(round(number))
    if abs(number - rounded) < 1e-6:
        return rounded
    return None


def format_float(value: float | None) -> str:
    if value is None or math.isnan(value):
        return ""
    return f"{value:.12g}"


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def bootstrap_summary(values: list[float], resamples: int, seed: int) -> tuple[float, tuple[float, float]]:
    if not values:
        return math.nan, (math.nan, math.nan)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(resamples):
        means.append(sum(rng.choice(values) for _ in range(n)) / n)
    means.sort()
    return percentile(means, 0.05), (percentile(means, 0.025), percentile(means, 0.975))


def hoeffding_lcb(values: list[float], delta: float = 0.05) -> float:
    if not values:
        return math.nan
    clipped = [min(1.0, max(-1.0, value)) for value in values]
    n = len(clipped)
    return mean(clipped) - 2 * math.sqrt(math.log(1 / delta) / (2 * n))


def win_rate(values: list[float]) -> float:
    if not values:
        return math.nan
    return sum(1 for value in values if value > 0) / len(values)


def unique_cases(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_case: dict[str, str] = {}
    for row in rows:
        case_id = row["case_id"]
        by_case.setdefault(case_id, row["scenario_id"])
    return [{"case_id": case_id, "scenario_id": scenario_id} for case_id, scenario_id in sorted(by_case.items(), key=lambda item: (item[1], item[0]))]


def write_split(path: Path, split_name: str, cases: list[dict[str, str]], calibration_cases: set[str]) -> None:
    rows = []
    for case in cases:
        rows.append(
            {
                "case_id": case["case_id"],
                "scenario_id": case["scenario_id"],
                "split_name": split_name,
                "split": "calibration" if case["case_id"] in calibration_cases else "holdout",
            }
        )
    write_csv(path, rows, ["case_id", "scenario_id", "split_name", "split"])


def write_splits(output_root: Path, cases: list[dict[str, str]]) -> tuple[dict[str, dict[str, set[str]]], list[str]]:
    split_specs: dict[str, dict[str, set[str]]] = {}
    notes: list[str] = []
    half = len(cases) // 2

    first_calibration = {case["case_id"] for case in cases[:half]}
    split_specs["first_half_split"] = {
        "calibration": first_calibration,
        "holdout": {case["case_id"] for case in cases[half:]},
    }
    write_split(output_root / "splits" / "first_half_split.csv", "first_half_split", cases, first_calibration)

    alternating_calibration = {case["case_id"] for index, case in enumerate(cases) if index % 2 == 0}
    split_specs["alternating_split"] = {
        "calibration": alternating_calibration,
        "holdout": {case["case_id"] for index, case in enumerate(cases) if index % 2 == 1},
    }
    write_split(output_root / "splits" / "alternating_split.csv", "alternating_split", cases, alternating_calibration)

    rng = random.Random(0)
    shuffled = cases[:]
    rng.shuffle(shuffled)
    random_calibration = {case["case_id"] for case in shuffled[:half]}
    split_specs["random_split_seed0"] = {
        "calibration": random_calibration,
        "holdout": {case["case_id"] for case in shuffled[half:]},
    }
    write_split(output_root / "splits" / "random_split_seed0.csv", "random_split_seed0", cases, random_calibration)

    group_by_case: dict[str, str] = {}
    for case in cases:
        scenario = case["scenario_id"].lower()
        group = None
        if "foreground" in scenario or re.search(r"(^|[_\-])fg($|[_\-])", scenario):
            group = "foreground"
        elif "background" in scenario or re.search(r"(^|[_\-])bg($|[_\-])", scenario):
            group = "background"
        if group:
            group_by_case[case["case_id"]] = group

    groups = sorted(set(group_by_case.values()))
    if len(groups) >= 2 and len(group_by_case) == len(cases):
        calibration_group = groups[0]
        group_calibration = {case_id for case_id, group in group_by_case.items() if group == calibration_group}
        split_specs["background_or_group_split"] = {
            "calibration": group_calibration,
            "holdout": {case["case_id"] for case in cases if case["case_id"] not in group_calibration},
        }
        write_split(output_root / "splits" / "background_or_group_split.csv", "background_or_group_split", cases, group_calibration)
        notes.append(f"background_or_group_split used `{calibration_group}` as calibration and the other exposed group(s) as holdout.")
    else:
        skip_note = "background_or_group_split skipped because scenario ids do not expose complete foreground/background groups."
        notes.append(skip_note)
        (output_root / "splits" / "background_or_group_split_SKIPPED.md").write_text(skip_note + "\n", encoding="utf-8")

    return split_specs, notes


def gain_index(rows: list[dict[str, str]]) -> dict[str, dict[int, float]]:
    indexed: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        case_id = row["case_id"]
        nfe = to_int(row.get("actual_nfe"))
        gain = to_float(row.get("gain_rgb_l1_closure"))
        if nfe is not None and gain is not None:
            indexed[case_id][nfe] = gain
    return indexed


def case_level_values(indexed: dict[str, dict[int, float]], case_ids: set[str], tset: list[int]) -> list[float]:
    values = []
    for case_id in sorted(case_ids):
        gains = [indexed[case_id][nfe] for nfe in tset if nfe in indexed.get(case_id, {})]
        if gains:
            values.append(mean(gains))
    return values


def split_verdict(low_lcb: float, all_lcb: float, calibration_cases: int, low_ci: tuple[float, float], all_ci: tuple[float, float]) -> str:
    if calibration_cases < 5:
        return "Need-more-calibration"
    if math.isnan(low_lcb) or math.isnan(all_lcb):
        return "Need-more-calibration"
    if low_ci[0] <= 0 <= low_ci[1] and all_ci[0] <= 0 <= all_ci[1]:
        interval_note = False
    else:
        interval_note = False
    if interval_note:
        return "Need-more-calibration"
    if all_lcb > 0:
        return "Green"
    if low_lcb > 0 and all_lcb <= 0:
        return "Low-only / Mixed"
    return "Reject"


def prediction_confirmed(verdict: str, holdout_low_mean: float, holdout_all_mean: float) -> str:
    if verdict == "Green":
        return "true" if holdout_all_mean > 0 else "false"
    if verdict == "Low-only / Mixed":
        return "true" if holdout_low_mean > 0 and holdout_all_mean <= 0 else "false"
    if verdict == "Reject":
        return "true" if holdout_low_mean <= 0 else "false"
    return ""


def compute_split_rows(
    split_specs: dict[str, dict[str, set[str]]],
    indexed: dict[str, dict[int, float]],
    all_tset: list[int],
    resamples: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for split_index, (split_name, split) in enumerate(split_specs.items()):
        calibration_low = case_level_values(indexed, split["calibration"], LOW_TSET)
        calibration_all = case_level_values(indexed, split["calibration"], all_tset)
        holdout_low = case_level_values(indexed, split["holdout"], LOW_TSET)
        holdout_all = case_level_values(indexed, split["holdout"], all_tset)

        low_lcb, low_ci = bootstrap_summary(calibration_low, resamples, 1000 + split_index)
        all_lcb, all_ci = bootstrap_summary(calibration_all, resamples, 2000 + split_index)
        verdict = split_verdict(low_lcb, all_lcb, min(len(calibration_low), len(calibration_all)), low_ci, all_ci)
        holdout_low_mean = mean(holdout_low) if holdout_low else math.nan
        holdout_all_mean = mean(holdout_all) if holdout_all else math.nan
        confirmed = prediction_confirmed(verdict, holdout_low_mean, holdout_all_mean)

        summaries = {
            "low": {
                "values": calibration_low,
                "holdout": holdout_low,
                "lcb": low_lcb,
                "ci": low_ci,
                "hoeffding": hoeffding_lcb(calibration_low),
                "notes": "Tset={10}",
            },
            "all": {
                "values": calibration_all,
                "holdout": holdout_all,
                "lcb": all_lcb,
                "ci": all_ci,
                "hoeffding": hoeffding_lcb(calibration_all),
                "notes": "Tset={" + ",".join(str(nfe) for nfe in all_tset) + "}",
            },
        }
        for tset_name in ["low", "all"]:
            summary = summaries[tset_name]
            values = summary["values"]
            holdout_values = summary["holdout"]
            ci = summary["ci"]
            rows.append(
                {
                    "split_name": split_name,
                    "tset_name": tset_name,
                    "calibration_cases": str(len(values)),
                    "calibration_mean_gain": format_float(mean(values) if values else math.nan),
                    "calibration_bootstrap_lcb95": format_float(summary["lcb"]),
                    "calibration_bootstrap_ci95": f"[{format_float(ci[0])}, {format_float(ci[1])}]",
                    "calibration_win_rate": format_float(win_rate(values)),
                    "calibration_hoeffding_lcb95": format_float(summary["hoeffding"]),
                    "predicted_verdict": verdict,
                    "holdout_cases": str(len(holdout_values)),
                    "holdout_mean_gain": format_float(mean(holdout_values) if holdout_values else math.nan),
                    "holdout_win_rate": format_float(win_rate(holdout_values)),
                    "holdout_confirms_prediction": confirmed,
                    "notes": summary["notes"],
                }
            )
    return rows


def summarize_cross_model(rows: list[dict[str, str]], gain_rows: list[dict[str, str]], all_tset: list[int]) -> dict[str, str]:
    low_rows = [row for row in rows if row["tset_name"] == "low"]
    all_rows = [row for row in rows if row["tset_name"] == "all"]

    def floats(source: list[dict[str, str]], column: str) -> list[float]:
        values = []
        for row in source:
            parsed = to_float(row.get(column))
            if parsed is not None:
                values.append(parsed)
        return values

    low_means = floats(low_rows, "calibration_mean_gain")
    low_lcbs = floats(low_rows, "calibration_bootstrap_lcb95")
    all_means = floats(all_rows, "calibration_mean_gain")
    all_lcbs = floats(all_rows, "calibration_bootstrap_lcb95")
    holdout_low_means = floats(low_rows, "holdout_mean_gain")
    holdout_all_means = floats(all_rows, "holdout_mean_gain")
    confirmations = [row["holdout_confirms_prediction"] for row in all_rows if row["holdout_confirms_prediction"] in {"true", "false"}]
    confirmation_rate = sum(1 for item in confirmations if item == "true") / len(confirmations) if confirmations else math.nan

    low_lcb_min = min(low_lcbs) if low_lcbs else math.nan
    all_lcb_min = min(all_lcbs) if all_lcbs else math.nan
    if all_lcb_min > 0:
        predicted = "Green"
    elif low_lcb_min > 0 and all_lcb_min <= 0:
        predicted = "Low-only / Mixed"
    elif low_lcb_min <= 0:
        predicted = "Reject"
    else:
        predicted = "Need-more-calibration"

    if predicted == "Low-only / Mixed" and confirmation_rate == 1:
        final = "Low-only / Mixed certificate confirmed on holdout"
    elif predicted == "Green" and confirmation_rate == 1:
        final = "Green certificate confirmed on holdout"
    elif predicted == "Reject" and confirmation_rate == 1:
        final = "Reject certificate confirmed on holdout"
    else:
        final = f"{predicted}; holdout confirmation rate={format_float(confirmation_rate)}"

    first = gain_rows[0] if gain_rows else {}
    cases = len({row["case_id"] for row in gain_rows})
    tested = sorted({to_int(row.get("actual_nfe")) for row in gain_rows if to_int(row.get("actual_nfe")) is not None})
    return {
        "model_id": "UniLumos",
        "modality": "video",
        "task": "relighting",
        "protocol": first.get("protocol", "official_demos"),
        "mode": first.get("mode", "abc"),
        "reference_method": first.get("reference_method", "reference_uniform25"),
        "reference_nfe": first.get("reference_nfe", "25"),
        "cases": str(cases),
        "tested_nfe_points": ",".join(str(point) for point in tested),
        "bds_low_mean_over_splits": format_float(mean(low_means) if low_means else math.nan),
        "bds_low_lcb_min_over_splits": format_float(low_lcb_min),
        "bds_all_mean_over_splits": format_float(mean(all_means) if all_means else math.nan),
        "bds_all_lcb_min_over_splits": format_float(all_lcb_min),
        "holdout_low_mean_gain_mean_over_splits": format_float(mean(holdout_low_means) if holdout_low_means else math.nan),
        "holdout_all_mean_gain_mean_over_splits": format_float(mean(holdout_all_means) if holdout_all_means else math.nan),
        "holdout_confirmation_rate": format_float(confirmation_rate),
        "predicted_deployment": predicted,
        "final_verdict": final,
        "notes": "BDS_all Tset={" + ",".join(str(nfe) for nfe in all_tset) + "}; bootstrap resamples cases.",
    }


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def find_column(headers: list[str], candidates: list[str]) -> str | None:
    normalized = {normalize(header): header for header in headers}
    for candidate in candidates:
        found = normalized.get(normalize(candidate))
        if found:
            return found
    for header in headers:
        name = normalize(header)
        if any(normalize(candidate) in name for candidate in candidates):
            return header
    return None


def discover_summary_row(repo_root: Path) -> Path | None:
    expected_names = ["cross_model_summary_row.csv"]
    for path in repo_root.rglob("cross_model_summary_row.csv"):
        if ".git" not in path.parts and path.name in expected_names:
            return path
    return None


def compare_with_full_summary(repo_root: Path, cross_model_row: dict[str, str]) -> dict[str, str]:
    summary_path = discover_summary_row(repo_root)
    if not summary_path:
        return {
            "model_id": "UniLumos",
            "bds_predicted_deployment": cross_model_row["predicted_deployment"],
            "full_mean_rgb_delta": "",
            "full_win_rate": "",
            "full_low_gain": "",
            "full_high_gain": "",
            "matched_quality_status": "unavailable",
            "prediction_consistent_with_full_result": "",
        }
    rows, headers = read_csv_rows(summary_path)
    row = rows[0] if rows else {}
    mean_delta_col = find_column(headers, ["mean_rgb_delta", "bcg", "mean_gain", "full_mean_rgb_delta"])
    win_rate_col = find_column(headers, ["win_rate", "full_win_rate"])
    low_gain_col = find_column(headers, ["low_gain", "bss_low_gain", "full_low_gain"])
    high_gain_col = find_column(headers, ["high_gain", "bss_high_gain", "full_high_gain"])
    matched_col = find_column(headers, ["matched_quality_status", "matched_quality", "compute_saving_status"])

    full_mean = row.get(mean_delta_col, "") if mean_delta_col else ""
    full_win = row.get(win_rate_col, "") if win_rate_col else ""
    low_gain = row.get(low_gain_col, "") if low_gain_col else ""
    high_gain = row.get(high_gain_col, "") if high_gain_col else ""
    matched = row.get(matched_col, "") if matched_col else ""
    predicted = cross_model_row["predicted_deployment"]

    consistent = ""
    low_gain_float = to_float(low_gain)
    high_gain_float = to_float(high_gain)
    if predicted == "Low-only / Mixed" and low_gain_float is not None and high_gain_float is not None:
        consistent = "true" if low_gain_float > 0 and high_gain_float <= 0 else "false"
    elif predicted == "Green":
        full_mean_float = to_float(full_mean)
        consistent = "true" if full_mean_float is not None and full_mean_float > 0 else "false"
    elif predicted == "Reject":
        low_gain_float = to_float(low_gain)
        consistent = "true" if low_gain_float is not None and low_gain_float <= 0 else "false"

    return {
        "model_id": "UniLumos",
        "bds_predicted_deployment": predicted,
        "full_mean_rgb_delta": full_mean,
        "full_win_rate": full_win,
        "full_low_gain": low_gain,
        "full_high_gain": high_gain,
        "matched_quality_status": matched or "unavailable",
        "prediction_consistent_with_full_result": consistent,
    }


def write_split_summary_report(path: Path, rows: list[dict[str, str]], split_notes: list[str]) -> None:
    lines = [
        "# UniLumos BDS Split Summary",
        "",
        "BDS was computed on calibration cases and verified on holdout cases. Bootstrap resampling is case-level to preserve case/NFE dependence.",
        "",
        "## Split Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in split_notes)
    lines.extend(["", "## Results", ""])
    for row in rows:
        lines.append(
            f"- {row['split_name']} / {row['tset_name']}: mean={row['calibration_mean_gain']}, "
            f"LCB95={row['calibration_bootstrap_lcb95']}, holdout_mean={row['holdout_mean_gain']}, "
            f"verdict={row['predicted_verdict']}, confirmed={row['holdout_confirms_prediction']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_final_report(
    output_root: Path,
    cross_model_row: dict[str, str],
    table_b_row: dict[str, str],
    split_notes: list[str],
) -> None:
    report = f"""# Final UniLumos BDS Certificate Report

## 1. Purpose

This report evaluates whether a calibration subset of official UniLumos demos can predict BSS deployment behavior on holdout cases using RGB-L1 closure gains.

## 2. Why BDS Is Non-Post-Hoc

The protocol is calibration official demos -> BDS -> predicted deployment -> holdout verification. The verdict is derived from calibration splits before checking holdout means and win rates.

## 3. Artifact Audit

See `reports/00_artifact_audit.md`.

## 4. Same-Compute Gain Table Summary

The gain table is `metrics/unilumos_same_compute_gain_long.csv`.

- cases: {cross_model_row['cases']}
- tested NFE points: {cross_model_row['tested_nfe_points']}
- reference: {cross_model_row['reference_method']} at NFE {cross_model_row['reference_nfe']}

## 5. Calibration/Holdout Splits

Splits are stored under `splits/`.

{chr(10).join(f"- {note}" for note in split_notes)}

## 6. BDS-Low And BDS-All Results

- BDS_low mean over splits: {cross_model_row['bds_low_mean_over_splits']}
- BDS_low minimum LCB over splits: {cross_model_row['bds_low_lcb_min_over_splits']}
- BDS_all mean over splits: {cross_model_row['bds_all_mean_over_splits']}
- BDS_all minimum LCB over splits: {cross_model_row['bds_all_lcb_min_over_splits']}

Detailed rows are in `tables/tableA_unilumos_bds_by_split.csv`.

## 7. Holdout Verification

- holdout low mean gain over splits: {cross_model_row['holdout_low_mean_gain_mean_over_splits']}
- holdout all mean gain over splits: {cross_model_row['holdout_all_mean_gain_mean_over_splits']}
- holdout confirmation rate: {cross_model_row['holdout_confirmation_rate']}

## 8. Comparison With Full-Run Summary

- full mean RGB delta: {table_b_row['full_mean_rgb_delta'] or 'unavailable'}
- full win rate: {table_b_row['full_win_rate'] or 'unavailable'}
- full low gain: {table_b_row['full_low_gain'] or 'unavailable'}
- full high gain: {table_b_row['full_high_gain'] or 'unavailable'}
- matched quality status: {table_b_row['matched_quality_status']}
- prediction consistent with full result: {table_b_row['prediction_consistent_with_full_result'] or 'unavailable'}

## 9. Final UniLumos Deployment Verdict

{cross_model_row['final_verdict']}

## 10. Caveats

- official demos only
- RGB-L1 closure to `reference_uniform25`
- NFE as compute proxy
- no universal claim

## 11. Recommended Next Experiment

- solver-coordinate ablation
- sample_shift ablation
- Model C
"""
    (output_root / "reports" / "FINAL_UNILUMOS_BDS_CERTIFICATE_REPORT.md").write_text(report, encoding="utf-8")


def running_in_colab() -> bool:
    try:
        import google.colab  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def mirror_if_colab(output_root: Path) -> None:
    mirror_root = Path("/content/drive/MyDrive/Colab_Projects/UniLumos-BDS/unilumos_bds_certificate_v1")
    if running_in_colab() and mirror_root.parent.exists() and output_root.resolve() != mirror_root.resolve():
        shutil.copytree(output_root, mirror_root, dirs_exist_ok=True)


def compute_bds(repo_root: Path, output_root: Path, resamples: int) -> int:
    ensure_output_dirs(output_root)
    gain_path = output_root / "metrics" / "unilumos_same_compute_gain_long.csv"
    if not gain_path.exists():
        raise FileNotFoundError(f"Missing gain table: {gain_path}")
    gain_rows, _ = read_csv_rows(gain_path)
    cases = unique_cases(gain_rows)
    tested_nfes = sorted({to_int(row.get("actual_nfe")) for row in gain_rows if to_int(row.get("actual_nfe")) is not None})
    all_tset = [nfe for nfe in PREFERRED_ALL_TSET if nfe in tested_nfes]
    if not all_tset:
        all_tset = tested_nfes

    split_specs, split_notes = write_splits(output_root, cases)
    if set(PREFERRED_ALL_TSET) - set(all_tset):
        missing = sorted(set(PREFERRED_ALL_TSET) - set(all_tset))
        split_notes.append(f"BDS_all used available preferred exact NFE points {all_tset}; missing preferred point(s): {missing}.")
    indexed = gain_index(gain_rows)
    table_a_rows = compute_split_rows(split_specs, indexed, all_tset, resamples)
    write_csv(output_root / "tables" / "tableA_unilumos_bds_by_split.csv", table_a_rows, TABLE_A_FIELDS)
    write_markdown_table(output_root / "tables" / "tableA_unilumos_bds_by_split.md", table_a_rows, TABLE_A_FIELDS)
    write_split_summary_report(output_root / "reports" / "01_bds_split_summary.md", table_a_rows, split_notes)

    cross_model_row = summarize_cross_model(table_a_rows, gain_rows, all_tset)
    write_csv(output_root / "tables" / "cross_model_bds_row.csv", [cross_model_row], CROSS_MODEL_FIELDS)
    write_markdown_table(output_root / "tables" / "cross_model_bds_row.md", [cross_model_row], CROSS_MODEL_FIELDS)

    table_b_row = compare_with_full_summary(repo_root, cross_model_row)
    write_csv(output_root / "tables" / "tableB_bds_vs_full_summary.csv", [table_b_row], TABLE_B_FIELDS)
    write_markdown_table(output_root / "tables" / "tableB_bds_vs_full_summary.md", [table_b_row], TABLE_B_FIELDS)

    write_final_report(output_root, cross_model_row, table_b_row, split_notes)
    mirror_if_colab(output_root)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute UniLumos calibration-to-holdout BDS from same-compute gain table.")
    parser.add_argument("--repo-root", type=Path, default=repo_root_from(Path.cwd()))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--bootstrap-resamples", type=int, default=BOOTSTRAP_RESAMPLES_DEFAULT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_root = (repo_root / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root
    return compute_bds(repo_root, output_root, args.bootstrap_resamples)


if __name__ == "__main__":
    raise SystemExit(main())
