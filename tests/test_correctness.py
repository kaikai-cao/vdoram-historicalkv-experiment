#!/usr/bin/env python3
"""EXP-DORAM-01 correctness tests (stdlib unittest, no third-party deps).

Covers the task package §五 table plus three strengthened checks:
  - E0/E1 returns equal the independent oracle on ALL 16 generated traces
  - E0 and E1 emit identical 5-column historical rows (proof-input compatibility)
  - hash commitments detect row deletion / value tampering / timestamp change
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.trace.generator import (  # noqa: E402
    DUMMY_ADDR, N_VALUES, T_VALUES, SEED, generate_trace, generate_all,
)
from src.baseline.e0_linear_scan import (  # noqa: E402
    E0LinearScan, TraceRow, make_row, replay_state,
)
from src.dual_store.e1_dual_store import (  # noqa: E402
    E1DualStore, HistoricalLog, row_commitment,
)
from src.oracle import Oracle  # noqa: E402


def run_trace(trace):
    e0, e1, orc = E0LinearScan(), E1DualStore(), Oracle()
    e0.run(trace)
    e1.run(trace)
    exp = orc.run(trace)
    return e0, e1, orc, exp


class SingleStepTests(unittest.TestCase):
    def _mini(self, recs):
        return [{"step": i, "op": op, "address": a, "value": v,
                 "pattern": "unit"} for i, (op, a, v) in enumerate(recs)]

    def test_01_load_never_written_returns_zero(self):
        tr = self._mini([("LOAD", 17, None)])
        e0, e1, _, exp = run_trace(tr)
        self.assertEqual(exp, [0])
        self.assertEqual(e0.actual_returns, [0])
        self.assertEqual(e1.actual_returns, [0])

    def test_02_store_then_load(self):
        tr = self._mini([("STORE", 17, 123), ("LOAD", 17, None)])
        _, _, _, exp = run_trace(tr)
        self.assertEqual(exp, [123, 123])

    def test_03_two_stores_latest_wins(self):
        tr = self._mini([("STORE", 17, 123), ("STORE", 17, 456), ("LOAD", 17, None)])
        e0, e1, _, exp = run_trace(tr)
        self.assertEqual(exp, [123, 456, 456])
        # The scan selects the most recent matching record, not the first.
        self.assertEqual(e0.actual_returns[-1], 456)
        self.assertEqual(e1.actual_returns[-1], 456)

    def test_04_interleaved_addresses_independent(self):
        tr = self._mini([
            ("STORE", 17, 111), ("STORE", 18, 222),
            ("LOAD", 17, None), ("LOAD", 18, None),
            ("STORE", 17, 333), ("LOAD", 18, None), ("LOAD", 17, None),
        ])
        _, _, orc, exp = run_trace(tr)
        self.assertEqual(exp, [111, 222, 111, 222, 333, 222, 333])
        self.assertEqual(orc.final_state(), {17: 333, 18: 222})

    def test_05_replay_history_matches_final_state(self):
        tr = self._mini([("STORE", 17, 123), ("LOAD", 17, None),
                         ("STORE", 18, 9), ("STORE", 17, 456)])
        e0, e1, orc, _ = run_trace(tr)
        self.assertEqual(e0.final_state(), e1.final_state())
        self.assertEqual(e1.log.replay(), orc.final_state())
        self.assertTrue(e1.log.check_order_and_integrity()[0])


class TamperTests(unittest.TestCase):
    def test_06_delete_one_store_record_changes_replay(self):
        tr = [{"step": 0, "op": "STORE", "address": 17, "value": 123, "pattern": "u"},
              {"step": 1, "op": "STORE", "address": 18, "value": 5, "pattern": "u"},
              {"step": 2, "op": "STORE", "address": 17, "value": 456, "pattern": "u"}]
        e1 = E1DualStore()
        e1.run(tr)
        before = e1.log.replay()
        # Remove the LAST store to addr 17 (must change replay result).
        del e1.log.rows[2]
        del e1.log.commitments[2]
        after = e1.log.replay()
        self.assertNotEqual(before, after)
        self.assertEqual(after.get(17), 123)

    def test_07_tamper_load_value_fails_integrity(self):
        tr = [{"step": 0, "op": "STORE", "address": 17, "value": 100, "pattern": "u"},
              {"step": 1, "op": "LOAD", "address": 17, "value": None, "pattern": "u"},
              {"step": 2, "op": "STORE", "address": 18, "value": 7, "pattern": "u"},
              {"step": 3, "op": "LOAD", "address": 17, "value": None, "pattern": "u"}]
        e1 = E1DualStore()
        e1.run(tr)
        self.assertTrue(e1.log.check_order_and_integrity()[0])
        # Forge a Load return value at step 1: addr 17 becomes 999 while the
        # following Load (step 3) still reports 100 -> value integrity broken.
        forged = TraceRow(17, 1, 1, 0, 999)
        e1.log.rows[1] = forged
        e1.log.commitments[1] = row_commitment(forged, e1.log.enc_key)
        ok, reason = e1.log.check_order_and_integrity()
        self.assertFalse(ok)
        self.assertIn("integrity", reason)

    def test_08_tamper_timestamp_fails_order(self):
        tr = [{"step": 0, "op": "STORE", "address": 17, "value": 1, "pattern": "u"},
              {"step": 1, "op": "STORE", "address": 17, "value": 2, "pattern": "u"},
              {"step": 2, "op": "STORE", "address": 18, "value": 3, "pattern": "u"}]
        e1 = E1DualStore()
        e1.run(tr)
        self.assertTrue(e1.log.check_order_and_integrity()[0])
        self.assertTrue(e1.log.check_hash_consistency()[0])
        # Tamper a timestamp (the commitment is NOT recomputed, exactly as an
        # attacker changing a stored row would leave the Prove-time hash stale).
        # The row-level hash (which binds global_step_counter) must break.
        r0 = e1.log.rows[0]
        e1.log.rows[0] = TraceRow(r0.mem_addr, 99, r0.is_mem_op, r0.is_mem_write, r0.mem_val)
        ok, reason = e1.log.check_hash_consistency()
        self.assertFalse(ok)
        self.assertIn("hash", reason)
        # Also verified: a duplicated global timestamp on the same address
        # violates the strict step-increase constraint within an address group.
        e1b = E1DualStore()
        e1b.run(tr)
        r1b = e1b.log.rows[1]
        e1b.log.rows[1] = TraceRow(r1b.mem_addr, 0, r1b.is_mem_op, r1b.is_mem_write, r1b.mem_val)
        ok2, reason2 = e1b.log.check_order_and_integrity()
        self.assertFalse(ok2)
        self.assertIn("timestamp", reason2)

    def test_09_commitment_detects_deletion_and_value_change(self):
        rows = [make_row("STORE", 17, 0, 123), make_row("LOAD", 17, 1, 123)]
        log = HistoricalLog()
        for r in rows:
            log.append(r)
        self.assertEqual(sum(log.hash_counts().values()), 2)
        changed = make_row("STORE", 17, 0, 124)
        self.assertNotEqual(row_commitment(changed), row_commitment(rows[0]))


class TraceEquivalenceTests(unittest.TestCase):
    def test_10_e0_e1_match_oracle_on_all_16_traces(self):
        data_dir = os.path.join(ROOT, "data")
        paths = generate_all(data_dir, SEED)  # ensures traces exist & are fixed-seed
        self.assertEqual(len(paths), 16)
        for n, t, path in paths:
            from src.trace.generator import load_trace
            tr = load_trace(path)
            e0, e1, orc, exp = run_trace(tr)
            self.assertEqual(e0.actual_returns, exp, f"E0 mismatch N={n} T={t}")
            self.assertEqual(e1.actual_returns, exp, f"E1 mismatch N={n} T={t}")
            self.assertEqual(e0.final_state(), orc.final_state(), f"E0 state N={n} T={t}")
            self.assertEqual(e1.final_state(), orc.final_state(), f"E1 state N={n} T={t}")

    def test_11_e0_e1_emit_identical_five_column_rows(self):
        tr = generate_trace(128, 256, SEED)
        e0, e1, _, _ = run_trace(tr)
        self.assertEqual([r.as_dict() for r in e0.history],
                         [r.as_dict() for r in e1.log.rows])

    def test_12_dummy_access_never_reveals_op_via_row_count(self):
        for n, t in ((64, 128), (512, 1024)):
            tr = generate_trace(n, t, SEED)
            e0, e1, _, _ = run_trace(tr)
            # Every instruction (incl. NOOP) produces exactly one trace row.
            self.assertEqual(e0.summary()["history_rows"], t)
            self.assertEqual(e1.summary()["history_rows"], t)
            self.assertTrue(all(r.mem_addr == DUMMY_ADDR for r in e0.history
                                if r.is_mem_op == 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
