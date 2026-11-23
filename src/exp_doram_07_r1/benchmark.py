#!/usr/bin/env python3
"""EXP-DORAM-07-R1 benchmark: three reference models, matched workload.

Matrix: n in {16,64,256,1024} x T in {64,256,1024,4096} x 5 workloads x 5 reps.
Every (n,T,workload,seed) trace is generated ONCE and fed byte-identically to
E0-EarlyExit, E0-FullScan and E1-ShadowState. Cross-model correctness checks
(returns, export, invariant) are HARD errors.

COST CAVEAT: Python wall time and abstract counters are reference-model
measurements, NOT MPC gates/rounds (see cost-model.md / benchmark-analysis.md).
"""

from __future__ import annotations

import csv
import gc
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.exp_doram_07_r1.e0_early_exit import E0EarlyExitAdapter  # noqa: E402
from src.exp_doram_07_r1.e0_full_scan import E0FullScan  # noqa: E402
from src.exp_doram_07_r1.e1_shadow_state import E1ShadowState  # noqa: E402
from src.exp_doram_07_r1.workloads import (  # noqa: E402
    WORKLOADS,
    generate_workload,
    op_counts,
)

N_VALUES = (16, 64, 256, 1024)
T_VALUES = (64, 256, 1024, 4096)
REPEATS = 5
SEED = 20261123
RESULTS = os.path.join(ROOT, "results", "exp_doram_07_r1")

IMPLS = ("E0-EarlyExit", "E0-FullScan", "E1-ShadowState")

# one row per (impl, cell, rep) -- full metrics for each model
RAW_FIELDS = [
    "impl", "n", "T", "workload", "rep", "seed",
    "fetch_count", "query_count", "update_count", "noop_count",
    # timing (seconds)
    "fetch_s", "query_s", "update_s", "append_s", "export_s",
    "execute_s", "end_to_end_s",
    # scan / operation counters
    "history_rows_scanned", "history_equality_checks",
    "shadow_slots_scanned", "shadow_equality_checks",
    "selection_operations", "update_operations", "history_append_operations",
    # correctness flags
    "export_ok", "returns_ok", "invariant_ok",
]

SUMMARY_FIELDS = [
    "impl", "n", "T", "workload", "reps",
    "fetch_count", "query_count", "update_count", "noop_count",
    "fetch_median_s", "update_median_s", "append_median_s", "export_median_s",
    "execute_median_s", "execute_q1_s", "execute_q3_s",
    "end_to_end_median_s", "end_to_end_q1_s", "end_to_end_q3_s",
    "history_rows_scanned", "history_equality_checks",
    "shadow_slots_scanned", "shadow_equality_checks",
    "selection_operations", "update_operations", "history_append_operations",
    # E1 relative to E0-FullScan (only populated for impl=E1)
    "execute_ratio_vs_fullscan", "end_to_end_ratio_vs_fullscan",
    "total_scan_ratio_vs_fullscan",
    "export_ok", "returns_ok", "invariant_ok",
]


def _quantiles(values: list[float]) -> tuple[float, float, float]:
    s = sorted(values)
    k = len(s) - 1

    def at(q: float) -> float:
        pos = q * k
        lo = int(pos)
        hi = min(lo + 1, k)
        frac = pos - lo
        return s[lo] * (1 - frac) + s[hi] * frac

    return at(0.5), at(0.25), at(0.75)


def _make_model(impl: str, n: int):
    if impl == "E0-EarlyExit":
        return E0EarlyExitAdapter(n=n)
    if impl == "E0-FullScan":
        return E0FullScan(n=n)
    if impl == "E1-ShadowState":
        return E1ShadowState(n=n)
    raise ValueError(impl)


def run_one(impl: str, n: int, trace: list[dict], counts: dict, rep: int) -> dict:
    model = _make_model(impl, n)
    gc.collect()
    t0 = time.perf_counter()
    sm = model.run(trace)
    wall_execute = time.perf_counter() - t0  # independent outer measurement

    t1 = time.perf_counter()
    exported = model.export_fields()
    export_wall = time.perf_counter() - t1

    # Use the model's own execute_time_s (consistent inner boundary) but keep
    # the outer wall measurement for transparency in analysis.
    execute = float(sm["execute_time_s"])
    export_t = float(sm["export_time_s"]) + export_wall  # both calls counted
    end_to_end = execute + export_t

    return {
        "impl": impl, "n": n, "T": len(trace), "workload": trace[0]["workload"],
        "rep": rep, "seed": SEED,
        "fetch_count": sm["fetch_count"],
        "query_count": sm["query_count"],
        "update_count": sm["update_count"],
        "noop_count": counts["NOOP"],
        "fetch_s": sm["fetch_time_s"],
        "query_s": sm["query_time_s"],
        "update_s": sm["update_time_s"],
        "append_s": sm["append_time_s"],
        "export_s": export_t,
        "execute_s": execute,
        "execute_wall_outer_s": wall_execute,  # extra diagnostic, ignored in summary
        "end_to_end_s": end_to_end,
        "history_rows_scanned": sm["history_rows_scanned"],
        "history_equality_checks": sm["history_equality_checks"],
        "shadow_slots_scanned": sm["shadow_slots_scanned"],
        "shadow_equality_checks": sm["shadow_equality_checks"],
        "selection_operations": sm["selection_operations"],
        "update_operations": sm["update_operations"],
        "history_append_operations": sm["history_append_operations"],
        "_exported": exported,
        "_returns": list(model.actual_returns),
        "_invariant": model.invariant()[0],
    }


