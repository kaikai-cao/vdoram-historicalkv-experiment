#!/usr/bin/env python3
"""EXP-DORAM-01-R1 benchmark: E0 vs E1 under IDENTICAL Fetch workload.

This is a targeted correction of the original benchmark, whose E0 only fetched
on LOAD while E1 fetched every step. In R1 both models run exactly one Fetch per
non-initial step (T-1), with the SAME fetch_address sequence (verified per run),
per source ZkProgramExecutor.cs L205-236 on pinned commit 10c90d3546...

Records per (N, T), 10 independent reps each (same as original round):
  * fetch_count          -- Fetch ops per run (must be T-1 for both)
  * query_total_s        -- pure Fetch/query time (E0 scan vs E1 dict read)
  * per_fetch_s          -- query_total_s / fetch_count
  * total_time_s         -- full run (trace -> state -> history + commitments)
  * peak_bytes           -- separate tracemalloc peak-heap run
  * fetch_seq_ok         -- E0.fetch_addresses == E1.fetch_addresses (canonical)
  * returns_ok / final_state_ok -- vs independent oracle

Output files are NEW (r1_* prefix); original-round CSVs are never overwritten.
NO prior assumption that E1 keeps a 4-23x edge -- the numbers decide.
E1 is a plain dict model, NOT an ORAM; no privacy/cost claim is made.
"""

from __future__ import annotations

import csv
import gc
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.trace.generator_r1 import (  # noqa: E402
    N_VALUES, T_VALUES, SEED, generate_all_r1, load_r1_trace, r1_trace_path,
)
from src.baseline.e0_linear_scan import E0LinearScan  # noqa: E402
from src.dual_store.e1_dual_store import E1DualStore  # noqa: E402
from src.oracle import Oracle  # noqa: E402

REPEATS = 10
DATA_DIR = ROOT / "data"
RESULTS = DATA_DIR / "results"


def timed_run(model, trace):
    """Wall-clock timing WITHOUT tracemalloc (which distorts timing 2-3x)."""
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


