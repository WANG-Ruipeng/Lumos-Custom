"""Schedule grid construction for Boundary-Split Sampling."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence


def _as_float_list(values: Iterable[float], name: str) -> list[float]:
    try:
        result = [float(v) for v in values]
    except TypeError as exc:
        raise TypeError(f"{name} must be an iterable of numbers") from exc
    if not result:
        raise ValueError(f"{name} must not be empty")
    return result


def parse_split_pairs(value: str | Sequence[int] | None) -> tuple[int, ...]:
    """Parse split-pair CLI values such as ``"0,-1"``."""

    if value is None:
        return (0, -1)
    if isinstance(value, str):
        pieces = [piece.strip() for piece in value.split(",") if piece.strip()]
        if not pieces:
            return (0, -1)
        return tuple(int(piece) for piece in pieces)
    return tuple(int(piece) for piece in value)


def get_uniform_shifted_sigmas(sample_steps: int, sample_shift: float) -> list[float]:
    """
    Match UniLumos official get_sampling_sigmas:

    sigma = np.linspace(1, 0, sample_steps + 1)[:sample_steps]
    sigma = shift * sigma / (1 + (shift - 1) * sigma)
    """

    if sample_steps <= 0:
        raise ValueError("sample_steps must be positive")
    shift = float(sample_shift)
    sigmas = []
    for i in range(sample_steps):
        sigma = 1.0 - (float(i) / float(sample_steps))
        shifted = shift * sigma / (1.0 + (shift - 1.0) * sigma)
        sigmas.append(float(shifted))
    return sigmas


def make_boundary_split_coords(
    base_coords: Iterable[float],
    split_indices: str | Sequence[int] = (0, -1),
    terminal_coord: float = 0.0,
    midpoint_mode: str = "linear",
) -> tuple[list[float], dict]:
    """
    Construct BSS coordinates from official base solver coordinates.

    For base NFE K and the default split indices, the output is:
    base[0], midpoint(base[0], base[1]), base[1], ..., base[-1],
    midpoint(base[-1], terminal).
    """

    if midpoint_mode != "linear":
        raise ValueError(f"Unsupported midpoint_mode: {midpoint_mode}")

    base = _as_float_list(base_coords, "base_coords")
    split_indices = parse_split_pairs(split_indices)
    terminal = float(terminal_coord)

    insert_after: dict[int, list[dict]] = defaultdict(list)
    inserted_midpoints: list[dict] = []

    for raw_index in split_indices:
        if raw_index == -1:
            left_index = len(base) - 1
            left = base[left_index]
            right = terminal
            right_index = "terminal"
        else:
            left_index = int(raw_index)
            if left_index < 0 or left_index >= len(base) - 1:
                raise ValueError(
                    f"split index {raw_index} must refer to an internal interval "
                    "or use -1 for the terminal interval"
                )
            left = base[left_index]
            right = base[left_index + 1]
            right_index = left_index + 1

        midpoint = (left + right) / 2.0
        record = {
            "split_index": raw_index,
            "left_index": left_index,
            "right_index": right_index,
            "left": left,
            "right": right,
            "midpoint": midpoint,
        }
        insert_after[left_index].append(record)
        inserted_midpoints.append(record)

    final_coords: list[float] = []
    for index, coord in enumerate(base):
        final_coords.append(coord)
        for record in insert_after.get(index, []):
            final_coords.append(record["midpoint"])

    metadata = {
        "base_nfe": len(base),
        "actual_nfe": len(final_coords),
        "split_indices": list(split_indices),
        "terminal_coord": terminal,
        "midpoint_mode": midpoint_mode,
        "inserted_midpoints": inserted_midpoints,
        "preserves_base_first": final_coords[0] == base[0],
        "preserves_base_last": base[-1] in final_coords,
    }
    return final_coords, metadata
