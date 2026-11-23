#!/usr/bin/env python3
"""EXP-DORAM-01-R1: Fetch workload-consistency tests.

Six R1 tests per the correction task, in addition to the original 12 in
test_correctness.py (which are kept unchanged and must keep passing):

  R1-1  E0 and E1 perform the SAME number of Fetch operations at every
        non-initial step (and both use zeroShare at step 0).
  R1-2  A STORE step also executes Fetch (it is not skipped).
  R1-3  A NOOP step also executes Fetch (it is not skipped).
  R1-4  A NOOP whose Fetch input address != the NegOne trace sentinel still
        executes correctly (the two address concepts are separated).
  R1-5  E0 and E1 produce identical Fetch results for the same fetch_address
        sequence, on every non-initial step.
  R1-6  Deleting one historical row while keeping the original execution-time
        commitment makes the Prove-stage hash-count check FAIL.

All conclusions here concern the two *reference models*; E1 is a plain dict,
NOT an ORAM, and no security claim is made.
"""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.trace.generator_r1 import (  # noqa: E402
    DUMMY_ADDR, N_VALUES, T_VALUES, SEED, generate_trace_r1, generate_all_r1,
    load_r1_trace, r1_trace_path,
)
from src.baseline.e0_linear_scan import (  # noqa: E402
    E0LinearScan, TraceRow, make_row,
)
from src.dual_store.e1_dual_store import (  # noqa: E402
    E1DualStore, HistoricalLog, row_commitment,
)
from src.oracle import Oracle  # noqa: E402


def _mini(recs):
    """Build an R1-format mini trace: (op, fetch_address, trace_address, value)."""
    out = []
    for i, (op, fa, ta, v) in enumerate(recs):
        out.append({"step": i, "op": op, "fetch_address": fa,
                    "trace_address": ta, "value": v, "pattern": "unit"})
    return out


def _run(trace):
    e0, e1 = E0LinearScan(), E1DualStore()
    s0, s1 = e0.run(trace), e1.run(trace)
    return e0, e1, s0, s1


