"""Small adapter helpers used by patched UniLumos inference scripts."""

from __future__ import annotations

import os


def add_bss_sampler_args(parser) -> None:
    parser.add_argument("--sample_steps", type=int, default=25, help="actual model evaluations")
    parser.add_argument("--sample_shift", type=float, default=8.0, help="UniLumos shifted sigma parameter")
    parser.add_argument("--seed", type=int, default=0, help="random seed for noise and global RNG")
    parser.add_argument(
        "--sampler_mode",
        type=str,
        default="uniform",
        choices=("uniform", "bss", "custom_sigmas"),
        help="schedule construction mode",
    )
    parser.add_argument("--base_sample_steps", type=int, default=None, help="base NFE for BSS")
    parser.add_argument("--split_pairs", type=str, default="0,-1", help="BSS split indices")
    parser.add_argument("--custom_sigmas", type=str, default=None, help="JSON or NPY custom sigma schedule")
    parser.add_argument("--dump_schedule_json", type=str, default=None, help="path or 'auto' for schedule JSON")
    parser.add_argument("--method", type=str, default=None, help="experiment method label")
    parser.add_argument("--max_cases", type=int, default=None, help="maximum cases to run")
    parser.add_argument("--case_filter", type=str, default=None, help="substring filter over case identifiers")


def case_matches(args, *parts) -> bool:
    if not getattr(args, "case_filter", None):
        return True
    haystack = " ".join(str(part) for part in parts if part is not None)
    return args.case_filter in haystack


def make_schedule_json_path(dump_schedule_json, output_stem: str, case_index: int | None = None) -> str | None:
    if not dump_schedule_json:
        return None
    if str(dump_schedule_json).lower() == "auto":
        return f"{output_stem}_schedule.json"
    root, ext = os.path.splitext(str(dump_schedule_json))
    if ext.lower() == ".json":
        return str(dump_schedule_json)
    suffix = "" if case_index is None else f"_{case_index:04d}"
    return os.path.join(str(dump_schedule_json), f"schedule{suffix}.json")
