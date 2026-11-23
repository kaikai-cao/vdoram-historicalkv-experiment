#!/usr/bin/env python3
"""EXP-DORAM-08-R1 tests: verify model definitions and boundary semantics,
not merely that functions run.
"""

import unittest

from src.exp_doram_08_r1.costs import (
    CostParams,
    e0_step, e0_total_by_sum, e0_total_closed,
    e1a_step, e1b_step,
    e1a_total_by_sum, e1b_total_by_sum,
    e1a_total_closed, e1b_total_closed,
    cross_threshold_n,
    e0_linear, e1a_linear, e1b_linear,
    rounds_from_mults, preproc_field_elems, online_field_elems,
)
from src.exp_doram_08_r1.counters import (
    eq_vector, select_compose, lowbit_onehot,
    e1_a_read, e1_b_read, select_compose_field_mul_count,
)

P = CostParams()


class TestE0(unittest.TestCase):
    def test_e0_per_step_scan_rows(self):
        for s in range(1, 10):
            self.assertEqual(e0_step(s, P), 393 * s - 2)
        self.assertEqual(e0_step(0, P), 0)  # step0 no fetch

    def test_e0_closed_equals_sum(self):
        for T in range(0, 12):
            self.assertEqual(e0_total_closed(T, P), e0_total_by_sum(T, P))

    def test_e0_closed_formula(self):
        T = 30
        self.assertEqual(e0_total_closed(T, P), 393 * T * (T - 1) // 2 - 2 * (T - 1))


class TestE1Fetch(unittest.TestCase):
    def test_e1a_scan_n_slots_with_lowbit(self):
        for n in (1, 2, 7, 16):
            # step>0, no store: E1-A fetch = 393n-2
            self.assertEqual(e1a_step(1, n, False, P), 393 * n - 2)
            self.assertEqual(e1a_step(5, n, False, P), 393 * n - 2)

    def test_e1b_no_lowbit(self):
        for n in (1, 2, 7, 16):
            self.assertEqual(e1b_step(1, n, False, P), 390 * n)
            # E1-A - E1-B = 3n-2 exactly the LowBit cost
            self.assertEqual(e1a_step(1, n, False, P) - e1b_step(1, n, False, P),
                             3 * n - 2)

    def test_e1_step0_no_fetch(self):
        self.assertEqual(e1a_step(0, 16, False, P), 0)
        self.assertEqual(e1b_step(0, 16, False, P), 0)


class TestReadSemantics(unittest.TestCase):
    def test_e1b_in_domain_unique_hit(self):
        n = 8
        values = [10 * j + 5 for j in range(n)]
        for k in range(n):
            eq = eq_vector(k, n)
            self.assertEqual(sum(eq), 1)  # exactly one hit
            self.assertEqual(e1_b_read(k, n, values), values[k])

    def test_e1b_out_of_domain_returns_zero(self):
        n = 8
        values = [10 * j + 5 for j in range(n)]
        self.assertEqual(e1_b_read(999, n, values, in_domain=False), 0)
        self.assertEqual(e1_b_read(None, n, values), 0)
        # NegOne / out-of-range with in_domain=False: all eq zero
        self.assertEqual(sum(eq_vector(999, n, in_domain=False)), 0)

    def test_e1a_e1b_same_on_unique_domain(self):
        n = 8
        values = [3 * j + 1 for j in range(n)]
        for k in range(n):
            self.assertEqual(e1_a_read(k, n, values), e1_b_read(k, n, values))

    def test_lowbit_selects_last_raw_one(self):
        raw = [0, 1, 0, 1, 0]
        self.assertEqual(lowbit_onehot(raw), [0, 0, 0, 1, 0])

    def test_select_compose_counts_all_rows(self):
        # Even all-zero selectors do n FieldMul (no early exit in gadget).
        self.assertEqual(select_compose_field_mul_count(5), 5)
        self.assertEqual(select_compose([0, 0, 0], [7, 8, 9]), 0)


class TestStoreUpdate(unittest.TestCase):
    def test_shared_vs_separate_cost(self):
        n = 10
        # step>0 shared: n*2 ; separate: n*(c_eq+2)
        self.assertEqual(e1b_step(3, n, True, P, share_eq=True), 390 * n + 2 * n)
        self.assertEqual(e1b_step(3, n, True, P, share_eq=False),
                         390 * n + (P.c_eq + 2) * n)
        self.assertEqual(P.c_upd_separate, 391)

    def test_step0_store_forced_separate(self):
        n = 10
        # step0 STORE: no fetch, forced separate even if share_eq=True
        self.assertEqual(e1a_step(0, n, True, P, share_eq=True), n * (P.c_eq + 2))
        self.assertEqual(e1b_step(0, n, True, P, share_eq=True), n * (P.c_eq + 2))
        # same cost regardless of share_eq flag at step0
        self.assertEqual(e1a_step(0, n, True, P, share_eq=True),
                         e1a_step(0, n, True, P, share_eq=False))

    def test_step_positive_shared_only_when_allowed(self):
        n = 10
        s = e1b_step(2, n, True, P, share_eq=True)
        sep = e1b_step(2, n, True, P, share_eq=False)
        self.assertLess(s, sep)

    def test_store_zero_percent(self):
        self.assertEqual(e1b_total_by_sum(20, 16, set(), P), 19 * 390 * 16)

    def test_store_hundred_percent(self):
        T, n = 20, 16
        steps = set(range(T))
        # step0 separate, 19 shared
        expected = 19 * 390 * n + n * (P.c_eq + 2) + 19 * n * 2
        self.assertEqual(e1b_total_by_sum(T, n, steps, P, share_eq=True), expected)


class TestTotalsAndClosedForms(unittest.TestCase):
    def test_e1_totals_sum_equals_closed(self):
        for T in (1, 2, 5, 17):
            for n in (1, 4, 16):
                for steps in (set(), {0}, {1}, {0, 2, 4}):
                    for mode in (True, False):
                        self.assertEqual(
                            e1a_total_by_sum(T, n, steps, P, mode),
                            e1a_total_closed(T, n, steps, P, mode))
                        self.assertEqual(
                            e1b_total_by_sum(T, n, steps, P, mode),
                            e1b_total_closed(T, n, steps, P, mode))

    def test_E1A_minus_E1B_fetch_only(self):
        T, n, steps = 32, 12, {0, 5, 9}
        self.assertEqual(e1a_total_closed(T, n, steps, P) - e1b_total_closed(T, n, steps, P),
                         (T - 1) * (3 * n - 2))

    def test_three_models_common_append(self):
        # R1-C1: history append fires at EVERY step (incl. step 0), verified from
        # ZkProgramExecutor.cs L116 (loop from 0) + L405 (AddMemoryTrace each step).
        # All three models must gain exactly T*append_mults, and stepwise == closed.
        p2 = CostParams(append_mults=7)
        T = 10
        self.assertEqual(e0_total_closed(T, p2) - e0_total_closed(T, P), T * 7)
        for steps in (set(), {0}, {1}, {0, 3, 7}):
            self.assertEqual(e0_total_by_sum(T, p2), e0_total_closed(T, p2))
            for fn_sum, fn_cls in ((e1a_total_by_sum, e1a_total_closed),
                                   (e1b_total_by_sum, e1b_total_closed)):
                self.assertEqual(fn_sum(T, 8, steps, p2), fn_cls(T, 8, steps, p2))
                self.assertEqual(fn_cls(T, 8, steps, p2) - fn_cls(T, 8, steps, P),
                                 T * 7)

    def test_append_step0_store_not_omitted(self):
        # A STORE at step 0 must still carry its history-append cost.
        p2 = CostParams(append_mults=7)
        T, n = 6, 5
        for variant, fn_sum, fn_cls in (("A", e1a_total_by_sum, e1a_total_closed),
                                        ("B", e1b_total_by_sum, e1b_total_closed)):
            self.assertEqual(fn_sum(T, n, {0}, p2), fn_cls(T, n, {0}, p2))
            self.assertEqual(fn_cls(T, n, {0}, p2) - fn_cls(T, n, {0}, P), T * 7)
            self.assertEqual(fn_cls(1, n, {0}, p2) - fn_cls(1, n, {0}, P), 7)


class TestAppendBoundary(unittest.TestCase):
    """R1-C1: stepwise/closed consistency at T=0,1,2 and append on/off."""

    def test_append_T0_T1_T2(self):
        for am in (0, 7):
            p = CostParams(append_mults=am)
            for T in (0, 1, 2):
                self.assertEqual(e0_total_by_sum(T, p), e0_total_closed(T, p))
                for n in (1, 4, 16):
                    for steps in (set(), {0}, {0, 1}):
                        self.assertEqual(e1a_total_by_sum(T, n, steps, p),
                                         e1a_total_closed(T, n, steps, p))
                        self.assertEqual(e1b_total_by_sum(T, n, steps, p),
                                         e1b_total_closed(T, n, steps, p))
            self.assertEqual(e0_total_closed(1, p), am)  # no fetch at step 0, one append
            # step1 fetch_e0(1) = 393*1-2 = 391, plus 2 appends
            self.assertEqual(e0_total_closed(2, p), 391 + 2 * am)


class TestCrossThreshold(unittest.TestCase):
    def test_read_only_threshold_exact(self):
        # R1-C1: exact symbolic crossovers, not a delta=1.0 approximation.
        for T in (2, 32, 64, 128, 1024, 4096):
            thrA = cross_threshold_n(T, set(), "A", P)
            thrB = cross_threshold_n(T, set(), "B", P)
            self.assertAlmostEqual(thrA, T / 2, places=9)
            self.assertAlmostEqual(thrB, (393 * T - 4) / 780, places=9)
            self.assertGreater(thrB, thrA)  # E1-B has no -2 fetch constant

    def test_cross_threshold_predicts_readonly_winner(self):
        # Cross conditions must agree with the actual closed-form sums.
        T = 64
        e0 = e0_total_closed(T, P)
        for n in (8, 16, 31, 32, 33, 48, 64):
            self.assertEqual(e1a_total_closed(T, n, set(), P) < e0,
                             n < T / 2, f"E1-A n={n}")
            self.assertEqual(e1b_total_closed(T, n, set(), P) < e0,
                             n < (393 * T - 4) / 780, f"E1-B n={n}")

    def test_mixed_rw_threshold_matches_parameterised_formula(self):
        T = 128
        K, b = 393, 2
        a0 = K * T * (T - 1) // 2 - b * (T - 1)
        steps = set(range(T))  # step0 + (T-1) positive STOREs
        U_shared = P.c_upd_separate + (T - 1) * P.c_upd_shared
        U_sep = T * P.c_upd_separate
        exp_sh = (a0 + b * (T - 1)) / (K * (T - 1) + U_shared)
        exp_se = (a0 + b * (T - 1)) / (K * (T - 1) + U_sep)
        self.assertAlmostEqual(cross_threshold_n(T, steps, "A", P, True), exp_sh, places=9)
        self.assertAlmostEqual(cross_threshold_n(T, steps, "A", P, False), exp_se, places=9)
        self.assertLess(exp_se, exp_sh)  # expensive updates shrink E1 advantage
        # read-only is the most permissive case
        self.assertGreater(cross_threshold_n(T, set(), "A", P), exp_sh)

    def test_writes_lower_threshold(self):
        T = 128
        steps = set(range(T))
        thr_shared = cross_threshold_n(T, steps, "B", P, share_eq=True)
        thr_sep = cross_threshold_n(T, steps, "B", P, share_eq=False)
        self.assertGreater(thr_shared, thr_sep)  # expensive updates shrink advantage

    def test_step0_store_lowers_threshold(self):
        T = 128
        thr_no = cross_threshold_n(T, set(), "B", P)
        thr_s0 = cross_threshold_n(T, {0}, "B", P)
        self.assertGreater(thr_no, thr_s0)

    def test_T_le_1(self):
        self.assertEqual(cross_threshold_n(1, set(), "B", P), 0.0)
        self.assertEqual(cross_threshold_n(0, set(), "B", P), 0.0)


class TestBoundary(unittest.TestCase):
    def test_T0_T1(self):
        self.assertEqual(e0_total_closed(0, P), 0)
        self.assertEqual(e0_total_closed(1, P), 0)
        self.assertEqual(e1a_total_closed(1, 8, {0}, P), 8 * (P.c_eq + 2))
        self.assertEqual(e1b_total_closed(1, 8, set(), P), 0)

    def test_n1(self):
        self.assertEqual(e1b_step(1, 1, False, P), 390)
        self.assertEqual(e1a_step(1, 1, False, P), 391)  # 393*1-2

    def test_n_half_T_boundary(self):
        # T=32,n=16: E1-B read-only should be near-losing at approx n=T/2
        T, n = 32, 16
        e0 = e0_total_closed(T, P)
        e1 = e1b_total_closed(T, n, set(), P)
        self.assertGreater(e1, 0.9 * e0)  # close to cross, not a blowout

    def test_illegal_n(self):
        self.assertEqual(e1a_step(1, 0, False, P), 0)
        self.assertEqual(e1b_step(1, 0, False, P), 0)


class TestLinearRoundsPreproc(unittest.TestCase):
    def test_linear_formulas(self):
        T, n = 9, 5
        self.assertEqual(e0_linear(T, P), (T - 1) * (2 * T - 1))
        self.assertEqual(e1a_linear(T, n, set(), P), (T - 1) * (4 * n - 1))
        self.assertEqual(e1b_linear(T, n, set(), P), (T - 1) * (3 * n - 1))

    def test_update_linear_manual(self):
        n = 5
        T, steps = 4, {0, 2}
        self.assertEqual(e1b_linear(T, n, steps, P), 3 * (3 * n - 1) + 2 * n * 2)

    def test_rounds_preproc_online(self):
        m = 100
        self.assertEqual(rounds_from_mults(m, P), 100)
        self.assertEqual(preproc_field_elems(m, P), 300)
        self.assertEqual(online_field_elems(m, P), 200)


if __name__ == "__main__":
    unittest.main()
