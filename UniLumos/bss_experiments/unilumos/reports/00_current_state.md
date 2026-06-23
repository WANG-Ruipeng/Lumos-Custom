# Phase 0 Current State Audit

Date: 2026-06-23

This audit was run in local code-edit mode. Model execution is intended for
Google Colab with weights stored on Google Drive. No model inference, training,
dependency installation, or weight modification was performed locally.

## Environment

| Item | Value |
|---|---|
| Local pwd | `E:\UniLumos` |
| Task root | `E:\UniLumos\UniLumos` |
| UniLumos code root | `E:\UniLumos\UniLumos\UniLumos` |
| Git remote | `origin https://github.com/alibaba-damo-academy/Lumos-Custom.git` |
| Current branch | `bss-unilumos-official-smoke` |
| HEAD | `1856e13710758c7e81686263d8b8a58cc83c99b8` |
| Git status before edits | `?? Prompt.txt` |
| Python | `Python 3.14.2` from WindowsApps/local Python launcher |
| Local GPU | `NVIDIA GeForce RTX 5080, 16303 MiB, driver 591.86` |
| Colab | Not local Colab |
| Google Drive mounted | Not mounted locally |

## Repository Notes

The upstream repository contains a Windows-incompatible file path:
`UniLumos/LumosBench/requirements.txt ` with a trailing space. The local clone
uses sparse checkout and keeps the main UniLumos project checked out. LumosBench
is audited through Git tree reads instead of full checkout.

## File Audit

| Item | Found? | Path / Evidence | Notes | Missing action |
|---|---:|---|---|---|
| Prompt backup | Yes | `Prompt.txt` | User reference file, untracked | Do not include in commit unless requested |
| Top-level UniLumos README | Yes | `UniLumos/README.md` | Checked out | None |
| Main code root | Yes | `UniLumos/UniLumos` | Contains inference scripts, src, examples, weights | None |
| `run_infer.sh` | Yes | `UniLumos/UniLumos/run_infer.sh` | Official command runs `torchrun --nproc_per_node=1 unilumos_infer_abc.py` | Update docs/runner, preserve official script unless needed |
| `unilumos_infer_abc.py` | Yes | `UniLumos/UniLumos/unilumos_infer_abc.py` | Captions + foreground + background | Patch schedule CLI |
| `unilumos_infer_ab.py` | Yes | `UniLumos/UniLumos/unilumos_infer_ab.py` | Captions + foreground | Patch schedule CLI |
| `unilumos_infer_ac.py` | Yes | `UniLumos/UniLumos/unilumos_infer_ac.py` | Captions + background | Patch schedule CLI |
| `unilumos_infer_a.py` | Yes | `UniLumos/UniLumos/unilumos_infer_a.py` | Captions only | Patch schedule CLI |
| `unilumos_infer_image.py` | Yes | `UniLumos/UniLumos/unilumos_infer_image.py` | Image/single-frame path | Patch schedule CLI |
| `RFLOW_WANX21_T2V.py` | Yes | `UniLumos/UniLumos/src/schedulers/RFLOW_WANX21_T2V.py` | Has `get_sampling_sigmas` and `retrieve_timesteps(sigmas=...)` | Add BSS/custom schedule mode |
| `rectified_flow.py` | Yes | `UniLumos/UniLumos/src/schedulers/rectified_flow.py` | `set_timesteps` supports custom `sigmas` | No direct patch expected |
| Official examples | Yes | `UniLumos/UniLumos/examples` | `examples_refined.csv`, 4 foreground examples, 5 backgrounds each, official generated sample outputs | Use one CSV row for first smoke |
| Weights | Placeholder only | `UniLumos/UniLumos/weights/readme.txt` | Required model files are missing locally | Provide weights on Colab/Drive |
| LumosBench | Git tree only | `git ls-tree HEAD UniLumos/LumosBench` | Sparse checkout excludes trailing-space requirements path | Audit only; do not run now |

## Code Search Findings

| Search item | Found? | Evidence | Notes | Missing action |
|---|---:|---|---|---|
| `sample_steps` | Yes | All five inference scripts pass `sample_steps=25`; scheduler default is 25 | Hard-coded in inference | Replace with CLI arg |
| `sample_shift` | Yes | All five inference scripts pass `sample_shift=8.0`; scheduler default is 8.0 | Hard-coded in inference | Replace with CLI arg |
| `RFLOW_WANX21_T2V` | Yes | Imported by all five inference scripts | Single scheduler integration point | Patch scheduler only |
| `get_sampling_sigmas` | Yes | `RFLOW_WANX21_T2V.py` lines near top | Official shifted sigma formula | Reuse exactly for uniform/base |
| `retrieve_timesteps` | Yes | `RFLOW_WANX21_T2V.py` supports `sigmas` | Custom sigma hook exists | Pass BSS/custom sigmas |
| `set_timesteps` | Yes | `rectified_flow.py` accepts `sigmas` | Appends terminal sigma internally | Keep terminal coord recorded as `0.0` |
| `manual_seed` | Yes | All five inference scripts use `manual_seed(0)` | Noise seed hard-coded | Replace with `args.seed` |
| `set_random_seed` | Yes | All five inference scripts use `set_random_seed(seed=0)` | Global seed hard-coded | Replace with `args.seed` |
| Output save paths | Yes | `save_dir` defaults to official examples results dirs | Must avoid overwriting official results | Runner uses separate experiment output root |

## Official Example Inputs

`examples_refined.csv` is present. The first row is an `abc` case:

- foreground/reference: `./examples/example_0/example_0.mp4`
- mask: `./examples/example_0/example_0_mask.mp4`
- degradation: `./examples/example_0/example_0.mp4`
- background: `examples/example_0/bg_path/bg_video_1.mp4`
- size: `480x832`
- duration: `4.08`

## Weights

Local `weights` contains only `readme.txt`. Expected runtime files include:

- `weights/models_t5_umt5-xxl-enc-bf16.pth`
- `weights/umt5-xxl`
- `weights/vae.pth`
- `weights/unilumos.pt`

No local smoke result can be produced without these. The planned notebook and
runner allow these paths to point at Google Drive.

## LumosBench Audit

LumosBench exists in the Git tree and includes:

- `assets/pipline_caption.jpg`
- `jsonls/gen_prompts.py`
- `jsonls/lighting_combinations.jsonl`
- `jsonls/test_gen_videos.jsonl`
- `main.py`
- `src/_predictor.py`
- `src/_prompts.py`
- `src/_quantitative_utils.py`
- `src/_vllm_model.py`
- `weights/readme.txt`

Its README says it evaluates six lighting attributes: direction, light source
type, intensity, color temperature, temporal dynamics, and optical phenomena.
It requires Qwen2.5-VL weights for the qualitative VLM evaluation. This is too
heavy for the first BSS same-NFE smoke and should remain appendix/planning work.
