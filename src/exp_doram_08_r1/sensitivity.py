#!/usr/bin/env python3
"""Deterministic symbolic sensitivity scan for EXP-DORAM-08-R1.

Writes results/exp_doram_08_r1/{symbolic_costs,sensitivity_raw,sensitivity_summary}.csv.
ALL cost parameters here are symbolic/assumed, never measured MPC benchmark.
Every row carries parameter_status.
"""

from __future__ import annotations

import csv
import os
import statistics
from itertools import product

from .costs import (
    CostParams,
    e0_total_closed,
    e0_total_by_sum,
    e1a_total_closed,
    e1a_total_by_sum,
    e1b_total_closed,
    e1b_total_by_sum,
    cross_threshold_n,
    rounds_from_mults,
    preproc_field_elems,
    online_field_elems,
)

NS = [16, 64, 256, 1024]
TS = [64, 256, 1024, 4096]
STORE_RATIOS = [0.0, 0.1, 0.5, 0.9, 1.0]
VARIANTS = ["E1-A", "E1-B"]
UPDATE_MODES = ["shared", "separate"]
EQ_RATIOS = [1, 389]           # 389 = source-derived; 1 = ASSUMED stress case
UPD_RATIOS = [2, 100]          # 2 = source-derived (R1-1 c_upd_shared); 100 = ASSUMED stress
STATUS_DERIVED = "DERIVED"
STATUS_ASSUMED = "ASSUMED"
MODEL_VERSION = "R1-C1"  # R1-C1: corrected crossover + unified append closed form

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(HERE, "..", "..", "results", "exp_doram_08_r1"))


def make_store_steps(T: int, ratio: float, strategy: str) -> set[int]:
    """Deterministic STORE step set for a given ratio and placement strategy.

    strategy 'uniform': every round step (plus step0 when ratio>0 and ceil).
    strategy 'step0': step0 included iff ratio>0 (tests step-0 boundary impact).
    """
    if T <= 0:
        return set()
    if strategy == "step0":
        return {0} if ratio > 0 else set()
    k = int(round(ratio * T))
    if strategy == "no_step0":
        # same count k, shifted off step 0 -> steps 1..k (clipped to T)
        return set(range(1, min(k + 1, T)))
    # uniform: pick first ceil(ratio*T) steps deterministically (includes step 0)
    return set(range(k))


def _param_status(p: CostParams, eq_ratio: int, upd_ratio: int) -> str:
    if eq_ratio == 389 and upd_ratio == 2:
        return STATUS_DERIVED
    return STATUS_ASSUMED


def _total(variant: str, T: int, n: int, steps: set[int], p: CostParams,
           share_eq: bool, by_sum: bool = False):
    if variant == "E0-FullScan":
        return e0_total_by_sum(T, p) if by_sum else e0_total_closed(T, p)
    fn_sum = e1a_total_by_sum if variant == "E1-A" else e1b_total_by_sum
    fn_cls = e1a_total_closed if variant == "E1-A" else e1b_total_closed
    return fn_sum(T, n, steps, p, share_eq) if by_sum else fn_cls(T, n, steps, p, share_eq)


