#!/usr/bin/env python3
"""Analyze EXP-DORAM-07-R1 benchmark CSVs; print facts for benchmark-analysis.md.

Reads results/exp_doram_07_r1/benchmark_summary.csv and benchmark_raw.csv.
Only computes descriptive statistics; no claim beyond reference-model scope.
"""
from __future__ import annotations

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS = os.path.join(ROOT, "results", "exp_doram_07_r1")
SUM = os.path.join(RESULTS, "benchmark_summary.csv")
RAW = os.path.join(RESULTS, "benchmark_raw.csv")


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def main():
    rows = load(SUM)
    raw = load(RAW)
    print(f"summary rows={len(rows)} raw rows={len(raw)}")
    by = {}
    for r in rows:
        key = (int(r["n"]), int(r["T"]), r["workload"])
        by.setdefault(key, {})[r["impl"]] = r

    # integrity flags
    flags = all(
        r["export_ok"] == "1" and r["returns_ok"] == "1" and r["invariant_ok"] == "1"
        for r in rows
    )
    print("all correctness flags == 1:", flags)

    # --- scan totals (structural, exact) ---
    print("\n=== scan totals by (n,T,workload): EE / FS / E1 ===")
    scan_cells = []
    for key in sorted(by):
        d = by[key]
        ee = d["E0-EarlyExit"]
        fs = d["E0-FullScan"]
        e1 = d["E1-ShadowState"]
        ee_scan = int(ee["history_rows_scanned"]) + int(ee["history_equality_checks"])
        fs_scan = int(fs["history_rows_scanned"]) + int(fs["history_equality_checks"])
        e1_scan = int(e1["shadow_slots_scanned"]) + int(e1["shadow_equality_checks"])
        scan_cells.append((key, ee_scan, fs_scan, e1_scan, e1_scan / fs_scan if fs_scan else 0))
    print(f"{'cell':>16s} {'EE':>10s} {'FS':>10s} {'E1':>10s} {'E1/FS':>7s}")
    for key, ee, fs, e1, ratio in scan_cells:
        print(f"{str(key):>16s} {ee:10d} {fs:10d} {e1:10d} {ratio:7.3f}")

    e1_better = sum(1 for _, _, fs, e1, _ in scan_cells if e1 < fs)
    print(f"\nE1 total scan < E0-FullScan in {e1_better}/{len(scan_cells)} cells")

    # --- E0-EarlyExit vs E0-FullScan scan gap ---
    gaps = [fs / ee for _, ee, fs, _, _ in scan_cells if ee > 0]
    print(f"EE->FS scan ratio (FS/EE): min={min(gaps):.2f} max={max(gaps):.2f} "
          f"median={sorted(gaps)[len(gaps)//2]:.2f}")

    # --- timing ratios E1 vs FullScan (execute & end-to-end) ---
    print("\n=== timing ratios (E1 / E0-FullScan), median basis ===")
    ex_ratios = []
    e2e_ratios = []
    for key in sorted(by):
        d = by[key]
        fs = d["E0-FullScan"]
        e1 = d["E1-ShadowState"]
        er = fnum(e1["execute_ratio_vs_fullscan"])
        tr = fnum(e1["end_to_end_ratio_vs_fullscan"])
        if er is not None:
            ex_ratios.append((key, er))
        if tr is not None:
            e2e_ratios.append((key, tr))
    if ex_ratios:
        vals = [v for _, v in ex_ratios]
        print(f"execute ratio: min={min(vals):.3f} max={max(vals):.3f} "
              f"median={sorted(vals)[len(vals)//2]:.3f}  cells<1={sum(1 for v in vals if v<1)}/{len(vals)}")
    if e2e_ratios:
        vals = [v for _, v in e2e_ratios]
        print(f"end-to-end ratio: min={min(vals):.3f} max={max(vals):.3f} "
              f"median={sorted(vals)[len(vals)//2]:.3f}  cells<1={sum(1 for v in vals if v<1)}/{len(vals)}")

    # --- Export share of end-to-end (FS, E1) ---
    print("\n=== export median as fraction of execute median (max cells) ===")
    for impl in ("E0-FullScan", "E1-ShadowState"):
        fracs = []
        for r in rows:
            if r["impl"] != impl:
                continue
            ex = fnum(r["execute_median_s"]) or 0
            exps = fnum(r["export_median_s"]) or 0
            if ex > 0:
                fracs.append((exps / ex, (int(r["n"]), int(r["T"]), r["workload"])))
        fracs.sort(reverse=True)
        print(f"{impl}: max export/execute={fracs[0][0]:.4f} at {fracs[0][1]}")

    # --- n/T threshold check (E1 scan < FS) ---
    print("\n=== n/T structure: for which T/n does E1 win on scan? ===")
    wins = []
    losses = []
    for key, ee, fs, e1, ratio in scan_cells:
        n, t, wl = key
        (wins if e1 < fs else losses).append((t / n, key, ratio))
    if wins:
        print(f"wins: T/n in [{min(w[0] for w in wins):.3f}, {max(w[0] for w in wins):.3f}]")
    if losses:
        print(f"losses/ties: T/n in [{min(l[0] for l in losses):.3f}, {max(l[0] for l in losses):.3f}]")

    # --- dense_write query benefit vs update cost ---
    print("\n=== dense_write: update vs fetch time share (E1) ===")
    for key in sorted(by):
        n, t, wl = key
        if wl != "dense_write":
            continue
        e1 = by[key]["E1-ShadowState"]
        fet = fnum(e1["fetch_median_s"]) or 0
        upd = fnum(e1["update_median_s"]) or 0
        print(f"{key}: fetch={fet:.6f}s update={upd:.6f}s update/(fetch+update)="
              f"{upd/(fet+upd) if fet+upd>0 else 0:.3f}")

    # --- Python time vs abstract count consistency (FS time vs T^2) ---
    print("\n=== FS execute time vs T^2 monotonic check (per workload) ===")
    for wl in sorted({k[2] for k in by}):
        pts = []
        for (n, t, w), d in sorted(by.items()):
            if w != wl:
                continue
            fs = d["E0-FullScan"]
            pts.append((t, fnum(fs["execute_median_s"]) or 0))
        inc = all(pts[i][1] <= pts[i + 1][1] for i in range(len(pts) - 1))
        print(f"{wl}: execute_median nondecreasing in T: {inc}; "
              f"T=64:{pts[0][1]:.5f}s T=4096:{pts[-1][1]:.5f}s")


if __name__ == "__main__":
    main()
