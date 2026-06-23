# UniLumos Official Demo Audit

## Environment

- current path: `E:\UniLumos`
- git remotes: `fork	https://github.com/WANG-Ruipeng/Lumos-Custom.git (fetch); fork	https://github.com/WANG-Ruipeng/Lumos-Custom.git (push); origin	https://github.com/alibaba-damo-academy/Lumos-Custom.git (fetch); origin	https://github.com/alibaba-damo-academy/Lumos-Custom.git (push)`
- branch: `bss-unilumos-official-smoke`
- commit hash: `1e2c3265fc550ae57c299273c021b16b176fde6c`
- dirty status: `True`
- Python version: `3.14.2`
- GPU info: not available in local Windows workspace
- running locally or in Colab: local workspace audit; Colab runtime is used for inference
- Google Drive mounted: not mounted locally

## Official Demo Sources

- `UniLumos/run_infer.sh` invokes `torchrun --nproc_per_node=1 unilumos_infer_abc.py`.
- `UniLumos/examples/examples_refined.csv` directly enumerates official abc demo scenarios.
- `UniLumos/examples/` contains foreground videos, masks, per-example background videos, and official result examples.
- Inference entry points exist for `abc`, `ab`, `ac`, `a`, and `image`; the official run script selects `abc`.

## Official Demo Scenario Definition

A UniLumos official demo scenario is one complete row directly enumerated by `examples/examples_refined.csv` or invoked by the official scripts. This audit does not create any new foreground/background/prompt combinations.

## Scenario Counts

- abc scenarios from `examples_refined.csv`: 20
- examples: example_0, example_1, example_2, example_3
- backgrounds: bg_video_1, bg_video_2, bg_video_3, bg_video_4, bg_video_5
- selected main mode: `abc`
- reason: `run_infer.sh` invokes `unilumos_infer_abc.py`, and the CSV enumerates paired foreground/background/prompt rows closest to the Relit-LiVE official protocol style.

## Missing Local Weights

The local workspace does not contain heavyweight model files. Colab runs should use the staged Drive weights path already verified in the smoke notebook.
- `E:\UniLumos\UniLumos\UniLumos\weights\models_t5_umt5-xxl-enc-bf16.pth`
- `E:\UniLumos\UniLumos\UniLumos\weights\umt5-xxl`
- `E:\UniLumos\UniLumos\UniLumos\weights\vae.pth`
- `E:\UniLumos\UniLumos\UniLumos\weights\unilumos.pt`

## Deliverable Scenario Table

