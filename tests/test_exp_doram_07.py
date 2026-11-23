#!/usr/bin/env python3
"""EXP-DORAM-07 tests: semantic, differential (100 seeds), boundary.

Run:
    python -m unittest discover -s tests -p "test_exp_doram_07.py" -v

All tests compare the two REFERENCE MODELS only. E1 is a plain array model,
NOT an ORAM; no security claim is made.
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.exp_doram_07.historical_kv import HistoricalKVLinearScan  # noqa: E402
from src.exp_doram_07.shadow_state import ShadowStateTable  # noqa: E402
from src.exp_doram_07.models import DUMMY_ADDR, latest_value  # noqa: E402
from src.exp_doram_07.workloads import WORKLOADS, generate_workload  # noqa: E402


def rec(step, op, fa, ta, value=None):
    return {
        "step": step, "op": op, "fetch_address": fa,
        "trace_address": ta, "value": value, "workload": "unit",
    }


def build_pair(n):
    return HistoricalKVLinearScan(n=n), ShadowStateTable(n=n)


def run_stepwise(trace, n):
    """Run both models step by step, recording per-step Query + invariant."""
    e0, e1 = build_pair(n)
    returns0, returns1 = [], []
    inv_ok = True
    for r in trace:
        returns0.append(e0.execute_step(r))
        returns1.append(e1.execute_step(r))
        ok, _ = e1.invariant()
        inv_ok = inv_ok and ok
    return e0, e1, returns0, returns1, inv_ok


class SemanticTests(unittest.TestCase):
    """12 required semantic tests (task 6.1)."""

    def test_01_empty_history_query(self):
        e0, e1 = build_pair(4)
        self.assertEqual(e0.fetch(0), 0)
        self.assertEqual(e1.fetch(0), 0)
        self.assertEqual(e0.export_fields(), [])
        self.assertEqual(e1.export_fields(), [])

    def test_02_first_write(self):
        tr = [rec(0, "STORE", 3, 3, 42), rec(1, "LOAD", 3, 3)]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertEqual(r0, [42, 42])
        self.assertEqual(r1, r0)
        self.assertTrue(inv)

    def test_03_same_address_overwrite(self):
        tr = [
            rec(0, "STORE", 2, 2, 5),
            rec(1, "STORE", 2, 2, 8),
            rec(2, "LOAD", 2, 2),
        ]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertEqual(r0, [5, 8, 8])
        self.assertEqual(r1, r0)
        self.assertTrue(inv)
        self.assertEqual(e1.shadow_snapshot()[2], 8)

    def test_04_interleaved_writes(self):
        tr = [
            rec(0, "STORE", 0, 0, 10),
            rec(1, "STORE", 1, 1, 20),
            rec(2, "LOAD", 0, 0),
            rec(3, "LOAD", 1, 1),
            rec(4, "STORE", 0, 0, 30),
            rec(5, "LOAD", 1, 1),
            rec(6, "LOAD", 0, 0),
        ]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertEqual(r0, [10, 20, 10, 20, 30, 20, 30])
        self.assertEqual(r1, r0)
        self.assertTrue(inv)

    def test_05_never_written_address(self):
        tr = [rec(0, "STORE", 0, 0, 7), rec(1, "LOAD", 3, 3)]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertEqual(r0, [7, 0])
        self.assertEqual(r1, r0)
        self.assertTrue(inv)

    def test_06_dummy_fetch(self):
        tr = [
            rec(0, "STORE", 1, 1, 9),
            rec(1, "NOOP", 1, DUMMY_ADDR),
            rec(2, "LOAD", 1, 1),
        ]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertEqual(r0, [9, 0, 9])
        self.assertEqual(r1, r0)
        # Both perform a Fetch at step 1 and step 2 (T-1 total).
        self.assertEqual(e0.c.fetch_count, 2)
        self.assertEqual(e1.c.fetch_count, 2)
        # Dummy row retained with NegOne trace address.
        self.assertEqual(e0.history[1].mem_addr, DUMMY_ADDR)
        self.assertEqual(e1.history[1].mem_addr, DUMMY_ADDR)
        self.assertTrue(inv)

    def test_07_step0_special(self):
        tr = [rec(0, "LOAD", 2, 2), rec(1, "LOAD", 2, 2)]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertEqual(r0[0], 0)  # zeroShare at step 0
        self.assertEqual(e0.c.fetch_count, 1)  # no Fetch at step 0
        self.assertEqual(e1.c.fetch_count, 1)
        self.assertEqual(r1, r0)

    def test_08_fetch_address_differs_from_trace_address(self):
        tr = [rec(0, "STORE", 2, 2, 77), rec(1, "NOOP", 2, DUMMY_ADDR)]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        self.assertNotEqual(tr[1]["fetch_address"], tr[1]["trace_address"])
        self.assertEqual(e0.fetch_addresses, [2])
        self.assertEqual(e1.fetch_addresses, [2])
        self.assertEqual(e1.history[1].mem_addr, DUMMY_ADDR)
        self.assertEqual(r1, r0)

    def test_09_export_keeps_overwritten_values(self):
        tr = [
            rec(0, "STORE", 0, 0, 1),
            rec(1, "STORE", 0, 0, 2),
            rec(2, "NOOP", 0, DUMMY_ADDR),
        ]
        e0, e1, r0, r1, inv = run_stepwise(tr, 4)
        vals = [row.mem_val for row in e0.history]
        self.assertEqual(vals, [1, 2, 0])
        self.assertEqual(len(e0.history), 3)
        self.assertEqual(e1.export_fields(), e0.export_fields())

    def test_10_query_equal_after_every_operation(self):
        tr = generate_workload(16, 64, "uniform", seed=1)
        e0, e1, r0, r1, inv = run_stepwise(tr, 16)
        for i, (a, b) in enumerate(zip(r0, r1)):
            self.assertEqual(a, b, f"step {i}")
        self.assertTrue(inv)

    def test_11_export_identical(self):
        for workload in WORKLOADS:
            tr = generate_workload(32, 128, workload, seed=2)
            e0, e1, r0, r1, inv = run_stepwise(tr, 32)
            self.assertEqual(e0.export_fields(), e1.export_fields(), workload)

    def test_12_invariant_every_step(self):
        for workload in WORKLOADS:
            tr = generate_workload(8, 96, workload, seed=3)
            _, _, _, _, inv = run_stepwise(tr, 8)
            self.assertTrue(inv, workload)


class DifferentialTests(unittest.TestCase):
    """At least 100 fixed-seed differential sequences (task 6.2)."""

    def test_100_random_sequences(self):
        for seed in range(100):
            n = [1, 2, 4, 8, 16][seed % 5]
            t = 8 + (seed % 23)
            workload = WORKLOADS[seed % len(WORKLOADS)]
            tr = generate_workload(n, t, workload, seed=9000 + seed)
            e0, e1 = build_pair(n)
            for step, r in enumerate(tr):
                a = e0.execute_step(r)
                b = e1.execute_step(r)
                self.assertEqual(a, b, f"seed={seed} step={step} returns")
                # Query every address after each step; both must agree.
                for addr in range(n):
                    self.assertEqual(
                        e0.fetch(addr), e1.fetch(addr),
                        f"seed={seed} step={step} query addr={addr}",
                    )
                ok, why = e1.invariant()
                self.assertTrue(ok, f"seed={seed} step={step} invariant: {why}")
            self.assertEqual(e0.export_fields(), e1.export_fields(), f"seed={seed} export")
            self.assertEqual(e0.c.fetch_count, e1.c.fetch_count)


class CounterTests(unittest.TestCase):
    """Counter expectations are abstract model counts, not MPC costs."""

    def test_counter_relationships(self):
        tr = generate_workload(16, 128, "uniform", seed=7)
        e0, e1, _, _, _ = run_stepwise(tr, 16)
        for m in (e0, e1):
            self.assertEqual(m.c.fetch_count, 127)          # T-1
            self.assertEqual(m.c.history_append_operations, 128)  # T rows
            self.assertEqual(len(m.history), 128)
        # E0 scans history rows on Fetch; E1 scans a fixed n slots per Fetch
        # plus n slots per Update.
        self.assertGreater(e0.c.history_rows_scanned, 0)
        self.assertGreater(e1.c.shadow_slots_scanned, 0)
        self.assertEqual(e1.c.equality_checks, e1.c.shadow_slots_scanned)

    def test_e1_scans_fixed_n_per_fetch_and_update(self):
        tr = generate_workload(16, 64, "dense_write", seed=8)
        e1 = ShadowStateTable(n=16)
        for r in tr:
            e1.execute_step(r)
        expected_slots = 16 * e1.c.fetch_count + 16 * e1.c.update_count
        self.assertEqual(e1.c.shadow_slots_scanned, expected_slots)


class BoundaryTests(unittest.TestCase):
    """Boundary cases (task 6.3)."""

    def test_n_1(self):
        tr = generate_workload(1, 12, "dense_write", seed=9)
        e0, e1, r0, r1, inv = run_stepwise(tr, 1)
        self.assertEqual(r0, r1)
        self.assertTrue(inv)
        for r in tr:
            self.assertIn(r["fetch_address"], (0, DUMMY_ADDR))

    def test_n_2(self):
        tr = generate_workload(2, 24, "uniform", seed=10)
        e0, e1, r0, r1, inv = run_stepwise(tr, 2)
        self.assertEqual(r0, r1)
        self.assertTrue(inv)

    def test_all_unwritten(self):
        tr = [rec(i, "LOAD", i % 3, i % 3) for i in range(6)]
        tr[0] = rec(0, "NOOP", 0, DUMMY_ADDR)
        e0, e1, r0, r1, inv = run_stepwise(tr, 3)
        self.assertTrue(all(v == 0 for v in r0))
        self.assertEqual(r0, r1)
        self.assertTrue(inv)

    def test_single_address_frequent(self):
        tr = [rec(i, "STORE", 0, 0, i + 1) for i in range(20)]
        tr.append(rec(20, "LOAD", 0, 0))
        e0, e1, r0, r1, inv = run_stepwise(tr, 8)
        self.assertEqual(r0[-1], 20)
        self.assertEqual(r0, r1)
        self.assertTrue(inv)

    def test_all_addresses_written(self):
        n = 5
        tr = [rec(i, "STORE", i, i, i * 3) for i in range(n)]
        tr += [rec(n + i, "LOAD", i, i) for i in range(n)]
        e0, e1, r0, r1, inv = run_stepwise(tr, n)
        self.assertEqual(r0[n:], [0, 3, 6, 9, 12])
        self.assertEqual(r0, r1)
        self.assertTrue(inv)

    def test_t_less_than_n(self):
        for n, t in ((1024, 64), (64, 16)):
            tr = generate_workload(n, t, "sparse_write", seed=11)
            e0, e1, r0, r1, inv = run_stepwise(tr, n)
            self.assertEqual(r0, r1)
            self.assertTrue(inv)

    def test_t_equals_n(self):
        tr = generate_workload(32, 32, "hotspot", seed=12)
        e0, e1, r0, r1, inv = run_stepwise(tr, 32)
        self.assertEqual(r0, r1)
        self.assertTrue(inv)

    def test_t_greater_than_n(self):
        tr = generate_workload(16, 512, "single_hot", seed=13)
        e0, e1, r0, r1, inv = run_stepwise(tr, 16)
        self.assertEqual(r0, r1)
        self.assertTrue(inv)

    def test_illegal_address(self):
        n = 4
        e0, e1 = build_pair(n)
        # Query out-of-domain: default 0 in both models (MODEL convention).
        self.assertEqual(e0.fetch(999), 0)
        self.assertEqual(e1.fetch(999), 0)
        self.assertEqual(e0.fetch(-1), 0)
        self.assertEqual(e1.fetch(-1), 0)
        # Illegal STORE appends a history row but updates no shadow slot;
        # invariant over [0,n-1] still holds.
        tr = [
            rec(0, "STORE", 999, 999, 5),
            rec(1, "LOAD", 0, 0),
        ]
        e0, e1, r0, r1, inv = run_stepwise(tr, n)
        self.assertEqual(r0, [5, 0])
        self.assertEqual(r1, r0)
        self.assertTrue(inv)
        self.assertEqual(latest_value(e1.history, 0), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
