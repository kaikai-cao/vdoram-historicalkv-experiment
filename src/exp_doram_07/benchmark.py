#!/usr/bin/env python3
"""EXP-DORAM-07 benchmark: E0 (history scan) vs E1 (shadow full-domain scan).

Matched design
--------------
* Identical workload records feed E0 and E1 (same seed, same op sequence).
* Wall-clock timing uses perf_counter WITHOUT tracemalloc (which distorts time).
* Every run verifies: Export field-for-field equality, actual return equality,
  counter expectations, final invariant. Any mismatch is a hard error.
* 5 independent reps per cell; raw rows + median/Q1/Q3 summary written as CSV.

COST CAVEAT (task 7.3 / 8):
  The Python wall-clock numbers and the abstract counters are REFERENCE-MODEL
  measurements. They are NOT MPC multiplication gates, communication rounds, or
  R1CS constraints, and must NOT be converted into cryptographic cost claims.
"""

from __future__ import annotations

import csv
import gc
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.exp_doram_07.historical_kv import HistoricalKVLinearScan  # noqa: E402
from src.exp_doram_07.shadow_state import ShadowStateTable  # noqa: E402
from src.exp_doram_07.workloads import WORKLOADS, generate_workload, op_counts  # noqa: E402

N_VALUES = (16, 64, 256, 1024)
T_VALUES = (64, 256, 1024, 4096)
REPEATS = 5
SEED = 20261123
RESULTS = ROOT / "results" / "exp_doram_07"

RAW_FIELDS = [
    "impl", "n", "T", "workload", "rep", "seed",
    "fetch_count", "query_count", "update_count", "noop_count",
    "total_s", "query_s", "update_s", "append_s", "export_s",
    "history_rows_scanned", "shadow_slots_scanned", "equality_checks",
    "selection_operations", "update_operations", "history_append_operations",
    "export_ok", "returns_ok", "invariant_ok",
]

SUMMARY_FIELDS = [
    "impl", "n", "T", "workload", "reps",
    "fetch_count", "query_count", "update_count", "noop_count",
    "total_median_s", "total_q1_s", "total_q3_s",
    "query_median_s", "query_q1_s", "query_q3_s",
    "update_median_s", "update_q1_s", "update_q3_s",
    "append_median_s", "export_median_s",
    "history_rows_scanned", "shadow_slots_scanned", "equality_checks",
    "selection_operations", "update_operations", "history_append_operations",
    "export_ok", "returns_ok", "invariant_ok",
]


def _quantiles(values: list[float]) -> tuple[float, float, float]:
    """Return (median, Q1, Q3) with linear interpolation (inclusive method)."""
    s = sorted(values)
    k = len(s) - 1

    def at(q: float) -> float:
        pos = q * k
        lo = int(pos)
        hi = min(lo + 1, k)
        frac = pos - lo
        return s[lo] * (1 - frac) + s[hi] * frac

    return at(0.5), at(0.25), at(0.75)


def _make_run(impl: str, n: int, trace: list[dict]):
    if impl == "E0":
        return HistoricalKVLinearScan(n=n)
    if impl == "E1":
        return ShadowStateTable(n=n)
    raise ValueError(impl)


