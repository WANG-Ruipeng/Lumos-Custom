# Schedule Contract

UniLumos official uniform schedule:

```python
sigma = np.linspace(1, 0, sample_steps + 1)[:sample_steps]
sigma = sample_shift * sigma / (1 + (sample_shift - 1) * sigma)
```

BSS actual NFE `T`:

- Build the official base schedule with `T - 2` steps.
- Insert one linear midpoint between `base[0]` and `base[1]`.
- Insert one linear midpoint between `base[-1]` and terminal coordinate `0.0`.
- Run exactly `T` model evaluations.

Default split pairs are `0,-1`.

Uniform `T` and BSS `T` are intentionally different schedules at the same NFE.
The scheduler must dump schedule JSON for every run used in a table.
