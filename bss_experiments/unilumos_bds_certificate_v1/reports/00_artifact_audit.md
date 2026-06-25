# UniLumos BDS Artifact Audit

## Environment

- repo path: `E:\UniLumos`
- git remote:

```text
fork	https://github.com/WANG-Ruipeng/Lumos-Custom.git (fetch)
fork	https://github.com/WANG-Ruipeng/Lumos-Custom.git (push)
origin	https://github.com/alibaba-damo-academy/Lumos-Custom.git (fetch)
origin	https://github.com/alibaba-damo-academy/Lumos-Custom.git (push)
```

- current branch: `bss-unilumos-official-smoke`
- commit hash: `d70cdd322ce799a468005f382906b1b217588046`
- dirty status:

```text
M Prompt.txt
?? bss_experiments/
```

- Python version: `3.14.2`
- platform: `Windows-11-10.0.26200-SP0`
- running in Colab: `False`

## Result Folder Search

- `\content\drive\MyDrive\Colab_Projects\UniLumos-BSS-Runs\model_b_unilumos_official_all_demos_bss_v1`: exists=False, expected_csvs_found=0, manifests_found=0
- `\content\UniLumos-BSS-Runs\model_b_unilumos_official_all_demos_bss_v1`: exists=False, expected_csvs_found=0, manifests_found=0
- `\content\drive\MyDrive\Colab_Projects\UniLumos-BSS-Runs\model_b_unilumos_official_bss_smoke_v1`: exists=False, expected_csvs_found=0, manifests_found=0

- selected result folder: `none`

## Found Metrics, Tables, And Manifests

- no selected result folder

## Official Demo Data Audit

- number of official demo cases with complete exact same-compute pairs: 0
- expected official demo cases: 20
- scenario ids: unavailable
- mode: unavailable, default would be abc
- reference method: unavailable, expected reference_uniform25
- reference NFE: unavailable, expected 25
- methods found: unavailable
- NFE points found: unavailable
- RGB-L1 closure available per case: no
- schedule validity status: unavailable

## Same-Compute Pair Availability

- NFE 10: 0 complete uniformT/bssT case pairs
- NFE 12: 0 complete uniformT/bssT case pairs
- NFE 16: 0 complete uniformT/bssT case pairs
- NFE 20: 0 complete uniformT/bssT case pairs
- NFE 24: 0 complete uniformT/bssT case pairs

## Missing Or Blocking Items

- No existing UniLumos BSS result folder was found in the expected /content locations or under this repository.
- Missing metrics/master_long_metrics.csv.
- Missing metrics/per_case_metrics.csv.
- Missing metrics/metrics_against_ref.csv.
- Missing tables/cross_model_summary_row.csv.
- Missing manifests/*.csv.

## Audit Conclusion

BDS computation is blocked. The missing items above must be provided before calibration/holdout scoring can be computed.
