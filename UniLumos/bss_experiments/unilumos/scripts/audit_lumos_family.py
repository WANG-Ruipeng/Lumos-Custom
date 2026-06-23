#!/usr/bin/env python
"""Write a planning audit for LumosBench and related baselines."""

from __future__ import annotations

from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    out = TASK_ROOT / "bss_experiments" / "unilumos" / "docs" / "lumos_family_notes.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        """# Lumos Family Notes

This is a planning audit only. Do not run these baselines in the first BSS smoke.

| Candidate | Type | Is DiT/flow? | Relighting? | Official examples? | Step count controllable? | BSS feasibility | Use |
|---|---|---|---|---|---|---|---|
| UniLumos | Image/video relighting model | Yes, flow-matching backbone | Yes | Yes | Yes, `sample_steps` and `sample_shift` | Main target | Model B smoke |
| LumosBench | Attribute benchmark | No, evaluation suite | Evaluates relighting outputs | JSONLs in repo tree | Not applicable | Not a sampler target | Appendix controllability evaluation |
| Wan2.1 | Video generation backbone | Likely yes | Generic backbone | External | Likely schedule-controlled | Possible but out of scope | Later generic video DiT |
| CogVideoX | Video generation model | Likely yes | Generic | External | Likely schedule-controlled | Possible but separate | Later generic video DiT |
| HunyuanVideo | Video generation model | Likely yes | Generic | External | Likely schedule-controlled | Possible but separate | Later generic video DiT |
| LTX-Video | Video generation model | Likely yes | Generic | External | Unknown in this repo | Possible but separate | Appendix candidate |
| IC-Light | Image relighting baseline | Not strict evidence here | Yes | External | Pipeline-specific | Not main BSS evidence | Task baseline |
| Light-A-Video | Video lighting baseline | Unknown here | Yes | External | Pipeline-specific | Not main BSS evidence | Task baseline |

LumosBench evaluates six lighting attributes: direction, light source type,
intensity, color temperature, temporal dynamics, and optical phenomena. It uses
Qwen2.5-VL for model-based qualitative scoring, so it is too heavy for the
first same-NFE BSS smoke.
""",
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
