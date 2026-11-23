#!/usr/bin/env python3
"""Deterministic symbolic-cost CSV generator for EXP-DORAM-08.

These are PARAMETRIC COST STRUCTURE numbers, not MPC benchmarks.
Every row carries parameter_status; no Python wall-clock time is used.
"""

from __future__ import annotations

import csv
import os
import statistics
from collections import defaultdict

from .costs import CostParams, cross_threshold_n, e0_total, e1_total

NS = (16, 64, 256, 1024)
TS = (64, 256, 1024, 4096)
STORE_RATIOS = (0.0, 0.1, 0.5, 0.9, 1.0)
EQ_RATIOS = (1, 100, 389, 1000)
UPD_RATIOS = (1, 100)
SHARE_EQ_MODES = (True, False)

BASE = CostParams()
DERIVED = "DERIVED_FROM_VERIFIED_SOURCE"
ASSUMED = "ASSUMED_PARAMETER_NOT_MEASURED"
STATUS = "SYMBOLIC_STRUCTURE_NOT_MPC_BENCHMARK"


def store_steps(T: int, ratio: float) -> set[int]:
    """Deterministic STORE placement: approximately ratio*(T-1) stores at s>=1."""
    total = int(round(ratio * (T - 1)))
    if total <= 0 or T <= 1:
        return set()
    return {(T - 1) * (i + 1) // total for i in range(total)}


def _ratio(e1: int, e0: int) -> float:
    return e1 / e0 if e0 else float("nan")


def write_symbolic_costs(path: str) -> int:
    fields = [
        "n", "T", "store_ratio", "share_eq", "F", "Q", "W", "D",
        "c_eq", "c_sel", "c_upd", "c_upd_separate", "K",
        "e0_secret_mults", "e1_secret_mults", "cost_ratio_e1_over_e0", "e1_wins",
        "e0_rounds_current_executor", "e1_rounds_current_executor",
        "e0_preproc_field_elems", "e1_preproc_field_elems",
        "e0_online_field_elems_per_party", "e1_online_field_elems_per_party",
        "c_eq_status", "c_upd_status", "parameter_status", "row_status",
    ]
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for n in NS:
            for T in TS:
                for ratio in STORE_RATIOS:
                    st = store_steps(T, ratio)
                    W = len(st)
                    F = max(0, T - 1)
                    Q = F - W
                    D = W
                    for share in SHARE_EQ_MODES:
                        e0 = e0_total(T, BASE)
                        e1 = e1_total(T, n, W, BASE, share_eq=share)
                        w.writerow({
                            "n": n, "T": T, "store_ratio": ratio, "share_eq": share,
                            "F": F, "Q": Q, "W": W, "D": D,
                            "c_eq": BASE.c_eq, "c_sel": BASE.c_sel,
                            "c_upd": BASE.c_upd if share else BASE.c_upd_separate,
                            "c_upd_separate": BASE.c_upd_separate, "K": BASE.K,
                            "e0_secret_mults": e0, "e1_secret_mults": e1,
                            "cost_ratio_e1_over_e0": f"{_ratio(e1, e0):.6f}",
                            "e1_wins": int(e1 < e0),
                            "e0_rounds_current_executor": e0 * BASE.rounds_per_mult,
                            "e1_rounds_current_executor": e1 * BASE.rounds_per_mult,
                            "e0_preproc_field_elems": e0 * BASE.field_elems_per_triple,
                            "e1_preproc_field_elems": e1 * BASE.field_elems_per_triple,
                            "e0_online_field_elems_per_party": e0 * BASE.field_elems_exposed_per_mult,
                            "e1_online_field_elems_per_party": e1 * BASE.field_elems_exposed_per_mult,
                            "c_eq_status": DERIVED,
                            "c_upd_status": ASSUMED if share else DERIVED,
                            "parameter_status": f"{DERIVED} for c_eq/c_sel; {ASSUMED} for c_upd/c_sel",
                            "row_status": STATUS,
                        })
                        rows += 1
    return rows


def write_sensitivity_raw(path: str) -> int:
    fields = [
        "eq_ratio", "upd_ratio", "share_eq", "store_ratio", "n", "T", "W",
        "c_eq", "c_sel", "c_upd", "e0_secret_mults", "e1_secret_mults",
        "cost_ratio_e1_over_e0", "e1_wins", "threshold_n_continuous",
        "parameter_status", "row_status",
    ]
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for eq_ratio in EQ_RATIOS:
            for upd_ratio in UPD_RATIOS:
                for share in SHARE_EQ_MODES:
                    p = BASE.scaled(eq_ratio, upd_ratio)
                    for ratio in STORE_RATIOS:
                        for n in NS:
                            for T in TS:
                                st = store_steps(T, ratio)
                                W = len(st)
                                e0 = e0_total(T, p)
                                e1 = e1_total(T, n, W, p, share_eq=share)
                                w.writerow({
                                    "eq_ratio": eq_ratio, "upd_ratio": upd_ratio,
                                    "share_eq": share, "store_ratio": ratio,
                                    "n": n, "T": T, "W": W,
                                    "c_eq": p.c_eq, "c_sel": p.c_sel, "c_upd": p.c_upd,
                                    "e0_secret_mults": e0, "e1_secret_mults": e1,
                                    "cost_ratio_e1_over_e0": f"{_ratio(e1, e0):.6f}",
                                    "e1_wins": int(e1 < e0),
                                    "threshold_n_continuous": f"{cross_threshold_n(T, W, p, share):.4f}",
                                    "parameter_status": (
                                        f"{ASSUMED} (eq_ratio={eq_ratio}, upd_ratio={upd_ratio})"
                                    ),
                                    "row_status": STATUS,
                                })
                                rows += 1
    return rows


def write_sensitivity_summary(path: str, raw_path: str) -> int:
    with open(raw_path, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in raw:
        key = (
            int(r["eq_ratio"]), int(r["upd_ratio"]), r["share_eq"], float(r["store_ratio"]),
        )
        groups[key].append(r)

    fields = [
        "eq_ratio", "upd_ratio", "share_eq", "store_ratio", "cells", "wins", "losses",
        "median_cost_ratio", "min_cost_ratio", "max_cost_ratio",
        "wins_Tn_ge_4", "losses_Tn_le_1", "parameter_status", "row_status",
    ]
    n_written = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for key in sorted(groups):
            rs = groups[key]
            ratios = [float(r["cost_ratio_e1_over_e0"]) for r in rs]
            wins = sum(int(r["e1_wins"]) for r in rs)
            hi = sum(int(r["e1_wins"]) for r in rs if int(r["T"]) / int(r["n"]) >= 4)
            lo = sum((1 - int(r["e1_wins"])) for r in rs if int(r["T"]) / int(r["n"]) <= 1)
            w.writerow({
                "eq_ratio": key[0], "upd_ratio": key[1], "share_eq": key[2],
                "store_ratio": key[3], "cells": len(rs), "wins": wins,
                "losses": len(rs) - wins,
                "median_cost_ratio": f"{statistics.median(ratios):.6f}",
                "min_cost_ratio": f"{min(ratios):.6f}",
                "max_cost_ratio": f"{max(ratios):.6f}",
                "wins_Tn_ge_4": hi, "losses_Tn_le_1": lo,
                "parameter_status": ASSUMED, "row_status": STATUS,
            })
            n_written += 1
    return n_written


def generate_all(outdir: str) -> dict[str, int]:
    os.makedirs(outdir, exist_ok=True)
    symbolic = os.path.join(outdir, "symbolic_costs.csv")
    raw = os.path.join(outdir, "sensitivity_raw.csv")
    summary = os.path.join(outdir, "sensitivity_summary.csv")
    return {
        "symbolic_costs.csv": write_symbolic_costs(symbolic),
        "sensitivity_raw.csv": write_sensitivity_raw(raw),
        "sensitivity_summary.csv": write_sensitivity_summary(summary, raw),
    }


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = os.path.join(here, "results", "exp_doram_08")
    print(generate_all(out))
