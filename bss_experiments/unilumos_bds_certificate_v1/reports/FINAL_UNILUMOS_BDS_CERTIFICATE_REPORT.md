# Final UniLumos BDS Certificate Report

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

- No existing UniLumos BSS result folder was found in the expected /content locations or under this repository.
- Missing metrics/master_long_metrics.csv.
- Missing metrics/per_case_metrics.csv.
- Missing metrics/metrics_against_ref.csv.
- Missing tables/cross_model_summary_row.csv.
- Missing manifests/*.csv.