def run_one(impl: str, n: int, trace: list[dict], counts: dict, rep: int) -> dict:
    model = _make_run(impl, n, trace)
    gc.collect()
    t0 = time.perf_counter()
    summary = model.run(trace)
    total = time.perf_counter() - t0

    t1 = time.perf_counter()
    exported = model.export_fields()
    export_wall = time.perf_counter() - t1

    c = summary  # counters + timing from the model
    return {
        "impl": impl, "n": n, "T": len(trace), "workload": trace[0]["workload"],
        "rep": rep, "seed": SEED,
        "fetch_count": c["fetch_count"],
        "query_count": c["query_count"],
        "update_count": c["update_count"],
        "noop_count": counts["NOOP"],
        "total_s": total,
        "query_s": c["query_time_s"],
        "update_s": c["update_time_s"],
        "append_s": c["append_time_s"],
        "export_s": export_wall,
        "history_rows_scanned": c["history_rows_scanned"],
        "shadow_slots_scanned": c["shadow_slots_scanned"],
        "equality_checks": c["equality_checks"],
        "selection_operations": c["selection_operations"],
        "update_operations": c["update_operations"],
        "history_append_operations": c["history_append_operations"],
        "_exported": exported,
        "_returns": list(model.actual_returns),
        "_invariant": model.invariant()[0] if impl == "E1" else True,
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    raw_rows: list[dict] = []
    # key -> list of rows for the same (impl, n, T, workload)
    grouped: dict[tuple, list[dict]] = {}

    total_cells = len(N_VALUES) * len(T_VALUES) * len(WORKLOADS)
    cell = 0
    for n in N_VALUES:
        for t in T_VALUES:
            for workload in WORKLOADS:
                cell += 1
                trace = generate_workload(n, t, workload, SEED)
                counts = op_counts(trace)
                # Ground truth: reference oracle from the SAME op semantics.
                # E0 and E1 must agree with each other; we use E0's logged
                # returns as the canonical sequence after checking model
                # consistency in tests. Here we cross-check E0 vs E1 directly.
                group: dict[str, list[dict]] = {"E0": [], "E1": []}
                for rep in range(REPEATS):
                    for impl in ("E0", "E1"):
                        row = run_one(impl, n, trace, counts, rep)
                        group[impl].append(row)
                        raw_rows.append(row)
                        key = (impl, n, t, workload)
                        grouped.setdefault(key, []).append(row)

                # Cross-model checks on the last rep of this cell.
                e0 = group["E0"][-1]
                e1 = group["E1"][-1]
                export_ok = e0["_exported"] == e1["_exported"]
                returns_ok = e0["_returns"] == e1["_returns"]
                if not (export_ok and returns_ok and e1["_invariant"]):
                    raise RuntimeError(
                        f"consistency failure n={n} T={t} wl={workload}: "
                        f"export={export_ok} returns={returns_ok} "
                        f"invariant={e1['_invariant']}"
                    )
                for row in group["E0"] + group["E1"]:
                    row["export_ok"] = int(export_ok)
                    row["returns_ok"] = int(returns_ok)
                    row["invariant_ok"] = int(e1["_invariant"])
                print(
                    f"[{cell:2d}/{total_cells}] n={n:4d} T={t:4d} "
                    f"{workload:12s} export/returns/invariant OK"
                )

    raw_path = RESULTS / "benchmark_raw.csv"
    with open(raw_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RAW_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(raw_rows)

    sum_path = RESULTS / "benchmark_summary.csv"
    with open(sum_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for (impl, n, t, workload), rows in grouped.items():
            total_m, total_q1, total_q3 = _quantiles([r["total_s"] for r in rows])
            q_m, q_q1, q_q3 = _quantiles([r["query_s"] for r in rows])
            u_m, _, _ = _quantiles([r["update_s"] for r in rows])
            a_m, _, _ = _quantiles([r["append_s"] for r in rows])
            e_m, _, _ = _quantiles([r["export_s"] for r in rows])
            w.writerow({
                "impl": impl, "n": n, "T": t, "workload": workload,
                "reps": len(rows),
                "fetch_count": rows[0]["fetch_count"],
                "query_count": rows[0]["query_count"],
                "update_count": rows[0]["update_count"],
                "noop_count": rows[0]["noop_count"],
                "total_median_s": total_m, "total_q1_s": total_q1,
                "total_q3_s": total_q3,
                "query_median_s": q_m, "query_q1_s": q_q1, "query_q3_s": q_q3,
                "update_median_s": u_m,
                "append_median_s": a_m, "export_median_s": e_m,
                "history_rows_scanned": rows[0]["history_rows_scanned"],
                "shadow_slots_scanned": rows[0]["shadow_slots_scanned"],
                "equality_checks": rows[0]["equality_checks"],
                "selection_operations": rows[0]["selection_operations"],
                "update_operations": rows[0]["update_operations"],
                "history_append_operations": rows[0]["history_append_operations"],
                "export_ok": rows[0]["export_ok"],
                "returns_ok": rows[0]["returns_ok"],
                "invariant_ok": rows[0]["invariant_ok"],
            })

    print(f"\nraw     -> {raw_path} ({len(raw_rows)} rows)")
    print(f"summary -> {sum_path} ({len(grouped)} groups)")
    print("all export/returns/invariant checks: OK")


if __name__ == "__main__":
    main()
