# UniLumos Integration

Patched entry points:

- `UniLumos/unilumos_infer_abc.py`
- `UniLumos/unilumos_infer_ab.py`
- `UniLumos/unilumos_infer_ac.py`
- `UniLumos/unilumos_infer_a.py`
- `UniLumos/unilumos_infer_image.py`
- `UniLumos/src/schedulers/RFLOW_WANX21_T2V.py`

Added CLI controls:

- `--sample_steps`
- `--sample_shift`
- `--seed`
- `--sampler_mode uniform|bss|custom_sigmas`
- `--base_sample_steps`
- `--split_pairs`
- `--custom_sigmas`
- `--dump_schedule_json`
- `--method`
- `--max_cases`
- `--case_filter`

The official uniform path still calls `get_sampling_sigmas(sample_steps,
sample_shift)` and then `retrieve_timesteps(..., sigmas=sampling_sigmas,
shift=1)`.

Colab execution should run from the inner UniLumos code directory, with
`PYTHONPATH` including both the task root and the code root.