def describe(values):
    return {"median": statistics.median(values),
            "min": min(values), "max": max(values)}


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    generate_all_r1(str(DATA_DIR), SEED)  # ensure 16 R1 traces exist

    raw_path = RESULTS / "r1_benchmark_raw.csv"
    sum_path = RESULTS / "r1_benchmark_summary.csv"
    oracle_path = RESULTS / "r1_oracle.json"
    fetchseq_path = RESULTS / "r1_fetch_sequence_evidence.json"

    raw_fields = [
        "impl", "N", "T", "rep", "fetch_count", "total_time_s",
        "query_total_s", "per_fetch_s", "workload_ops", "workload_kind",
        "history_rows", "peak_bytes", "fetch_seq_ok",
        "returns_ok", "final_state_ok",
    ]
    sum_fields = [
        "impl", "N", "T", "reps", "fetch_count",
        "total_median_s", "total_min_s", "total_max_s",
        "query_total_median_s", "query_total_min_s", "query_total_max_s",
        "per_fetch_median_s", "per_fetch_min_s", "per_fetch_max_s",
        "workload_ops", "workload_kind", "history_rows",
        "peak_median_bytes", "peak_min_bytes", "peak_max_bytes",
        "fetch_seq_ok", "returns_ok", "final_state_ok",
    ]

    raw_rows = []
    grouped = {}
    oracle_states = {}
    fetchseq_evidence = {}

    for n in N_VALUES:
        for t in T_VALUES:
            trace = load_r1_trace(r1_trace_path(str(DATA_DIR), n, t))
            orc = Oracle()
            expected = orc.run(trace)
            oracle_states[f"N{n}_T{t}"] = {str(k): v for k, v in orc.final_state().items()}

            # Canonical fetch-address sequence from the trace (step>0).
            canonical = [rec["fetch_address"] for rec in trace if rec["step"] != 0]
            fetchseq_evidence[f"N{n}_T{t}"] = {
                "fetch_count": len(canonical),
                "first_8": canonical[:8],
                "last_8": canonical[-8:],
            }

            for impl in ("E0", "E1"):
                key = (impl, n, t)
                grouped[key] = []
                model_cls = E0LinearScan if impl == "E0" else E1DualStore
                peak = memory_run(model_cls, trace)
                for rep in range(REPEATS):
                    model = model_cls()
                    elapsed, summary = timed_run(model, trace)

                    fetch_count = summary["queries"]
                    fetch_seq_ok = (summary["fetch_addresses"] == canonical)
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

                    qt = summary["query_time_s"]
                    rec = {
                        "impl": impl, "N": n, "T": t, "rep": rep,
                        "fetch_count": fetch_count,
                        "total_time_s": elapsed,
                        "query_total_s": qt,
                        "per_fetch_s": qt / fetch_count if fetch_count else 0.0,
                        "workload_ops": workload_ops,
                        "workload_kind": wl_kind,
                        "history_rows": summary["history_rows"],
                        "peak_bytes": peak,
                        "fetch_seq_ok": int(fetch_seq_ok),
                        "returns_ok": int(returns_ok),
                        "final_state_ok": int(state_ok),
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
        for (impl, n, t), recs in grouped.items():
            tot = describe([r["total_time_s"] for r in recs])
            qt = describe([r["query_total_s"] for r in recs])
            pf = describe([r["per_fetch_s"] for r in recs])
            pk = describe([r["peak_bytes"] for r in recs])
            w.writerow({
                "impl": impl, "N": n, "T": t, "reps": len(recs),
                "fetch_count": recs[0]["fetch_count"],
                "total_median_s": tot["median"],
                "total_min_s": tot["min"], "total_max_s": tot["max"],
                "query_total_median_s": qt["median"],
                "query_total_min_s": qt["min"], "query_total_max_s": qt["max"],
                "per_fetch_median_s": pf["median"],
                "per_fetch_min_s": pf["min"], "per_fetch_max_s": pf["max"],
                "workload_ops": recs[0]["workload_ops"],
                "workload_kind": "scanned_rows" if impl == "E0" else "hash_lookups",
                "history_rows": recs[0]["history_rows"],
                "peak_median_bytes": pk["median"],
                "peak_min_bytes": pk["min"], "peak_max_bytes": pk["max"],
                "fetch_seq_ok": all(r["fetch_seq_ok"] for r in recs),
                "returns_ok": all(r["returns_ok"] for r in recs),
                "final_state_ok": all(r["final_state_ok"] for r in recs),
            })

    with open(oracle_path, "w", encoding="utf-8") as f:
        json.dump(oracle_states, f, ensure_ascii=False, indent=2)
    with open(fetchseq_path, "w", encoding="utf-8") as f:
        json.dump(fetchseq_evidence, f, ensure_ascii=False, indent=2)

    all_ok = all(r["fetch_seq_ok"] and r["returns_ok"] and r["final_state_ok"]
                 for r in raw_rows)
    print(f"raw       -> {raw_path} ({len(raw_rows)} rows)")
    print(f"summary   -> {sum_path} ({len(grouped)} groups)")
    print(f"fetch seq -> {fetchseq_path}")
    print(f"all correctness + fetch-sequence flags: {all_ok}")

    # Compact comparison table (median pure-query time, both models).
    print(f"\n{'N':>4} {'T':>5} {'fetch':>6} {'E0_q_ms':>9} {'E1_q_ms':>9} "
          f"{'ratio':>7} {'E0_scan':>8} {'E1_lookup':>9}")
    for n in N_VALUES:
        for t in T_VALUES:
            e0 = [r for r in grouped[("E0", n, t)]] if ("E0", n, t) in grouped else []
            # read from summary rows on disk for medians
    srows = list(csv.DictReader(open(sum_path, encoding="utf-8")))
    for n in N_VALUES:
        for t in T_VALUES:
            a = [r for r in srows if r["impl"] == "E0" and r["N"] == str(n) and r["T"] == str(t)][0]
            b = [r for r in srows if r["impl"] == "E1" and r["N"] == str(n) and r["T"] == str(t)][0]
            q0 = float(a["query_total_median_s"]) * 1000
            q1 = float(b["query_total_median_s"]) * 1000
            ratio = q0 / q1 if q1 else float("nan")
            print(f"{n:>4} {t:>5} {a['fetch_count']:>6} {q0:>9.4f} {q1:>9.4f} "
                  f"{ratio:>6.2f}x {int(a['workload_ops']):>8} {int(b['workload_ops']):>9}")


if __name__ == "__main__":
    main()
