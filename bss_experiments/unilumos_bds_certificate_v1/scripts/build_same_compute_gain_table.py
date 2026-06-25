from __future__ import annotations

import argparse
import csv
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path("bss_experiments/unilumos_bds_certificate_v1")

EXPECTED_RELATIVE_FILES = [
    "metrics/master_long_metrics.csv",
    "metrics/metrics_against_ref.csv",
    "metrics/per_case_metrics.csv",
    "tables/table1a_same_compute_rgb_closure_main.csv",
    "tables/table1b_same_compute_rgb_closure_support_aware.csv",
    "tables/table2_matched_quality_compute_saving.csv",
    "tables/table3_same_nfe_main.csv",
    "tables/table4_failure_or_smallest_gain_cases.csv",
    "tables/cross_model_summary_row.csv",
]

CANDIDATE_RESULT_ROOTS = [
    Path("/content/drive/MyDrive/Colab_Projects/UniLumos-BSS-Runs/model_b_unilumos_official_all_demos_bss_v1"),
    Path("/content/UniLumos-BSS-Runs/model_b_unilumos_official_all_demos_bss_v1"),
    Path("/content/drive/MyDrive/Colab_Projects/UniLumos-BSS-Runs/model_b_unilumos_official_bss_smoke_v1"),
]

ALLOWED_NFE_POINTS = [10, 12, 16, 20, 24]
REFERENCE_METHOD_DEFAULT = "reference_uniform25"
REFERENCE_NFE_DEFAULT = 25
MODE_DEFAULT = "abc"

