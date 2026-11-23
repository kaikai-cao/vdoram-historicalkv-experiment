# EXP-DORAM-08-R1 symbolic model — reproducibility

Pure symbolic secret-multiplication cost model. Not an MPC benchmark.

## Run

```bash
PYTHONPATH="src;tests" python -m unittest tests.test_exp_doram_08_r1 -v
PYTHONPATH="src" python -m src.exp_doram_08_r1.sensitivity
```

Regenerates `results/exp_doram_08_r1/{symbolic_costs,sensitivity_raw,sensitivity_summary}.csv`
deterministically (no RNG).

## Modules

- `costs.py` — E0 / E1-A / E1-B step & total costs; closed forms; step-0 forced
  separate; explicit STORE step set; linear ops; rounds/preproc/online derivations.
- `counters.py` — symbolic eq-vector / SelectCompose / LowBit semantics checks
  (E1-B domain correctness P1/P2/P3).
- `sensitivity.py` — deterministic parameter sweep → three CSVs.

All defaults source-derived from pinned upstream `10c90d35`; see
`docs/exp-doram-08-r1/source-corrections.md`. Stress weights are ASSUMED and
labelled `parameter_status` in every CSV row.
