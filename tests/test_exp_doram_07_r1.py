#!/usr/bin/env python3
"""EXP-DORAM-07-R1 tests: semantics, counters, differential, boundary.

Run:
    PYTHONPATH="src;tests" python -m unittest tests.test_exp_doram_07_r1 -v

Three INDEPENDENT reference models are compared:
    E0-EarlyExit (read-only adapter), E0-FullScan (faithful), E1-ShadowState.

All assertions compare reference-model behaviour only. No cryptographic or
MPC-cost claim is made (see cost-model.md). Every failure below is a real
model defect; do not weaken assertions or delete tests to make them pass.
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.exp_doram_07_r1.e0_early_exit import E0EarlyExitAdapter  # noqa: E402
from src.exp_doram_07_r1.e0_full_scan import E0FullScan  # noqa: E402
from src.exp_doram_07_r1.e1_shadow_state import E1ShadowState  # noqa: E402
from src.exp_doram_07_r1.models import (  # noqa: E402
    DUMMY_ADDR,
    TraceRow,
    latest_value,
    make_trace_row,
)
from src.exp_doram_07_r1.workloads import (  # noqa: E402
    WORKLOADS,
    generate_workload,
    op_counts,
)


def rec(step, op, fa, ta, value=None):
    return {
        "step": step,
        "op": op,
        "fetch_address": fa,
        "trace_address": ta,
        "value": value,
        "workload": "unit",
    }


def make_all(n):
    """Fresh trio of models for the same domain n."""
    return {
        "E0-EarlyExit": E0EarlyExitAdapter(n=n),
        "E0-FullScan": E0FullScan(n=n),
        "E1-ShadowState": E1ShadowState(n=n),
    }


def run_all(models, trace):
    """Run every model on the SAME trace; return its summary dict."""
    return {name: m.run(trace) for name, m in models.items()}


class SemanticTests(unittest.TestCase):
    """12 basic semantic requirements (task 6.1)."""

    def test_01_empty_history_query(self):
        # A single LOAD at step>0 but no prior STORE -> default 0, all agree.
        tr = [rec(0, "NOOP", 0, DUMMY_ADDR), rec(1, "LOAD", 3, 3)]
        models = make_all(8)
        run_all(models, tr)
        for name, m in models.items():
            self.assertEqual(m.actual_returns[-1], 0, name)

    def test_02_first_write(self):
        tr = [
            rec(0, "STORE", 2, 2, 42),  # step 0 zeroShare; store 42
            rec(1, "LOAD", 2, 2),
        ]
        models = make_all(8)
        run_all(models, tr)
        for m in models.values():
            self.assertEqual(m.actual_returns[-1], 42)

    def test_03_same_address_rewrite(self):
        tr = [
            rec(0, "STORE", 1, 1, 1),
            rec(1, "STORE", 1, 1, 2),
            rec(2, "STORE", 1, 1, 3),
            rec(3, "LOAD", 1, 1),
        ]
        models = make_all(8)
        run_all(models, tr)
        for m in models.values():
            self.assertEqual(m.actual_returns[-1], 3)

    def test_04_interleaved_addresses(self):
        tr = [
            rec(0, "STORE", 0, 0, 10),
            rec(1, "STORE", 1, 1, 20),
            rec(2, "STORE", 0, 0, 11),
            rec(3, "LOAD", 0, 0),
            rec(4, "LOAD", 1, 1),
        ]
        models = make_all(8)
        run_all(models, tr)
        for m in models.values():
            self.assertEqual(m.actual_returns[3:5], [11, 20])

    def test_05_never_written_address(self):
        tr = [
            rec(0, "STORE", 0, 0, 7),
            rec(1, "LOAD", 6, 6),
        ]
        models = make_all(8)
        run_all(models, tr)
        for m in models.values():
            self.assertEqual(m.actual_returns[-1], 0)

    def test_06_dummy_fetch(self):
        # STORE and NOOP steps still fetch (scan) but values are unused.
        tr = [
            rec(0, "STORE", 0, 0, 5),
            rec(1, "NOOP", 0, DUMMY_ADDR),   # dummy fetch on addr 0
            rec(2, "STORE", 0, 0, 6),        # store also fetches
            rec(3, "LOAD", 0, 0),
        ]
        models = make_all(8)
        s = run_all(models, tr)
        # every model fetches at steps 1,2,3 => 3 fetches
        for name, sm in s.items():
            self.assertEqual(sm["fetch_count"], 3, name)
        for m in models.values():
            self.assertEqual(m.actual_returns[-1], 6)

    def test_07_step0_zero_share(self):
        tr = [rec(0, "LOAD", 3, 3), rec(1, "LOAD", 3, 3)]
        models = make_all(8)
        s = run_all(models, tr)
        # step 0 does NOT fetch; step 1 fetches once
        for name, sm in s.items():
            self.assertEqual(sm["fetch_count"], 1, name)
        for m in models.values():
            self.assertEqual(m.actual_returns[0], 0)  # step0 zeroShare

    def test_08_fetch_addr_differs_from_trace_addr(self):
        # NOOP: fetch_address ordinary, trace_address NegOne sentinel.
        tr = [
            rec(0, "STORE", 0, 0, 9),
            rec(1, "NOOP", 0, DUMMY_ADDR),
            rec(2, "LOAD", 0, 0),
        ]
        models = make_all(8)
        run_all(models, tr)
        fs = models["E0-FullScan"]
        self.assertEqual(fs.fetch_addresses[0], 0)  # fetch on ordinary addr
        last_row = fs.history[-1] if False else fs.history[1]  # the NOOP row
        self.assertEqual(last_row.mem_addr, DUMMY_ADDR)  # trace addr is NegOne
        for m in models.values():
            self.assertEqual(m.actual_returns[-1], 9)

    def test_09_export_keeps_overwritten_history(self):
        tr = [
            rec(0, "STORE", 1, 1, 1),
            rec(1, "STORE", 1, 1, 2),
            rec(2, "STORE", 1, 1, 3),
        ]
        models = make_all(8)
        run_all(models, tr)
        fs = models["E0-FullScan"]
        vals = [r.mem_val for r in fs.history]
        self.assertEqual(vals, [1, 2, 3])  # all historical writes retained

    def test_10_three_models_same_returns(self):
        tr = generate_workload(16, 120, "uniform", seed=11)
        models = make_all(16)
        run_all(models, tr)
        a = list(models["E0-EarlyExit"].actual_returns)
        b = list(models["E0-FullScan"].actual_returns)
        c = list(models["E1-ShadowState"].actual_returns)
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def test_11_fullscan_vs_e1_export_identical(self):
        for wl in WORKLOADS:
            tr = generate_workload(32, 100, wl, seed=13)
            fs = E0FullScan(n=32)
            e1 = E1ShadowState(n=32)
            fs.run(tr)
            e1.run(tr)
            self.assertEqual(fs.export_fields(), e1.export_fields(), wl)
            self.assertEqual(len(fs.export_fields()), len(tr), wl)

    def test_12_e1_invariant_every_step(self):
        tr = generate_workload(24, 150, "dense_write", seed=17)
        e1 = E1ShadowState(n=24)
        for step_rec in tr:
            e1.execute_step(step_rec)
            ok, msg = e1.invariant()
            self.assertTrue(ok, f"step {step_rec['step']}: {msg}")


class CounterTests(unittest.TestCase):
    """Counter verification with hand-built small scenarios (task 6.2)."""

    def test_c01_fullscan_scans_all_visible_history(self):
        # step s>0 scans exactly s rows (all prior steps' rows).
        tr = [rec(s, "NOOP", 0, DUMMY_ADDR) for s in range(6)]
        fs = E0FullScan(n=4)
        fs.run(tr)
        # steps 1..5 -> 1+2+3+4+5 = 15 rows scanned; step0 none
        self.assertEqual(fs.c.history_rows_scanned, 15)
        self.assertEqual(fs.c.history_equality_checks, 15)
        self.assertEqual(fs.c.fetch_count, 5)

    def test_c02_earlyexit_scans_to_hit_position(self):
        # Fetch on addr 0; most recent write to addr 0 is at row 0 (oldest).
        # Reverse scan must traverse ALL rows to reach it -> equals FullScan here.
        tr = [
            rec(0, "STORE", 0, 0, 1),
            rec(1, "STORE", 1, 1, 2),
            rec(2, "STORE", 2, 2, 3),
            rec(3, "LOAD", 0, 0),
        ]
        ee = E0EarlyExitAdapter(n=4)
        fs = E0FullScan(n=4)
        se = ee.run(tr)
        sf = fs.run(tr)
        # Per-step: step1 fetch scans row0(no match)=1; step2 rows1,0=2;
        # step3 rows2,1,0 -> match at row0 =3. EE total = 1+2+3=6 == full here
        # because the newest matching row is the OLDEST row.
        self.assertEqual(se["history_rows_scanned"], 6)
        self.assertEqual(sf["history_rows_scanned"], 1 + 2 + 3)

    def test_c03_earlyexit_stops_at_newest_match(self):
        # Most recent write to addr 0 is newest row -> early exit after 1 row.
        tr = [
            rec(0, "STORE", 0, 0, 1),
            rec(1, "STORE", 0, 0, 2),
            rec(2, "STORE", 0, 0, 3),
            rec(3, "LOAD", 0, 0),
        ]
        ee = E0EarlyExitAdapter(n=4)
        se = ee.run(tr)
        # step1 fetch scans row0 -> 1; step2 scans row1 -> 1; step3 scans row2 -> 1
        total = se["history_rows_scanned"]
        self.assertEqual(total, 3)

    def test_c04_e1_scans_n_per_fetch_and_update(self):
        tr = [
            rec(0, "STORE", 1, 1, 5),  # update: n slots
            rec(1, "LOAD", 1, 1),      # fetch: n slots
        ]
        e1 = E1ShadowState(n=10)
        sm = e1.run(tr)
        # 1 fetch (step1) + 1 store update (step0) => 2*n slot scans
        self.assertEqual(sm["shadow_slots_scanned"], 20)
        self.assertEqual(sm["shadow_equality_checks"], 20)

    def test_c05_step0_not_counted_as_fetch(self):
        tr = [rec(0, "STORE", 0, 0, 1)]
        for n, model in [
            ("ee", E0EarlyExitAdapter(n=2)),
            ("fs", E0FullScan(n=2)),
            ("e1", E1ShadowState(n=2)),
        ]:
            sm = model.run(tr)
            self.assertEqual(sm["fetch_count"], 0, n)
            self.assertEqual(sm["history_append_operations"], 1, n)

    def test_c06_dummy_fetch_not_missed(self):
        tr = [
            rec(0, "STORE", 0, 0, 1),
            rec(1, "NOOP", 0, DUMMY_ADDR),
            rec(2, "NOOP", 3, DUMMY_ADDR),
        ]
        for name, model in make_all(4).items():
            sm = model.run(tr)
            self.assertEqual(sm["fetch_count"], 2, name)  # steps 1,2 fetch

    def test_c07_fullscan_never_early_exits_even_on_hit(self):
        # Every row has the target address -> EarlyExit scans 1; FullScan scans all.
        tr = [
            rec(0, "STORE", 0, 0, 1),
            rec(1, "STORE", 0, 0, 2),
            rec(2, "STORE", 0, 0, 3),
            rec(3, "LOAD", 0, 0),
        ]
        ee = E0EarlyExitAdapter(n=2)
        fs = E0FullScan(n=2)
        se = ee.run(tr)["history_rows_scanned"]
        sf = fs.run(tr)["history_rows_scanned"]
        # EE: step1=1,step2=1,step3=1 => 3 ; FS: 1+2+3=6
        self.assertEqual(se, 3)
        self.assertEqual(sf, 6)


class RandomDifferentialTests(unittest.TestCase):
    """>=100 fixed-seed sequences, step-by-step + export comparison (6.3)."""

    def test_100_random_sequences_all_models_agree(self):
        checked = 0
        for seed in range(100):
            n = [1, 2, 8, 16, 64][seed % 5]
            t = 20 + (seed % 40)
            wl = WORKLOADS[seed % len(WORKLOADS)]
            tr = generate_workload(n, t, wl, seed=1000 + seed)
            models = make_all(n)
            # step-by-step comparison
            for step_rec in tr:
                returns = {k: m.execute_step(step_rec) for k, m in models.items()}
                self.assertEqual(
                    len(set(returns.values())), 1,
                    f"seed={seed} step={step_rec['step']} returns={returns}",
                )
            # export field-for-field (FullScan vs E1, and vs EarlyExit)
            ef = models["E0-FullScan"].export_fields()
            e1 = models["E1-ShadowState"].export_fields()
            ee = models["E0-EarlyExit"].export_fields()
            self.assertEqual(ef, e1, f"export mismatch seed={seed} wl={wl}")
            self.assertEqual(ee, ef, f"EE export mismatch seed={seed} wl={wl}")
            ok, msg = models["E1-ShadowState"].invariant()
            self.assertTrue(ok, f"invariant seed={seed}: {msg}")
            checked += 1
        self.assertEqual(checked, 100)


class BoundaryTests(unittest.TestCase):
    """Boundary cases (task 6.4)."""

    def _run_case(self, n, t, wl="uniform", seed=5):
        tr = generate_workload(n, t, wl, seed=seed)
        models = make_all(n)
        run_all(models, tr)
        self.assertEqual(
            models["E0-FullScan"].export_fields(),
            models["E1-ShadowState"].export_fields(),
        )
        self.assertEqual(
            list(models["E0-EarlyExit"].actual_returns),
            list(models["E0-FullScan"].actual_returns),
        )
        ok, msg = models["E1-ShadowState"].invariant()
        self.assertTrue(ok, msg)

    def test_b_n1(self):
        self._run_case(1, 30)

    def test_b_n2(self):
        self._run_case(2, 30)

    def test_b_T_less_than_n(self):
        self._run_case(64, 16)

    def test_b_T_equal_n(self):
        self._run_case(32, 32)

    def test_b_T_greater_than_n(self):
        self._run_case(8, 200)

    def test_b_unwritten_address(self):
        tr = [rec(0, "STORE", 0, 0, 1), rec(1, "LOAD", 99, 99)]
        models = make_all(100)
        run_all(models, tr)
        for m in models.values():
            self.assertEqual(m.actual_returns[-1], 0)

    def test_b_single_hotspot(self):
        self._run_case(16, 128, "single_hotspot")

    def test_b_all_addresses_covered(self):
        # dense write over all n addresses
        self._run_case(16, 400, "dense_write")

    def test_b_invalid_address_nondomain_returns_default(self):
        # out-of-domain fetch returns 0 in both E0-FullScan and E1.
        tr = [rec(0, "STORE", 0, 0, 5), rec(1, "LOAD", DUMMY_ADDR, DUMMY_ADDR)]
        fs = E0FullScan(n=4)
        e1 = E1ShadowState(n=4)
        fs.run(tr)
        e1.run(tr)
        self.assertEqual(fs.actual_returns[-1], 0)
        self.assertEqual(e1.actual_returns[-1], 0)

    def test_b_illegal_n(self):
        with self.assertRaises(ValueError):
            E1ShadowState(n=0)
        with self.assertRaises(ValueError):
            E1ShadowState(n=-3)

    def test_b_unknown_op(self):
        with self.assertRaises(ValueError):
            make_trace_row("JUMP", 0, 0, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
