#!/usr/bin/env python
"""Create a simple first-frame side-by-side contact sheet."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def existing_output(stem: str) -> Path | None:
    base = Path(stem)
    for suffix in ("", ".mp4", ".png", ".jpg", ".jpeg"):
        candidate = Path(str(base) + suffix)
        if candidate.exists():
            return candidate
    return None


def first_frame(path: Path):
    import imageio.v3 as iio
    from PIL import Image

    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return Image.fromarray(iio.imread(path)).convert("RGB")
    for frame in iio.imiter(path):
        return Image.fromarray(frame).convert("RGB")
    raise RuntimeError(f"No frame found in {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output_dir", type=Path, default=None)
    args = parser.parse_args()

    with args.manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    order = ["uniform8", "uniform10", "bss10", "reference_uniform25"]
    frames = []
    labels = []
    for method in order:
        row = next((item for item in rows if item["method"] == method), None)
        if row is None:
            continue
        path = existing_output(row["output_path"])
        if path is None:
            continue
        frames.append(first_frame(path))
        labels.append(method)
    if not frames:
        raise RuntimeError("No output media found")

    from PIL import Image, ImageDraw

    height = min(frame.height for frame in frames)
    resized = [frame.resize((int(frame.width * height / frame.height), height)) for frame in frames]
    label_h = 32
    width = sum(frame.width for frame in resized)
    sheet = Image.new("RGB", (width, height + label_h), "white")
    draw = ImageDraw.Draw(sheet)
    x = 0
    for label, frame in zip(labels, resized):
        sheet.paste(frame, (x, label_h))
        draw.text((x + 8, 8), label, fill=(0, 0, 0))
        x += frame.width
    out_dir = args.output_dir or args.manifest.parent.parent / "figures" / "side_by_side"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "one_case_side_by_side.jpg"
    sheet.save(out, quality=95)
    print(out)


if __name__ == "__main__":
    main()
