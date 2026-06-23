# Dry Run Commands

Local validation generated the expected one-case commands for:

- `uniform8`
- `uniform10`
- `bss10`
- `reference_uniform25`

Colab command template:

```bash
python bss_experiments/unilumos/scripts/make_manifest_unilumos_official_smoke.py \
  --experiment_root /content/drive/MyDrive/Colab_Projects/UniLumos-BSS-Runs/model_b_unilumos_official_bss_smoke_v1 \
  --max_cases 1 \
  --mode abc
```

Then dry-run:

```bash
python bss_experiments/unilumos/scripts/run_manifest.py \
  --manifest /content/drive/MyDrive/Colab_Projects/UniLumos-BSS-Runs/model_b_unilumos_official_bss_smoke_v1/manifests/unilumos_official_smoke_manifest.csv \
  --weights_root /content/drive/MyDrive/Colab_Projects/UniLumos/weights \
  --dry_run
```

Then execute after verifying Drive weights:

```bash
python bss_experiments/unilumos/scripts/run_manifest.py \
  --manifest /content/drive/MyDrive/Colab_Projects/UniLumos-BSS-Runs/model_b_unilumos_official_bss_smoke_v1/manifests/unilumos_official_smoke_manifest.csv \
  --weights_root /content/drive/MyDrive/Colab_Projects/UniLumos/weights \
  --resume
```

The runner executes from the inner `UniLumos` code directory and writes outputs,
logs, schedules, metrics, and figures under the experiment root.
