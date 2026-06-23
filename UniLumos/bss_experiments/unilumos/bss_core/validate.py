"""Schedule validation helpers for UniLumos BSS experiments."""

from __future__ import annotations

from typing import Iterable

from .grids import get_uniform_shifted_sigmas, make_boundary_split_coords, parse_split_pairs


def _float_list(values: Iterable[float] | None) -> list[float]:
    if values is None:
        return []
    return [float(v) for v in values]


def _close(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(float(a) - float(b)) <= tol


def _same_list(a: Iterable[float], b: Iterable[float], tol: float = 1e-9) -> bool:
    a_list = _float_list(a)
    b_list = _float_list(b)
    return len(a_list) == len(b_list) and all(_close(x, y, tol) for x, y in zip(a_list, b_list))


def _monotone_nonincreasing(values: Iterable[float], tol: float = 1e-9) -> bool:
    coords = _float_list(values)
    return all(coords[i] >= coords[i + 1] - tol for i in range(len(coords) - 1))


def validate_schedule_payload(payload: dict, raise_on_error: bool = False) -> dict:
    """Validate one dumped UniLumos schedule JSON payload."""

    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    sampler_mode = payload.get("sampler_mode")
    sample_steps = int(payload.get("sample_steps", 0) or 0)
    sample_shift = float(payload.get("sample_shift", 0.0) or 0.0)
    actual_nfe = int(payload.get("actual_nfe", 0) or 0)
    final_sigmas = _float_list(payload.get("final_sigmas"))
    base_sigmas = _float_list(payload.get("base_sigmas"))
    timesteps = payload.get("timesteps") or []

    add("model_name", payload.get("model_name") == "UniLumos", str(payload.get("model_name")))
    add("final_sigmas_count", len(final_sigmas) == actual_nfe, f"{len(final_sigmas)} vs {actual_nfe}")
    add("timesteps_count", len(timesteps) == actual_nfe, f"{len(timesteps)} vs {actual_nfe}")
    add("model_eval_count", len(final_sigmas) == actual_nfe, f"{len(final_sigmas)} model eval coords")
    add("monotone_nonincreasing", _monotone_nonincreasing(final_sigmas), str(final_sigmas))
    add("terminal_recorded", "terminal_coord" in payload, str(payload.get("terminal_coord")))

    if sampler_mode == "uniform":
        expected = get_uniform_shifted_sigmas(sample_steps, sample_shift)
        add("uniform_nfe", actual_nfe == sample_steps, f"{actual_nfe} vs {sample_steps}")
        add("uniform_sigmas_match", _same_list(final_sigmas, expected), "")
    elif sampler_mode == "bss":
        base_steps = int(payload.get("base_sample_steps", 0) or 0)
        split_pairs = parse_split_pairs(payload.get("split_pairs"))
        terminal = float(payload.get("terminal_coord", 0.0))
        expected, _ = make_boundary_split_coords(base_sigmas, split_pairs, terminal)
        uniform_same_nfe = get_uniform_shifted_sigmas(actual_nfe, sample_shift)
        add("bss_nfe", actual_nfe == sample_steps, f"{actual_nfe} vs {sample_steps}")
        add("bss_base_nfe", len(base_sigmas) == base_steps, f"{len(base_sigmas)} vs {base_steps}")
        add("bss_base_plus_midpoints", _same_list(final_sigmas, expected), "")
        add("bss_not_uniform_same_nfe", not _same_list(final_sigmas, uniform_same_nfe), "")
        add("bss_preserves_first", bool(final_sigmas and base_sigmas and _close(final_sigmas[0], base_sigmas[0])), "")
        add("bss_preserves_last_base", any(_close(v, base_sigmas[-1]) for v in final_sigmas) if base_sigmas else False, "")
    elif sampler_mode == "custom_sigmas":
        add("custom_sigmas_nfe", actual_nfe == len(final_sigmas), f"{actual_nfe} vs {len(final_sigmas)}")
    else:
        add("known_sampler_mode", False, str(sampler_mode))

    ok = all(check["passed"] for check in checks)
    result = {"ok": ok, "checks": checks}
    if raise_on_error and not ok:
        failed = ", ".join(check["name"] for check in checks if not check["passed"])
        raise AssertionError(f"Schedule validation failed: {failed}")
    return result