| scenario_id | mode | official source | prompt/caption | foreground/input | background/condition | output default | notes |
|---|---|---|---|---|---|---|---|
| example_0_bg_video_1 | abc | `examples/examples_refined.csv` | A woman stands by a window, gazing out at a cityscape dominated by modern skyscrapers. The foreground features a blurred glass surface with vertical lines, reflecting the surrou... | ./examples/example_0/example_0.mp4 | examples/example_0/bg_path/bg_video_1.mp4 | examples/results/example_0_bg_video_1_gen.mp4 | official CSV row |
| example_0_bg_video_2 | abc | `examples/examples_refined.csv` | A woman stands by a window, gazing out at a cityscape dominated by modern skyscrapers. The foreground features a blurred glass surface with vertical lines, reflecting the surrou... | ./examples/example_0/example_0.mp4 | examples/example_0/bg_path/bg_video_2.mp4 | examples/results/example_0_bg_video_2_gen.mp4 | official CSV row |
| example_0_bg_video_3 | abc | `examples/examples_refined.csv` | A woman stands by a window, gazing out at a cityscape dominated by modern skyscrapers. The foreground features a blurred glass surface with vertical lines, reflecting the surrou... | ./examples/example_0/example_0.mp4 | examples/example_0/bg_path/bg_video_3.mp4 | examples/results/example_0_bg_video_3_gen.mp4 | official CSV row |
| example_0_bg_video_4 | abc | `examples/examples_refined.csv` | A woman stands by a window, gazing out at a cityscape dominated by modern skyscrapers. The foreground features a blurred glass surface with vertical lines, reflecting the surrou... | ./examples/example_0/example_0.mp4 | examples/example_0/bg_path/bg_video_4.mp4 | examples/results/example_0_bg_video_4_gen.mp4 | official CSV row |
| example_0_bg_video_5 | abc | `examples/examples_refined.csv` | A woman stands by a window, gazing out at a cityscape dominated by modern skyscrapers. The foreground features a blurred glass surface with vertical lines, reflecting the surrou... | ./examples/example_0/example_0.mp4 | examples/example_0/bg_path/bg_video_5.mp4 | examples/results/example_0_bg_video_5_gen.mp4 | official CSV row |
| example_1_bg_video_1 | abc | `examples/examples_refined.csv` | A woman with shoulder-length brown hair stands in front of a wooden lattice wall, captured from an eye-level camera angle. She is wearing a black dress with thin straps that cro... | ./examples/example_1/example_1.mp4 | examples/example_1/bg_path/bg_video_1.mp4 | examples/results/example_1_bg_video_1_gen.mp4 | official CSV row |
| example_1_bg_video_2 | abc | `examples/examples_refined.csv` | A woman with shoulder-length brown hair stands in front of a wooden lattice wall, captured from an eye-level camera angle. She is wearing a black dress with thin straps that cro... | ./examples/example_1/example_1.mp4 | examples/example_1/bg_path/bg_video_2.mp4 | examples/results/example_1_bg_video_2_gen.mp4 | official CSV row |
| example_1_bg_video_3 | abc | `examples/examples_refined.csv` | A woman with shoulder-length brown hair stands in front of a wooden lattice wall, captured from an eye-level camera angle. She is wearing a black dress with thin straps that cro... | ./examples/example_1/example_1.mp4 | examples/example_1/bg_path/bg_video_3.mp4 | examples/results/example_1_bg_video_3_gen.mp4 | official CSV row |
| example_1_bg_video_4 | abc | `examples/examples_refined.csv` | A woman with shoulder-length brown hair stands in front of a wooden lattice wall, captured from an eye-level camera angle. She is wearing a black dress with thin straps that cro... | ./examples/example_1/example_1.mp4 | examples/example_1/bg_path/bg_video_4.mp4 | examples/results/example_1_bg_video_4_gen.mp4 | official CSV row |
| example_1_bg_video_5 | abc | `examples/examples_refined.csv` | A woman with shoulder-length brown hair stands in front of a wooden lattice wall, captured from an eye-level camera angle. She is wearing a black dress with thin straps that cro... | ./examples/example_1/example_1.mp4 | examples/example_1/bg_path/bg_video_5.mp4 | examples/results/example_1_bg_video_5_gen.mp4 | official CSV row |
| example_2_bg_video_1 | abc | `examples/examples_refined.csv` | A man with short, dark hair and a light beard, wearing a light gray button-up shirt with a blue collar, sits at a table, looking contemplative. The shirt is slightly wrinkled, a... | ./examples/example_2/example_2.mp4 | examples/example_2/bg_path/bg_video_1.mp4 | examples/results/example_2_bg_video_1_gen.mp4 | official CSV row |
| example_2_bg_video_2 | abc | `examples/examples_refined.csv` | A man with short, dark hair and a light beard, wearing a light gray button-up shirt with a blue collar, sits at a table, looking contemplative. The shirt is slightly wrinkled, a... | ./examples/example_2/example_2.mp4 | examples/example_2/bg_path/bg_video_2.mp4 | examples/results/example_2_bg_video_2_gen.mp4 | official CSV row |
| example_2_bg_video_3 | abc | `examples/examples_refined.csv` | A man with short, dark hair and a light beard, wearing a light gray button-up shirt with a blue collar, sits at a table, looking contemplative. The shirt is slightly wrinkled, a... | ./examples/example_2/example_2.mp4 | examples/example_2/bg_path/bg_video_3.mp4 | examples/results/example_2_bg_video_3_gen.mp4 | official CSV row |
| example_2_bg_video_4 | abc | `examples/examples_refined.csv` | A man with short, dark hair and a light beard, wearing a light gray button-up shirt with a blue collar, sits at a table, looking contemplative. The shirt is slightly wrinkled, a... | ./examples/example_2/example_2.mp4 | examples/example_2/bg_path/bg_video_4.mp4 | examples/results/example_2_bg_video_4_gen.mp4 | official CSV row |
| example_2_bg_video_5 | abc | `examples/examples_refined.csv` | A man with short, dark hair and a light beard, wearing a light gray button-up shirt with a blue collar, sits at a table, looking contemplative. The shirt is slightly wrinkled, a... | ./examples/example_2/example_2.mp4 | examples/example_2/bg_path/bg_video_5.mp4 | examples/results/example_2_bg_video_5_gen.mp4 | official CSV row |
| example_3_bg_video_1 | abc | `examples/examples_refined.csv` | A man with a beard, wearing a dark shirt and a light-colored hat, is playing a black electric bass guitar in a medium shot. The bass guitar features a white pickguard with a gli... | ./examples/example_3/example_3.mp4 | examples/example_3/bg_path/bg_video_1.mp4 | examples/results/example_3_bg_video_1_gen.mp4 | official CSV row |
| example_3_bg_video_2 | abc | `examples/examples_refined.csv` | A man with a beard, wearing a dark shirt and a light-colored hat, is playing a black electric bass guitar in a medium shot. The bass guitar features a white pickguard with a gli... | ./examples/example_3/example_3.mp4 | examples/example_3/bg_path/bg_video_2.mp4 | examples/results/example_3_bg_video_2_gen.mp4 | official CSV row |
| example_3_bg_video_3 | abc | `examples/examples_refined.csv` | A man with a beard, wearing a dark shirt and a light-colored hat, is playing a black electric bass guitar in a medium shot. The bass guitar features a white pickguard with a gli... | ./examples/example_3/example_3.mp4 | examples/example_3/bg_path/bg_video_3.mp4 | examples/results/example_3_bg_video_3_gen.mp4 | official CSV row |
| example_3_bg_video_4 | abc | `examples/examples_refined.csv` | A man with a beard, wearing a dark shirt and a light-colored hat, is playing a black electric bass guitar in a medium shot. The bass guitar features a white pickguard with a gli... | ./examples/example_3/example_3.mp4 | examples/example_3/bg_path/bg_video_4.mp4 | examples/results/example_3_bg_video_4_gen.mp4 | official CSV row |
| example_3_bg_video_5 | abc | `examples/examples_refined.csv` | A man with a beard, wearing a dark shirt and a light-colored hat, is playing a black electric bass guitar in a medium shot. The bass guitar features a white pickguard with a gli... | ./examples/example_3/example_3.mp4 | examples/example_3/bg_path/bg_video_5.mp4 | examples/results/example_3_bg_video_5_gen.mp4 | official CSV row |

## Schedule-Control Search Summary

- `RFLOW_WANX21_T2V.py` owns `get_sampling_sigmas`, `retrieve_timesteps`, and `scheduler.sample`.
- Inference scripts expose `sample_steps`, `sample_shift`, `seed`, `sampler_mode`, `base_sample_steps`, `split_pairs`, and schedule JSON dumping on this branch.
- Uniform mode keeps the official shifted uniform sigma path. BSS mode uses base `T-2` plus first/last interval splits.