GAIN_FIELDNAMES = [
    "model_id",
    "protocol",
    "mode",
    "reference_method",
    "reference_nfe",
    "scenario_id",
    "case_id",
    "actual_nfe",
    "compute_fraction",
    "uniform_method",
    "bss_method",
    "uniform_rgb_l1_closure",
    "bss_rgb_l1_closure",
    "gain_rgb_l1_closure",
    "bss_win",
    "schedule_valid",
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


def run_command(args: list[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - audit best effort
        return f"unavailable ({exc})"
    output = (completed.stdout or completed.stderr or "").strip()
    return output if output else "unavailable"


def running_in_colab() -> bool:
    if os.environ.get("COLAB_RELEASE_TAG"):
        return True
    try:
        import google.colab  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def find_column(headers: list[str], aliases: list[str]) -> str | None:
    normalized = {normalize(header): header for header in headers}
    for alias in aliases:
        found = normalized.get(normalize(alias))
        if found:
            return found
    alias_norms = [normalize(alias) for alias in aliases]
    for header in headers:
        name = normalize(header)
        if any(alias in name for alias in alias_norms):
            return header
    return None


def find_rgb_l1_closure_column(headers: list[str]) -> str | None:
    exact_aliases = [
        "rgb_l1_closure",
        "rgb_l1_closure_to_reference",
        "rgb_l1_ref_closure",
        "closure_rgb_l1",
        "rgb_l1_against_ref",
        "rgb_l1_against_reference",
        "rgb_l1",
    ]
    exact = find_column(headers, exact_aliases)
    if exact:
        return exact

    closure_candidates = []
    fallback_candidates = []
    for header in headers:
        name = normalize(header)
        has_rgb_l1 = "rgb" in name and "l1" in name
        if has_rgb_l1 and "closure" in name:
            closure_candidates.append(header)
        elif has_rgb_l1 and ("ref" in name or "reference" in name):
            fallback_candidates.append(header)
    if closure_candidates:
        return sorted(closure_candidates, key=len)[0]
    if fallback_candidates:
        return sorted(fallback_candidates, key=len)[0]
    return None


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        return rows, list(reader.fieldnames or [])


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


def format_float(value: float) -> str:
    return f"{value:.12g}"


def infer_nfe(row: dict[str, str], nfe_column: str | None, method_column: str | None) -> int | None:
    if nfe_column:
        parsed = to_int(row.get(nfe_column))
        if parsed is not None:
            return parsed
    if method_column:
        text = str(row.get(method_column, ""))
        for pattern in [r"(?:nfe|steps|step|t|uniform|bss)[_\- ]*(\d+)", r"(\d+)"]:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                parsed = int(match.group(1))
                if parsed in ALLOWED_NFE_POINTS or parsed == REFERENCE_NFE_DEFAULT:
                    return parsed
    return None


def classify_method(method: str) -> str | None:
    lowered = method.lower()
    if "reference" in lowered or "ref" in lowered and "uniform25" in lowered:
        return None
    if "bss" in lowered:
        return "bss"
    if "uniform" in lowered:
        return "uniform"
    return None


def most_common(values: list[str], default: str) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return default
    return Counter(cleaned).most_common(1)[0][0]


def boolish(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"true", "1", "yes", "y", "valid"}:
        return "true"
    if lowered in {"false", "0", "no", "n", "invalid"}:
        return "false"
    return text


def extract_nfe_from_column(column: str) -> int | None:
    name = normalize(column)
    for nfe in ALLOWED_NFE_POINTS:
        if re.search(rf"(^|_){nfe}($|_)", name):
            return nfe
        if re.search(rf"(uniform|bss|nfe|t|step|steps){nfe}($|_)", name):
            return nfe
    return None


def wide_metric_columns(headers: list[str], kind: str) -> dict[int, str]:
    matches: dict[int, str] = {}
    for header in headers:
        name = normalize(header)
        if kind not in name:
            continue
        if not ("rgb" in name and "l1" in name):
            continue
        if "closure" not in name and "ref" not in name and "reference" not in name:
            continue
        nfe = extract_nfe_from_column(header)
        if nfe in ALLOWED_NFE_POINTS:
            matches.setdefault(nfe, header)
    return matches


def collect_csv_inventory(root: Path) -> dict[str, list[str]]:
    inventory: dict[str, list[str]] = {"metrics": [], "tables": [], "manifests": []}
    for folder in inventory:
        path = root / folder
        if path.exists():
            inventory[folder] = sorted(str(item.relative_to(root)) for item in path.glob("*.csv"))
    return inventory


def expected_file_status(root: Path) -> dict[str, bool]:
    return {relative: (root / relative).exists() for relative in EXPECTED_RELATIVE_FILES}


def discover_result_roots(repo_root: Path, explicit_roots: list[Path]) -> list[Path]:
    ordered: list[Path] = []
    for root in [*explicit_roots, *CANDIDATE_RESULT_ROOTS]:
        if root not in ordered:
            ordered.append(root)

    discovered: list[Path] = []
    for path in repo_root.rglob("master_long_metrics.csv"):
        if ".git" in path.parts:
            continue
        if path.parent.name == "metrics":
            discovered.append(path.parent.parent)
    for root in discovered:
        if root not in ordered:
            ordered.append(root)
    return ordered


def choose_result_root(roots: list[Path]) -> tuple[Path | None, list[dict[str, Any]]]:
    audit: list[dict[str, Any]] = []
    best_root: Path | None = None
    best_score = -1
    for root in roots:
        status = expected_file_status(root)
        score = sum(1 for present in status.values() if present)
        manifests = sorted((root / "manifests").glob("*.csv")) if (root / "manifests").exists() else []
        score += len(manifests)
        audit.append(
            {
                "path": str(root),
                "exists": root.exists(),
                "score": score,
                "expected_status": status,
                "manifest_count": len(manifests),
            }
        )
        if root.exists() and score > best_score:
            best_root = root
            best_score = score
    if best_score <= 0:
        return None, audit
    return best_root, audit


def parse_metric_rows(source_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows, headers = read_csv_rows(source_path)
    scenario_column = find_column(headers, ["scenario_id", "scenario", "scene_id", "demo_id"])
    case_column = find_column(headers, ["case_id", "case", "example_id", "sample_id", "scenario_id"])
    method_column = find_column(headers, ["method", "method_id", "sampler", "schedule", "variant", "run_method"])
    nfe_column = find_column(headers, ["actual_nfe", "nfe", "num_inference_steps", "steps", "n_steps", "t"])
    mode_column = find_column(headers, ["mode"])
    reference_method_column = find_column(headers, ["reference_method", "ref_method", "reference"])
    reference_nfe_column = find_column(headers, ["reference_nfe", "ref_nfe"])
    schedule_valid_column = find_column(headers, ["schedule_valid", "schedule_json_valid", "is_schedule_valid"])
    metric_column = find_rgb_l1_closure_column(headers)
    uniform_wide = wide_metric_columns(headers, "uniform")
    bss_wide = wide_metric_columns(headers, "bss")

    metadata: dict[str, Any] = {
        "source_path": str(source_path),
        "headers": headers,
        "scenario_column": scenario_column,
        "case_column": case_column,
        "method_column": method_column,
        "nfe_column": nfe_column,
        "metric_column": metric_column,
        "mode_column": mode_column,
        "reference_method_column": reference_method_column,
        "reference_nfe_column": reference_nfe_column,
        "schedule_valid_column": schedule_valid_column,
        "uniform_wide_columns": uniform_wide,
        "bss_wide_columns": bss_wide,
        "rows_read": len(rows),
    }

    pair_rows: dict[tuple[str, str, int], dict[str, Any]] = defaultdict(dict)
    methods: set[str] = set()
    modes: list[str] = []
    references: list[str] = []
    reference_nfes: list[str] = []
    schedule_values: list[str] = []
    nfe_points: set[int] = set()
    scenario_ids: set[str] = set()
    case_ids: set[str] = set()

    if metric_column and method_column:
        for row_index, row in enumerate(rows):
            method = str(row.get(method_column, "")).strip()
            kind = classify_method(method)
            if kind not in {"uniform", "bss"}:
                continue
            nfe = infer_nfe(row, nfe_column, method_column)
            if nfe not in ALLOWED_NFE_POINTS:
                continue
            metric_value = to_float(row.get(metric_column))
            if metric_value is None:
                continue
            scenario_id = str(row.get(scenario_column, "") if scenario_column else "").strip()
            case_id = str(row.get(case_column, "") if case_column else "").strip()
            if not scenario_id:
                scenario_id = case_id or f"row_{row_index:05d}"
            if not case_id:
                case_id = scenario_id
            key = (case_id, scenario_id, nfe)
            pair_rows[key][kind] = {
                "method": method,
                "value": metric_value,
                "schedule_valid": boolish(row.get(schedule_valid_column)) if schedule_valid_column else "",
            }
            methods.add(method)
            nfe_points.add(nfe)
            scenario_ids.add(scenario_id)
            case_ids.add(case_id)
            if mode_column:
                modes.append(str(row.get(mode_column, "")).strip())
            if reference_method_column:
                references.append(str(row.get(reference_method_column, "")).strip())
            if reference_nfe_column:
                reference_nfes.append(str(row.get(reference_nfe_column, "")).strip())
            if schedule_valid_column:
                schedule_values.append(boolish(row.get(schedule_valid_column)))

    if uniform_wide and bss_wide:
        for row_index, row in enumerate(rows):
            scenario_id = str(row.get(scenario_column, "") if scenario_column else "").strip()
            case_id = str(row.get(case_column, "") if case_column else "").strip()
            if not scenario_id:
                scenario_id = case_id or f"row_{row_index:05d}"
            if not case_id:
                case_id = scenario_id
            for nfe in sorted(set(uniform_wide) | set(bss_wide)):
                if nfe not in ALLOWED_NFE_POINTS:
                    continue
                key = (case_id, scenario_id, nfe)
                uniform_col = uniform_wide.get(nfe)
                bss_col = bss_wide.get(nfe)
                if uniform_col:
                    value = to_float(row.get(uniform_col))
                    if value is not None:
                        pair_rows[key]["uniform"] = {
                            "method": f"uniform{nfe}",
                            "value": value,
                            "schedule_valid": boolish(row.get(schedule_valid_column)) if schedule_valid_column else "",
                        }
                        methods.add(f"uniform{nfe}")
                if bss_col:
                    value = to_float(row.get(bss_col))
                    if value is not None:
                        pair_rows[key]["bss"] = {
                            "method": f"bss{nfe}",
                            "value": value,
                            "schedule_valid": boolish(row.get(schedule_valid_column)) if schedule_valid_column else "",
                        }
                        methods.add(f"bss{nfe}")
                nfe_points.add(nfe)
                scenario_ids.add(scenario_id)
                case_ids.add(case_id)
            if mode_column:
                modes.append(str(row.get(mode_column, "")).strip())
            if reference_method_column:
                references.append(str(row.get(reference_method_column, "")).strip())
            if reference_nfe_column:
                reference_nfes.append(str(row.get(reference_nfe_column, "")).strip())
            if schedule_valid_column:
                schedule_values.append(boolish(row.get(schedule_valid_column)))

    metadata.update(
        {
            "methods": sorted(methods),
            "modes": sorted(set(value for value in modes if value)),
            "reference_methods": sorted(set(value for value in references if value)),
            "reference_nfes": sorted(set(value for value in reference_nfes if value)),
            "schedule_values": schedule_values,
            "nfe_points": sorted(nfe_points),
            "scenario_ids": sorted(scenario_ids),
            "case_ids": sorted(case_ids),
            "pair_keys": pair_rows,
        }
    )

    reference_method = most_common(references, REFERENCE_METHOD_DEFAULT)
    reference_nfe_text = most_common(reference_nfes, str(REFERENCE_NFE_DEFAULT))
    reference_nfe = to_int(reference_nfe_text) or REFERENCE_NFE_DEFAULT
    mode = most_common(modes, MODE_DEFAULT)

    output_rows: list[dict[str, str]] = []
    for (case_id, scenario_id, nfe), pair in sorted(pair_rows.items(), key=lambda item: (item[0][1], item[0][0], item[0][2])):
        uniform = pair.get("uniform")
        bss = pair.get("bss")
        if not uniform or not bss:
            continue
        uniform_value = float(uniform["value"])
        bss_value = float(bss["value"])
        gain = bss_value - uniform_value
        schedule_valid = bss.get("schedule_valid") or uniform.get("schedule_valid") or ""
        output_rows.append(
            {
                "model_id": "UniLumos",
                "protocol": "official_demos",
                "mode": mode,
                "reference_method": reference_method,
                "reference_nfe": str(reference_nfe),
                "scenario_id": scenario_id,
                "case_id": case_id,
                "actual_nfe": str(nfe),
                "compute_fraction": format_float(nfe / reference_nfe),
                "uniform_method": str(uniform["method"]),
                "bss_method": str(bss["method"]),
                "uniform_rgb_l1_closure": format_float(uniform_value),
                "bss_rgb_l1_closure": format_float(bss_value),
                "gain_rgb_l1_closure": format_float(gain),
                "bss_win": "true" if gain > 0 else "false",
                "schedule_valid": schedule_valid,
            }
        )
    return output_rows, metadata


def candidate_metric_files(result_root: Path) -> list[Path]:
    ordered = [
        result_root / "metrics" / "master_long_metrics.csv",
        result_root / "metrics" / "per_case_metrics.csv",
        result_root / "metrics" / "metrics_against_ref.csv",
    ]
    return [path for path in ordered if path.exists()]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown_bullets(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def pair_status_from_rows(rows: list[dict[str, str]]) -> list[str]:
    counts: dict[int, int] = defaultdict(int)
    for row in rows:
        nfe = to_int(row.get("actual_nfe"))
        if nfe is not None:
            counts[nfe] += 1
    return [f"NFE {nfe}: {counts.get(nfe, 0)} complete uniformT/bssT case pairs" for nfe in ALLOWED_NFE_POINTS]


def write_audit_report(
    output_root: Path,
    repo_root: Path,
    result_root: Path | None,
    root_audit: list[dict[str, Any]],
    selected_inventory: dict[str, list[str]] | None,
    metadata: dict[str, Any] | None,
    gain_rows: list[dict[str, str]],
    missing: list[str],
) -> None:
    remote = run_command(["git", "remote", "-v"], repo_root)
    branch = run_command(["git", "branch", "--show-current"], repo_root)
    commit = run_command(["git", "rev-parse", "HEAD"], repo_root)
    dirty = run_command(["git", "status", "--short"], repo_root)
    dirty_status = dirty if dirty != "unavailable" else "unavailable"
    if dirty_status == "":
        dirty_status = "clean"

    scenario_ids = sorted({row["scenario_id"] for row in gain_rows})
    case_ids = sorted({row["case_id"] for row in gain_rows})
    methods = metadata.get("methods", []) if metadata else []
    nfe_points = metadata.get("nfe_points", []) if metadata else []
    modes = metadata.get("modes", []) if metadata else []
    reference_methods = metadata.get("reference_methods", []) if metadata else []
    reference_nfes = metadata.get("reference_nfes", []) if metadata else []
    schedule_values = metadata.get("schedule_values", []) if metadata else []
    schedule_counter = Counter(value for value in schedule_values if value)

    root_lines = []
    for entry in root_audit:
        found = [name for name, present in entry["expected_status"].items() if present]
        root_lines.append(
            f"- `{entry['path']}`: exists={entry['exists']}, expected_csvs_found={len(found)}, manifests_found={entry['manifest_count']}"
        )
        for name in found:
            root_lines.append(f"  - found `{name}`")

    inventory_lines: list[str] = []
    if selected_inventory:
        for folder, files in selected_inventory.items():
            inventory_lines.append(f"- {folder}: {len(files)} csv file(s)")
            for file_name in files:
                inventory_lines.append(f"  - `{file_name}`")
    else:
        inventory_lines.append("- no selected result folder")

    report = f"""# UniLumos BDS Artifact Audit

## Environment

- repo path: `{repo_root}`
- git remote:

```text
{remote}
```

- current branch: `{branch}`
- commit hash: `{commit}`
- dirty status:

```text
{dirty_status}
```

- Python version: `{platform.python_version()}`
- platform: `{platform.platform()}`
- running in Colab: `{running_in_colab()}`

## Result Folder Search

{chr(10).join(root_lines) if root_lines else "- no candidate folders checked"}

- selected result folder: `{result_root if result_root else "none"}`

## Found Metrics, Tables, And Manifests

{chr(10).join(inventory_lines)}

## Official Demo Data Audit

- number of official demo cases with complete exact same-compute pairs: {len(case_ids)}
- expected official demo cases: 20
- scenario ids: {", ".join(scenario_ids) if scenario_ids else "unavailable"}
- mode: {", ".join(modes) if modes else f"unavailable, default would be {MODE_DEFAULT}"}
- reference method: {", ".join(reference_methods) if reference_methods else f"unavailable, expected {REFERENCE_METHOD_DEFAULT}"}
- reference NFE: {", ".join(reference_nfes) if reference_nfes else f"unavailable, expected {REFERENCE_NFE_DEFAULT}"}
- methods found: {", ".join(methods) if methods else "unavailable"}
- NFE points found: {", ".join(str(point) for point in nfe_points) if nfe_points else "unavailable"}
- RGB-L1 closure available per case: {"yes" if gain_rows else "no"}
- schedule validity status: {dict(schedule_counter) if schedule_counter else "unavailable"}

## Same-Compute Pair Availability

{chr(10).join(f"- {line}" for line in pair_status_from_rows(gain_rows))}

## Missing Or Blocking Items

{markdown_bullets(missing)}

## Audit Conclusion

{"Required inputs are present and `metrics/unilumos_same_compute_gain_long.csv` was created." if not missing else "BDS computation is blocked. The missing items above must be provided before calibration/holdout scoring can be computed."}
"""
    (output_root / "reports" / "00_artifact_audit.md").write_text(report, encoding="utf-8")


def write_blocked_final_report(output_root: Path, missing: list[str]) -> None:
    report = f"""# Final UniLumos BDS Certificate Report

## 1. Purpose

Run a calibration-to-holdout BSS Deployment Score analysis on existing UniLumos official-demo results using RGB-L1 closure.

## 2. Why BDS Is Non-Post-Hoc

The intended protocol is calibration official demos -> BDS -> predicted deployment -> holdout verification. This run did not reach scoring because the required existing official-demo metrics were not available in this workspace.

## 3. Artifact Audit

See `reports/00_artifact_audit.md`.

## 4. Same-Compute Gain Table Summary

Not computed. The same-compute gain table requires per-case RGB-L1 closure for exact uniformT and bssT pairs.

## 5. Calibration/Holdout Splits

Not computed because no official-demo per-case gain table is available.

## 6. BDS-Low And BDS-All Results

Not computed.

## 7. Holdout Verification

Not computed.

## 8. Comparison With Full-Run Summary

Not computed because the expected full-run summary table was not found.

## 9. Final UniLumos Deployment Verdict

Blocked: insufficient artifacts. No Low-only, Green, Reject, or Mixed certificate was issued.

## 10. Caveats

- official demos only
- RGB-L1 closure to `reference_uniform25`
- NFE as compute proxy
- no universal claim
- this blocked report does not contain a BDS estimate

## 11. Recommended Next Experiment

- solver-coordinate ablation
- sample_shift ablation
- Model C

## Missing Inputs

{markdown_bullets(missing)}
"""
    (output_root / "reports" / "FINAL_UNILUMOS_BDS_CERTIFICATE_REPORT.md").write_text(report, encoding="utf-8")


def mirror_if_colab(output_root: Path) -> None:
    mirror_root = Path("/content/drive/MyDrive/Colab_Projects/UniLumos-BDS/unilumos_bds_certificate_v1")
    if running_in_colab() and mirror_root.parent.exists() and output_root.resolve() != mirror_root.resolve():
        shutil.copytree(output_root, mirror_root, dirs_exist_ok=True)


def build_gain_table(repo_root: Path, output_root: Path, explicit_roots: list[Path]) -> int:
    ensure_output_dirs(output_root)
    roots = discover_result_roots(repo_root, explicit_roots)
    result_root, root_audit = choose_result_root(roots)

    missing: list[str] = []
    gain_rows: list[dict[str, str]] = []
    metadata: dict[str, Any] | None = None
    inventory: dict[str, list[str]] | None = None

    if result_root is None:
        missing.extend(
            [
                "No existing UniLumos BSS result folder was found in the expected /content locations or under this repository.",
                "Missing metrics/master_long_metrics.csv.",
                "Missing metrics/per_case_metrics.csv.",
                "Missing metrics/metrics_against_ref.csv.",
                "Missing tables/cross_model_summary_row.csv.",
                "Missing manifests/*.csv.",
            ]
        )
    else:
        inventory = collect_csv_inventory(result_root)
        metric_files = candidate_metric_files(result_root)
        if not metric_files:
            missing.append("No per-case metrics CSV found. Expected one of metrics/master_long_metrics.csv, metrics/per_case_metrics.csv, or metrics/metrics_against_ref.csv.")
        else:
            parse_attempts: list[str] = []
            for metric_file in metric_files:
                rows, candidate_metadata = parse_metric_rows(metric_file)
                parse_attempts.append(f"{metric_file}: {len(rows)} complete pairs")
                if rows:
                    gain_rows = rows
                    metadata = candidate_metadata
                    break
                metadata = candidate_metadata
            if not gain_rows:
                missing.append(
                    "Unable to construct per-case RGB-L1 closure same-compute pairs from available metric CSVs. "
                    "Need rows or wide columns containing scenario/case id, method, exact NFE, and RGB-L1 closure for uniformT and bssT."
                )
                missing.extend(parse_attempts)

    if gain_rows:
        scenario_count = len({row["scenario_id"] for row in gain_rows})
        row_count = len(gain_rows)
        if scenario_count != 20:
            missing.append(f"Expected 20 official demo scenarios, found {scenario_count}.")
        if row_count != 20 * 4 and row_count != 20 * 5:
            missing.append(f"Expected approximately 80 or 100 exact same-compute rows for 20 cases, found {row_count}.")
        write_csv(output_root / "metrics" / "unilumos_same_compute_gain_long.csv", gain_rows, GAIN_FIELDNAMES)

    write_audit_report(output_root, repo_root, result_root, root_audit, inventory, metadata, gain_rows, missing)
    if missing:
        write_blocked_final_report(output_root, missing)
    mirror_if_colab(output_root)
    return 0 if gain_rows and not missing else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build UniLumos same-compute RGB-L1 closure gain table for BDS.")
    parser.add_argument("--repo-root", type=Path, default=repo_root_from(Path.cwd()))
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--input-root", type=Path, action="append", default=[], help="Explicit UniLumos BSS result root. Can be passed multiple times.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_root = (repo_root / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root
    explicit_roots = [path.resolve() if not path.is_absolute() else path for path in args.input_root]
    return build_gain_table(repo_root, output_root, explicit_roots)


if __name__ == "__main__":
    raise SystemExit(main())