def gen_symbolic_costs() -> int:
    """One row per (variant,T,n,store_ratio,update_mode) at source-derived params."""
    path = os.path.join(RESULTS, "symbolic_costs.csv")
    cols = [
        "model_version", "model_variant", "T", "n", "store_ratio",
        "store_step_strategy", "update_mode", "c_eq", "c_sel", "c_upd",
        "c_upd_separate", "parameter_status", "e0_cost", "e1_cost",
        "cost_ratio_e1_over_e0", "winner", "fetch_cost", "update_cost",
        "linear_ops_e1", "rounds_e1", "preproc_elems_e1", "online_elems_e1",
    ]
    rows = []
    p = CostParams()
    for T, n, ratio, strategy in product(TS, NS, STORE_RATIOS,
                                         ["uniform", "step0", "no_step0"]):
        steps = make_store_steps(T, ratio, strategy)
        e0 = e0_total_closed(T, p)
        for variant in VARIANTS:
            for mode in UPDATE_MODES:
                share_eq = mode == "shared"
                e1 = _total(variant, T, n, steps, p, share_eq)
                ratio_v = e1 / e0 if e0 else float("nan")
                if variant == "E1-A":
                    fetch = (T - 1) * p.fetch_a(n)
                    linear = (T - 1) * (4 * n - 1) + 2 * n * len(steps)
                else:
                    fetch = (T - 1) * p.fetch_b(n)
                    linear = (T - 1) * (3 * n - 1) + 2 * n * len(steps)
                w0 = 1 if 0 in steps else 0
                wpos = len(steps) - w0
                upd = w0 * n * p.c_upd_separate + wpos * n * (
                    p.c_upd_shared if share_eq else p.c_upd_separate)
                rows.append({
                    "model_version": MODEL_VERSION,
                    "model_variant": variant,
                    "T": T, "n": n, "store_ratio": ratio,
                    "store_step_strategy": strategy,
                    "update_mode": mode,
                    "c_eq": p.c_eq, "c_sel": p.c_sel,
                    "c_upd": p.c_upd_shared, "c_upd_separate": p.c_upd_separate,
                    "parameter_status": STATUS_DERIVED,
                    "e0_cost": e0, "e1_cost": e1,
                    "cost_ratio_e1_over_e0": f"{ratio_v:.6f}",
                    "winner": "E1" if e1 < e0 else ("E0" if e0 < e1 else "TIE"),
                    "fetch_cost": fetch, "update_cost": upd,
                    "linear_ops_e1": linear,
                    "rounds_e1": rounds_from_mults(e1, p),
                    "preproc_elems_e1": preproc_field_elems(e1, p),
                    "online_elems_e1": online_field_elems(e1, p),
                })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def gen_sensitivity_raw() -> int:
    """Parameter sweep with ASSUMED weight regimes."""
    path = os.path.join(RESULTS, "sensitivity_raw.csv")
    cols = [
        "model_version", "model_variant", "T", "n", "store_ratio",
        "store_step_strategy", "update_mode", "eq_ratio", "upd_ratio",
        "c_eq", "c_sel", "c_upd", "c_upd_separate", "parameter_status",
        "e0_cost", "e1_cost", "cost_ratio_e1_over_e0", "winner",
        "threshold_n_continuous", "fetch_cost", "update_cost",
    ]
    rows = []
    for T, n, ratio, variant, mode, eqr, upr in product(
            TS, NS, STORE_RATIOS, VARIANTS, UPDATE_MODES, EQ_RATIOS, UPD_RATIOS):
        p = CostParams().scaled(eqr, upr)
        steps = make_store_steps(T, ratio, "uniform")
        share_eq = mode == "shared"
        e0 = e0_total_closed(T, p)
        e1 = _total(variant, T, n, steps, p, share_eq)
        ratio_v = e1 / e0 if e0 else float("nan")
        thr = cross_threshold_n(T, steps, "A" if variant == "E1-A" else "B", p, share_eq)
        if variant == "E1-A":
            fetch = (T - 1) * p.fetch_a(n)
        else:
            fetch = (T - 1) * p.fetch_b(n)
        w0 = 1 if 0 in steps else 0
        wpos = len(steps) - w0
        upd = w0 * n * p.c_upd_separate + wpos * n * (
            p.c_upd_shared if share_eq else p.c_upd_separate)
        rows.append({
            "model_version": MODEL_VERSION,
            "model_variant": variant, "T": T, "n": n,
            "store_ratio": ratio, "store_step_strategy": "uniform",
            "update_mode": mode, "eq_ratio": eqr, "upd_ratio": upr,
            "c_eq": p.c_eq, "c_sel": p.c_sel, "c_upd": p.c_upd_shared,
            "c_upd_separate": p.c_upd_separate,
            "parameter_status": _param_status(p, eqr, upr),
            "e0_cost": e0, "e1_cost": e1,
            "cost_ratio_e1_over_e0": f"{ratio_v:.6f}",
            "winner": "E1" if e1 < e0 else ("E0" if e0 < e1 else "TIE"),
            "threshold_n_continuous": f"{thr:.4f}",
            "fetch_cost": fetch, "update_cost": upd,
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def gen_sensitivity_summary() -> int:
    """Aggregate raw by (variant,store_ratio,mode,eq_ratio,upd_ratio)."""
    raw_path = os.path.join(RESULTS, "sensitivity_raw.csv")
    out_path = os.path.join(RESULTS, "sensitivity_summary.csv")
    with open(raw_path, encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    groups: dict[tuple, list[dict]] = {}
    for r in raw:
        key = (r["model_variant"], r["store_ratio"], r["update_mode"],
               r["eq_ratio"], r["upd_ratio"])
        groups.setdefault(key, []).append(r)
    cols = [
        "model_version", "model_variant", "store_ratio", "update_mode",
        "eq_ratio", "upd_ratio", "parameter_status", "cells", "wins_e1",
        "losses_e1", "ties", "median_cost_ratio", "min_cost_ratio",
        "max_cost_ratio", "wins_Tn_ge_4", "wins_Tn_le_1", "losses_Tn_le_1",
    ]
    out = []
    for key, rs in sorted(groups.items()):
        variant, ratio, mode, eqr, upr = key
        ratios = [float(x["cost_ratio_e1_over_e0"]) for x in rs]
        wins = sum(1 for x in rs if x["winner"] == "E1")
        losses = sum(1 for x in rs if x["winner"] == "E0")
        ties = len(rs) - wins - losses
        ge4 = sum(1 for x in rs if x["winner"] == "E1"
                  and int(x["T"]) / int(x["n"]) >= 4)
        le1 = [x for x in rs if int(x["T"]) / int(x["n"]) <= 1]
        le1_wins = sum(1 for x in le1 if x["winner"] == "E1")
        le1_losses = sum(1 for x in le1 if x["winner"] == "E0")
        out.append({
            "model_version": MODEL_VERSION,
            "model_variant": variant, "store_ratio": ratio,
            "update_mode": mode, "eq_ratio": eqr, "upd_ratio": upr,
            "parameter_status": rs[0]["parameter_status"],
            "cells": len(rs), "wins_e1": wins, "losses_e1": losses, "ties": ties,
            "median_cost_ratio": f"{statistics.median(ratios):.6f}",
            "min_cost_ratio": f"{min(ratios):.6f}",
            "max_cost_ratio": f"{max(ratios):.6f}",
            "wins_Tn_ge_4": ge4, "wins_Tn_le_1": le1_wins,
            "losses_Tn_le_1": le1_losses,
        })
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    return len(out)


def main():
    os.makedirs(RESULTS, exist_ok=True)
    a = gen_symbolic_costs()
    b = gen_sensitivity_raw()
    c = gen_sensitivity_summary()
    print(f"symbolic_costs.csv: {a} rows")
    print(f"sensitivity_raw.csv: {b} rows")
    print(f"sensitivity_summary.csv: {c} rows")


if __name__ == "__main__":
    main()