def main() -> None:
    os.makedirs(RESULTS, exist_ok=True)
    raw_rows: list[dict] = []
    grouped: dict[tuple, list[dict]] = {}

    cells = [
        (n, t, wl)
        for n in N_VALUES for t in T_VALUES for wl in WORKLOADS
    ]
    total_cells = len(cells)
    for idx, (n, t, workload) in enumerate(cells, 1):
        trace = generate_workload(n, t, workload, SEED)
        counts = op_counts(trace)
        # Run all three models, reps interleaved; verify consistency on last rep.
        by_impl: dict[str, list[dict]] = {impl: [] for impl in IMPLS}
        for rep in range(REPEATS):
            for impl in IMPLS:
                row = run_one(impl, n, trace, counts, rep)
                by_impl[impl].append(row)
                raw_rows.append(row)
                grouped.setdefault((impl, n, t, workload), []).append(row)

        # cross-model hard checks (use last rep)
        ee = by_impl["E0-EarlyExit"][-1]
        fs = by_impl["E0-FullScan"][-1]
        e1 = by_impl["E1-ShadowState"][-1]
        export_ok = (
            ee["_exported"] == fs["_exported"] == e1["_exported"]
        )
        returns_ok = (
            ee["_returns"] == fs["_returns"] == e1["_returns"]
        )
        invariant_ok = bool(e1["_invariant"])
        if not (export_ok and returns_ok and invariant_ok):
            raise RuntimeError(
                f"consistency failure n={n} T={t} wl={workload}: "
                f"export={export_ok} returns={returns_ok} invariant={invariant_ok}"
            )
        for impl in IMPLS:
            for row in by_impl[impl]:
                row["export_ok"] = int(export_ok)
                row["returns_ok"] = int(returns_ok)
                row["invariant_ok"] = int(invariant_ok)

        if idx % 20 == 0 or idx == total_cells:
            print(
                f"[{idx:3d}/{total_cells}] n={n:4d} T={t:4d} "
                f"{workload:14s} export/returns/invariant OK"
            )

    raw_path = os.path.join(RESULTS, "benchmark_raw.csv")
    with open(raw_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RAW_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(raw_rows)

    # summary: medians/Q1/Q3 + E1-relative ratios
    sum_path = os.path.join(RESULTS, "benchmark_summary.csv")
    ratio_lookup: dict[tuple, dict] = {}
    for (impl, n, t, wl), rows in grouped.items():
        if impl != "E0-FullScan":
            continue
        fs_exec = _quantiles([r["execute_s"] for r in rows])[0]
        fs_e2e = _quantiles([r["end_to_end_s"] for r in rows])[0]
        fs_scan = (
            _quantiles([r["history_rows_scanned"] + r["history_equality_checks"] for r in rows])[0]
        )
        ratio_lookup[(n, t, wl)] = {
            "execute": fs_exec, "e2e": fs_e2e, "scan": fs_scan,
        }

    with open(sum_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        w.writeheader()
        for (impl, n, t, workload), rows in grouped.items():
            def med(field):
                return _quantiles([r[field] for r in rows])[0]

            ex_m, ex_q1, ex_q3 = _quantiles([r["execute_s"] for r in rows])
            e2e_m, e2e_q1, e2e_q3 = _quantiles([r["end_to_end_s"] for r in rows])
            ref = ratio_lookup[(n, t, workload)]
            if impl == "E1-ShadowState":
                ex_ratio = ex_m / ref["execute"] if ref["execute"] > 0 else 0.0
                e2e_ratio = e2e_m / ref["e2e"] if ref["e2e"] > 0 else 0.0
                scan_e1 = med("shadow_slots_scanned") + med("shadow_equality_checks")
                scan_ratio = scan_e1 / ref["scan"] if ref["scan"] > 0 else 0.0
            else:
                ex_ratio = e2e_ratio = scan_ratio = ""
            w.writerow({
                "impl": impl, "n": n, "T": t, "workload": workload, "reps": len(rows),
                "fetch_count": rows[0]["fetch_count"],
                "query_count": rows[0]["query_count"],
                "update_count": rows[0]["update_count"],
                "noop_count": rows[0]["noop_count"],
                "fetch_median_s": med("fetch_s"),
                "update_median_s": med("update_s"),
                "append_median_s": med("append_s"),
                "export_median_s": med("export_s"),
                "execute_median_s": ex_m, "execute_q1_s": ex_q1, "execute_q3_s": ex_q3,
                "end_to_end_median_s": e2e_m, "end_to_end_q1_s": e2e_q1, "end_to_end_q3_s": e2e_q3,
                "history_rows_scanned": rows[0]["history_rows_scanned"],
                "history_equality_checks": rows[0]["history_equality_checks"],
                "shadow_slots_scanned": rows[0]["shadow_slots_scanned"],
                "shadow_equality_checks": rows[0]["shadow_equality_checks"],
                "selection_operations": rows[0]["selection_operations"],
                "update_operations": rows[0]["update_operations"],
                "history_append_operations": rows[0]["history_append_operations"],
                "execute_ratio_vs_fullscan": ex_ratio,
                "end_to_end_ratio_vs_fullscan": e2e_ratio,
                "total_scan_ratio_vs_fullscan": scan_ratio,
                "export_ok": rows[0]["export_ok"],
                "returns_ok": rows[0]["returns_ok"],
                "invariant_ok": rows[0]["invariant_ok"],
            })

    print(f"\nraw     -> {raw_path} ({len(raw_rows)} rows)")
    print(f"summary -> {sum_path} ({len(grouped)} groups)")
    print("all export/returns/invariant checks: OK")


if __name__ == "__main__":
    main()
