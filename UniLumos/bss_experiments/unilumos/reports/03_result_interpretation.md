# Result Interpretation

Pending Colab execution.

Use this wording after metrics are available:

- On this UniLumos official-protocol smoke case, BSS-10 does or does not improve
  over uniform10 at the same NFE.
- Reference is `uniform25`, the official default schedule, not ground truth.
- This is cross-model smoke evidence, not final generality.

Decision rule for the first smoke:

- Primary same-NFE comparison: `bss10` versus `uniform10`.
- Reference closure target: `reference_uniform25`.
- BSS win if `bss10` improves RGB L1 or temporal reference error versus
  `uniform10`; stronger if both improve.
- If the smoke fails due to runtime/weights, do not run the ladder.
