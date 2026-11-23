#!/usr/bin/env python3
"""EXP-DORAM-01 benchmark: E0 (linear scan) vs E1 (dual store).

For every (N, T) in {64,128,256,512} x {128,256,512,1024}, each implementation
is run REPEATS independent times on the SAME fixed-seed trace. We record:
  - total execution time, per-query time, per-step time
  - workload (E0 scanned rows vs E1 hash lookups -- DIFFERENT operations)
  - history row count, peak RSS (memory), final-state consistency vs oracle

Times use perf_counter; memory uses tracemalloc (peak traced Python heap) since
it is deterministic and portable. Each raw repetition is written to CSV so
medians/min/max can be recomputed. A single summary CSV holds aggregates.

NOTE (task §六): E0 scanned-rows and E1 hash-lookups are NOT the same cost unit
and must not be compared as identical. Conclusions use wall-clock time + memory.
No E2 numbers are produced here (no Path ORAM, no MPC, no Halo2).
"""

from __future__ import annotations

import csv
import gc
import os
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.trace.generator import (  # noqa: E402
    N_VALUES, T_VALUES, SEED, generate_all, load_trace, trace_path,
)
from src.baseline.e0_linear_scan import E0LinearScan  # noqa: E402
from src.dual_store.e1_dual_store import E1DualStore  # noqa: E402
from src.oracle import Oracle  # noqa: E402

REPEATS = 10
DATA_DIR = ROOT / "data"


def timed_run(model, trace):
    """Wall-clock measurement WITHOUT tracemalloc (which distorts timing 2-3x)."""
    gc.collect()
    t0 = time.perf_counter()
    summary = model.run(trace)
    elapsed = time.perf_counter() - t0
    return elapsed, summary


def memory_run(model_cls, trace):
    """Separate single-run peak-heap measurement (tracemalloc on)."""
    gc.collect()
    tracemalloc.start()
    model = model_cls()
    model.run(trace)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def describe(values: list[float]) -> dict:
    return {
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    results_dir = DATA_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Ensure all 16 fixed-seed traces exist on disk.
    generate_all(str(DATA_DIR), SEED)

    raw_path = results_dir / "benchmark_raw.csv"
    sum_path = results_dir / "benchmark_summary.csv"
    oracle_path = results_dir / "oracle.json"

    raw_fields = [
        "impl", "N", "T", "rep", "total_time_s", "query_total_s", "per_query_s",
        "per_step_s", "workload_ops", "workload_kind", "history_rows", "peak_bytes",
        "final_state_ok", "returns_ok",
    ]
    sum_fields = [
        "impl", "N", "T", "reps",
        "total_median_s", "total_min_s", "total_max_s",
        "query_total_median_s", "per_query_median_s", "per_query_min_s", "per_query_max_s",
        "workload_ops", "workload_kind", "history_rows",
        "peak_median_bytes", "peak_min_bytes", "peak_max_bytes",
        "final_state_ok", "returns_ok",
    ]

    raw_rows = []
    grouped: dict[tuple, list[dict]] = {}
    oracle_states: dict[str, dict] = {}

    for n in N_VALUES:
        for t in T_VALUES:
            trace = load_trace(trace_path(str(DATA_DIR), n, t))
            orc = Oracle()
            expected = orc.run(trace)
            oracle_states[f"N{n}_T{t}"] = {str(k): v for k, v in orc.final_state().items()}

            for impl, kind in (("E0", "E0"), ("E1", "E1")):
                key = (impl, n, t, kind)
                grouped[key] = []
                model_cls = E0LinearScan if impl == "E0" else E1DualStore
                # Time: REPEATS clean runs. Memory: one separate traced run.
                peak = memory_run(model_cls, trace)
                for rep in range(REPEATS):
                    model = model_cls()
                    elapsed, summary = timed_run(model, trace)

                    queries = summary["queries"]
                    steps = len(trace)
                    if impl == "E0":
                        workload_ops = summary["scanned_rows"]
                        wl_kind = "scanned_rows"
                    else:
                        workload_ops = summary["hash_lookups"]
                        wl_kind = "hash_lookups"

                    returns_ok = (list(model.actual_returns) == expected)
                    state_ok = (model.final_state() == orc.final_state())
                    if impl == "E1":
                        state_ok = state_ok and summary["integrity_ok"]

                    query_total = summary["query_time_s"]
                    rec = {
                        "impl": impl, "N": n, "T": t, "rep": rep,
                        "total_time_s": elapsed,
                        "query_total_s": query_total,
                        "per_query_s": query_total / queries if queries else 0.0,
                        "per_step_s": elapsed / steps if steps else 0.0,
                        "workload_ops": workload_ops,
                        "workload_kind": wl_kind,
                        "history_rows": summary["history_rows"],
                        "peak_bytes": peak,
                        "final_state_ok": int(state_ok),
                        "returns_ok": int(returns_ok),
                    }
                    raw_rows.append(rec)
                    grouped[key].append(rec)

    with open(raw_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=raw_fields)
        w.writeheader()
        w.writerows(raw_rows)

    with open(sum_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sum_fields)
        w.writeheader()
        for (impl, n, t, kind), recs in grouped.items():
            tot = describe([r["total_time_s"] for r in recs])
            qt = describe([r["query_total_s"] for r in recs])
            pq = describe([r["per_query_s"] for r in recs])
            pk = describe([r["peak_bytes"] for r in recs])
            w.writerow({
                "impl": impl, "N": n, "T": t, "reps": len(recs),
                "total_median_s": tot["median"],
                "total_min_s": tot["min"],
                "total_max_s": tot["max"],
                "query_total_median_s": qt["median"],
                "per_query_median_s": pq["median"],
                "per_query_min_s": pq["min"],
                "per_query_max_s": pq["max"],
                "workload_ops": recs[0]["workload_ops"],
                "workload_kind": kind,
                "history_rows": recs[0]["history_rows"],
                "peak_median_bytes": pk["median"],
                "peak_min_bytes": pk["min"],
                "peak_max_bytes": pk["max"],
                "final_state_ok": all(r["final_state_ok"] for r in recs),
                "returns_ok": all(r["returns_ok"] for r in recs),
            })

    import json
    with open(oracle_path, "w", encoding="utf-8") as f:
        json.dump(oracle_states, f, ensure_ascii=False, indent=2)

    print(f"raw  -> {raw_path} ({len(raw_rows)} rows)")
    print(f"sum  -> {sum_path} ({len(grouped)} groups)")
    print(f"oracle -> {oracle_path}")
    print("all correctness flags:",
          all(r["final_state_ok"] and r["returns_ok"] for r in raw_rows))


if __name__ == "__main__":
    main()