class FetchWorkloadConsistencyTests(unittest.TestCase):

    def test_r1_01_fetch_count_identical_all_noninitial_steps(self):
        """R1-1: both models Fetch exactly T-1 times; step 0 is zeroShare."""
        for n, t in ((64, 128), (256, 512), (512, 1024)):
            tr = generate_trace_r1(n, t, SEED)
            e0, e1, s0, s1 = _run(tr)
            self.assertEqual(s0["queries"], t - 1, f"E0 count N={n} T={t}")
            self.assertEqual(s1["queries"], t - 1, f"E1 count N={n} T={t}")
            self.assertEqual(s0["queries"], s1["queries"])
            # Exact input-address sequence must be byte-for-byte identical.
            self.assertEqual(s0["fetch_addresses"], s1["fetch_addresses"],
                             f"fetch address sequence N={n} T={t}")

    def test_r1_02_store_step_executes_fetch(self):
        """R1-2: a STORE still incurs one Fetch; value is not consumed."""
        # step0 STORE (zeroShare, no fetch); step1 STORE must fetch reg0=17.
        tr = _mini([
            ("STORE", 17, 17, 100),
            ("STORE", 17, 17, 200),
        ])
        e0, e1, s0, s1 = _run(tr)
        self.assertEqual(s0["queries"], 1)   # only step 1 fetches
        self.assertEqual(s1["queries"], 1)
        self.assertEqual(s0["fetch_addresses"], [17])
        self.assertEqual(s1["fetch_addresses"], [17])
        # STORE return value is the written value, not the fetched one.
        self.assertEqual(e0.actual_returns, [100, 200])
        self.assertEqual(e1.actual_returns, [100, 200])

    def test_r1_03_noop_step_executes_fetch(self):
        """R1-3: a NOOP at a non-initial step still incurs one Fetch."""
        tr = _mini([
            ("NOOP", 5, DUMMY_ADDR, None),
            ("NOOP", 9, DUMMY_ADDR, None),
            ("NOOP", 9, DUMMY_ADDR, None),
        ])
        e0, e1, s0, s1 = _run(tr)
        self.assertEqual(s0["queries"], 2)   # step 0 skipped; steps 1,2 fetch
        self.assertEqual(s1["queries"], 2)
        self.assertEqual(s0["fetch_addresses"], [9, 9])
        self.assertEqual(s1["fetch_addresses"], [9, 9])
        self.assertEqual(e0.actual_returns, [0, 0, 0])
        self.assertEqual(e1.actual_returns, [0, 0, 0])

    def test_r1_04_noop_fetch_input_differs_from_trace_sentinel(self):
        """R1-4: NOOP fetch_address (ordinary) != trace_address (NegOne)."""
        tr = _mini([
            ("STORE", 7, 7, 55),
            ("NOOP", 7, DUMMY_ADDR, None),   # fetch reg0=7, trace addr=NegOne
        ])
        fa, ta = tr[1]["fetch_address"], tr[1]["trace_address"]
        self.assertNotEqual(fa, DUMMY_ADDR)
        self.assertEqual(ta, DUMMY_ADDR)
        e0, e1, s0, s1 = _run(tr)
        # Fetch input for the NOOP step is the ordinary address 7 in both.
        self.assertEqual(s0["fetch_addresses"], [7])
        self.assertEqual(s1["fetch_addresses"], [7])
        # Historical row for NOOP is keyed by NegOne and is not a memory op.
        self.assertEqual(e0.history[1].mem_addr, DUMMY_ADDR)
        self.assertEqual(e1.log.rows[1].mem_addr, DUMMY_ADDR)
        self.assertEqual(e0.history[1].is_mem_op, 0)
        # State unchanged by the NOOP even though Fetch read address 7.
        self.assertEqual(e0.final_state(), {7: 55})
        self.assertEqual(e1.final_state(), {7: 55})

    def test_r1_05_identical_fetch_results_per_address(self):
        """R1-5: for the same fetch_address sequence E0/E1 return same values
        at every non-initial step (using dedicated per-step step functions)."""
        tr = generate_trace_r1(128, 512, SEED)
        e0, e1, s0, s1 = _run(tr)
        self.assertEqual(s0["fetch_addresses"], s1["fetch_addresses"])
        # Re-run step-by-step, comparing the raw value each Fetch returns.
        e0s, e1s = E0LinearScan(), E1DualStore()
        fa_list = []
        for rec in tr:
            fa = rec["fetch_address"]
            ta = rec["trace_address"]
            if rec["step"] == 0:
                continue
            v0, _ = e0s.fetch(fa)
            v1 = e1s.current.read(fa)
            fa_list.append(fa)
            self.assertEqual(v0, v1, f"fetch result mismatch at step {rec['step']}")
        self.assertEqual(len(fa_list), len(tr) - 1)

    def test_r1_06_deleted_row_with_stale_commitment_fails_hash_count(self):
        """R1-6: deleting a historical row but KEEPING the original
        execution-time commitments makes the Prove-stage hash-count check fail.

        This is the gap in the original test_06 (which deleted both the row and
        its commitment). Real VDORAM accumulates row hashes during execution;
        Prove re-hashes the (sorted) rows and compares the multisets. A missing
        row with the old commitment still present must be detected.
        """
        tr = [
            {"step": 0, "op": "STORE", "fetch_address": 17, "trace_address": 17,
             "value": 123, "pattern": "u"},
            {"step": 1, "op": "STORE", "fetch_address": 18, "trace_address": 18,
             "value": 5, "pattern": "u"},
            {"step": 2, "op": "STORE", "fetch_address": 17, "trace_address": 17,
             "value": 456, "pattern": "u"},
        ]
        e1 = E1DualStore()
        e1.run(tr)
        # Healthy log: Prove-stage recomputation matches execution-time hashes.
        self.assertTrue(e1.log.check_hash_consistency()[0])
        self.assertEqual(e1.log.recomputed_hash_counts(), e1.log.hash_counts())

        # Delete ONE historical row but DO NOT touch the commitments list -- this
        # models Prove receiving a truncated trace while the committed hashes
        # from execution time remain intact.
        del e1.log.rows[1]
        ok, reason = e1.log.check_hash_consistency()
        self.assertFalse(ok)
        self.assertIn("hash", reason)
        # Sanity: replay also diverges (the deleted Store changes final state).
        self.assertNotEqual(e1.log.replay().get(18), 5)

    def test_r1_07_all16_r1_traces_consistent(self):
        """Cross-check: all 16 R1 traces keep E0/E1/oracle consistent."""
        data_dir = os.path.join(ROOT, "data")
        made = generate_all_r1(data_dir, SEED)
        self.assertEqual(len(made), 16)
        for n, t, path in made:
            tr = load_r1_trace(path)
            e0, e1, orc = E0LinearScan(), E1DualStore(), Oracle()
            s0, s1 = e0.run(tr), e1.run(tr)
            exp = orc.run(tr)
            self.assertEqual(e0.actual_returns, exp, f"E0 returns N={n} T={t}")
            self.assertEqual(e1.actual_returns, exp, f"E1 returns N={n} T={t}")
            self.assertEqual(s0["queries"], s1["queries"], f"count N={n} T={t}")
            self.assertEqual(s0["fetch_addresses"], s1["fetch_addresses"],
                             f"seq N={n} T={t}")
            self.assertEqual(e0.final_state(), e1.final_state(),
                             f"state N={n} T={t}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
