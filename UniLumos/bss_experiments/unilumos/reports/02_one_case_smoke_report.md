# One-Case Smoke Report

Status: pending Colab execution.

Local code-only validation completed:

- Python syntax parse passed for BSS scripts, patched inference scripts, and scheduler.
- Toy BSS validation passed for `bss10 = base8 + split first/last`.
- Manifest generation passed for first official `abc` case.
- Runner dry-run produced four commands: `uniform8`, `uniform10`, `bss10`, and `reference_uniform25`.

Selected smoke case:

- `case_id`: `example_0_bg_video_1`
- mode: `abc`
- foreground/reference: `./examples/example_0/example_0.mp4`
- mask: `./examples/example_0/example_0_mask.mp4`
- degradation: `./examples/example_0/example_0.mp4`
- background: `examples/example_0/bg_path/bg_video_1.mp4`
- reference method: `reference_uniform25`

Local weights are missing, so no output videos or metrics were generated
locally. Execute the notebook in Colab with Drive weights to complete this
report.
