# Lumos Family Notes

This is a planning note only. Do not run LumosBench or other baselines during
the first UniLumos BSS smoke.

| Candidate | Type | Is DiT/flow? | Relighting? | Official examples? | Step count controllable? | BSS feasibility | Use |
|---|---|---|---|---|---|---|---|
| UniLumos | Image/video relighting model | Yes, flow matching | Yes | Yes | Yes | Main target | Model B smoke |
| LumosBench | Benchmark/evaluator | No | Evaluates relighting | JSONLs in tree | Not applicable | Not a sampler target | Appendix controllability |
| Wan2.1 | Video model/backbone | Likely yes | Generic | External | Likely | Possible later | Generic video DiT |
| LTX-Video | Video model | Likely yes | Generic | External | Unknown here | Possible later | Appendix candidate |
| CogVideoX | Video model | Likely yes | Generic | External | Likely | Possible later | Generic video DiT |
| HunyuanVideo | Video model | Likely yes | Generic | External | Likely | Possible later | Generic video DiT |
| IC-Light | Image relighting baseline | Not strict here | Yes | External | Pipeline-specific | Not main evidence | Task baseline |
| Light-A-Video | Video relighting baseline | Unknown here | Yes | External | Pipeline-specific | Not main evidence | Task baseline |

LumosBench evaluates six attributes: direction, light source type, intensity,
color temperature, temporal dynamics, and optical phenomena. It requires
Qwen2.5-VL for qualitative scoring, so it is too heavy for the first same-NFE
smoke.
