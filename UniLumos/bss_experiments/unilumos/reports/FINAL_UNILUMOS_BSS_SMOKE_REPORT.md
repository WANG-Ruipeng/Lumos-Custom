# Final UniLumos BSS Smoke Report

Status: code scaffold and schedule integration prepared locally. Local
lightweight validation passed. Model smoke execution is intended for Colab with
weights on Google Drive.

## Purpose

Create a UniLumos official-protocol smoke test for Boundary-Split Sampling as
Model B evidence beyond Relit-LiVE.

## Relation To Model A

The one-case smoke mirrors the Relit-LiVE comparison structure:
`uniform8`, `uniform10`, `bss10`, and a high/default reference. For UniLumos,
the initial reference is `uniform25`, matching the official default in the
inference scripts.

## Environment And Git State

See `reports/00_current_state.md`.

## Selected Protocol

Initial mode: `abc`, using one row from official `examples_refined.csv`.

Fallback order remains `abc`, `ab`, `ac`, `a`, then `image`.

## BSS Implementation Summary

BSS is implemented only as a sigma-grid modification in
`RFLOW_WANX21_T2V.sample`. Uniform sampling still uses the official
`get_sampling_sigmas(sample_steps, sample_shift)` path.

## Local Validation

- Parsed 23 Python files with AST parsing.
- Validated toy bss10 = base8 + split first/last.
- Confirmed bss10 has 10 coordinates and is not uniform10.
- Generated a one-case manifest in a temporary folder.
- Dry-ran the runner and produced commands for uniform8, uniform10, bss10, and reference_uniform25.
- Validated notebook JSON.

## Schedule Validation
Toy validation passed locally. Full schedule JSON validation is pending Colab run output.

## One-Case Smoke Results

Pending Colab run.

## Side-By-Side Outputs

Pending Colab run.

## Lumos Family Summary

UniLumos is the Model B target. LumosBench is better reserved for later
attribute controllability evaluation and should not be part of the first
same-NFE sampler smoke.

## Verdict

Run the notebook in Colab with Drive weights. If schedule validation and one
case outputs pass, expand to more official UniLumos examples. If video mode is
too heavy or weights are unavailable, fall back to image mode.
