#!/usr/bin/env python3
"""EXP-DORAM-08 tests: validate the SYMBOLIC model definitions and counter semantics.

No MPC timing, no upstream imports, no R1CS claims.
"""

from __future__ import annotations

import unittest

from src.exp_doram_08.costs import (
    CostParams,
    cross_threshold_n,
    e0_step,
    e0_total,
    e0_total_by_sum,
    e1_step,
    e1_total,
    e1_total_by_sum,
    fetch_linear_adds,
    fetch_mults,
    lowbit_mults,
    online_field_elems,
    preproc_field_elems,
    rounds_from_mults,
)
from src.exp_doram_08.counters import e0_fetch_counters, e1_fetch_counters
from src.exp_doram_08.sensitivity import store_steps

P = CostParams()


class PrimitiveDecompositionTests(unittest.TestCase):
    def test_inversion_multiplication_count(self):
        # p-2: bit_length=253, popcount=133 -> 386 BeaverMulti (MpcExecutor L365-370)
        self.assertEqual(133 + 253, 386)
        self.assertEqual(P.c_eq, 1 + 386 + 1 + 1)

    def test_lowbit_formula(self):
        for k in (1, 2, 3, 16, 1024):
            self.assertEqual(lowbit_mults(k, P), 3 * k - 2)

    def test_fetch_row_count_is_393k_minus_2(self):
        for k in (1, 2, 3, 64, 1024):
            self.assertEqual(fetch_mults(k, P), 393 * k - 2)
            # independent decomposition: 389 eq + (3k-2) lowbit + k select
            self.assertEqual(fetch_mults(k, P), 389 * k + (3 * k - 2) + k)

    def test_fetch_linear_adds(self):
        # 2k (FieldEquals: FieldSub + BoolNot) + k (LowBit NOT) + (k-1) (select sums) = 4k-1
        for k in (1, 2, 7):
            self.assertEqual(fetch_linear_adds(k, P), 4 * k - 1)

    def test_zero_rows_no_fetch(self):
        self.assertEqual(fetch_mults(0, P), 0)
        self.assertEqual(lowbit_mults(0, P), 0)

    def test_K_coefficient(self):
        self.assertEqual(P.K, 393)


class E0StepTests(unittest.TestCase):
    def test_e0_step_scans_exactly_step_rows(self):
        # step s sees s visible history rows; step 0 -> zero Fetch
        for s in range(0, 8):
            self.assertEqual(e0_step(s, P), fetch_mults(s, P))

    def test_e0_step_zero_and_one(self):
        self.assertEqual(e0_step(0, P), 0)
        self.assertEqual(e0_step(1, P), 391)

    def test_e0_history_row_count_matches_r1(self):
        # abstract scan count T(T-1)/2 is preserved; cost uses 393 per row
        for T in (4, 16, 64):
            self.assertEqual(sum(range(T)), T * (T - 1) // 2)


class E1StepTests(unittest.TestCase):
    def test_e1_fetch_scans_n_slots(self):
        for n in (1, 2, 16, 1024):
            self.assertEqual(e1_step(1, n, False, P), fetch_mults(n, P))
            self.assertEqual(e1_step(1, n, False, P), 393 * n - 2)

    def test_e1_store_adds_n_updates_shared_eq(self):
        for n in (1, 3, 64):
            base = e1_step(1, n, False, P)
            store = e1_step(1, n, True, P, share_eq=True)
            self.assertEqual(store - base, n)

    def test_e1_store_adds_390n_updates_separate_eq(self):
        for n in (1, 3, 64):
            base = e1_step(1, n, False, P)
            store = e1_step(1, n, True, P, share_eq=False)
            self.assertEqual(store - base, 390 * n)

    def test_e1_step_zero_store_uses_separate_eq(self):
        # step 0 has no read scan; a STORE there cannot reuse eq bits
        self.assertEqual(e1_step(0, 5, False, P), 0)
        self.assertEqual(e1_step(0, 5, True, P, share_eq=True), 5)
        self.assertEqual(e1_step(0, 5, True, P, share_eq=False), 5 * 390)


class ClosedFormTests(unittest.TestCase):
    def test_e0_closed_form_equals_step_sum(self):
        for T in (0, 1, 2, 5, 17, 64):
            self.assertEqual(e0_total(T, P), e0_total_by_sum(T, P))

    def test_e0_hand_computation(self):
        # T=4: 391 + 784 + 1177 = 2352; closed form 393*6 - 2*3
        self.assertEqual(e0_total(4, P), 2352)
        self.assertEqual(sum(fetch_mults(s, P) for s in (1, 2, 3)), 391 + 784 + 1177)

    def test_e1_closed_form_equals_step_sum(self):
        for T, n, stores in ((5, 2, {1, 3}), (8, 4, set()), (1, 1, {0})):
            W = len(stores)
            self.assertEqual(e1_total(T, n, W, P, share_eq=True), e1_total_by_sum(T, n, stores, P, True))
            self.assertEqual(e1_total(T, n, W, P, share_eq=False), e1_total_by_sum(T, n, stores, P, False))

    def test_e1_hand_computation(self):
        # T=5, n=2, W=1(shared): 4*784 + 2 = 3138
        self.assertEqual(e1_total(5, 2, 1, P, share_eq=True), 3138)
        self.assertEqual(e1_total(5, 2, 1, P, share_eq=False), 4 * 784 + 780)

    def test_append_cost_identical_for_both_models(self):
        # Both models append exactly T rows; Fetch circuit processes none of them.
        self.assertEqual(P.append_mults, 0)
        for T in (0, 1, 10):
            self.assertEqual(sum(P.append_mults for _ in range(T)), sum(P.append_mults for _ in range(T)))
            e0_app = sum(e0_step(s, P) - fetch_mults(s, P) for s in range(T))
            e1_app = sum(e1_step(s, 4, False, P) - (fetch_mults(4, P) if s > 0 else 0) for s in range(T))
            self.assertEqual(e0_app, e1_app)

    def test_rounds_and_preprocessing_not_confused_with_mults(self):
        m = 391
        self.assertEqual(rounds_from_mults(m, P), m)  # current serial executor only
        self.assertEqual(preproc_field_elems(m, P), 3 * m)
        self.assertEqual(online_field_elems(m, P), 2 * m)
        self.assertNotEqual(rounds_from_mults(m, P), preproc_field_elems(m, P))


class CounterSemanticsTests(unittest.TestCase):
    def test_example1_latest_hit_still_multiplies_all_rows(self):
        c = e0_fetch_counters(3, True)
        self.assertEqual(c.logical_selection_results, 1)
        self.assertEqual(c.select_compose_rows, 3)
        self.assertEqual(c.select_compose_field_mul, 3)

    def test_example2_no_match_still_multiplies_all_rows(self):
        c = e0_fetch_counters(3, False)
        self.assertEqual(c.logical_selection_results, 0)
        self.assertEqual(c.select_compose_rows, 3)
        self.assertEqual(c.select_compose_field_mul, 3)

    def test_example3_all_different_addresses(self):
        c = e0_fetch_counters(4, False)
        self.assertEqual(c.logical_selection_results, 0)
        self.assertEqual(c.select_compose_field_mul, 4)

    def test_e1_read_and_write_select_separate(self):
        read = e1_fetch_counters(4, True, False)
        self.assertEqual(read.select_compose_field_mul, 4)
        self.assertEqual(read.e1_read_select_rows, 4)
        self.assertEqual(read.e1_write_select_rows, 0)
        store = e1_fetch_counters(4, True, True)
        self.assertEqual(store.select_compose_field_mul, 8)
        self.assertEqual(store.e1_write_select_rows, 4)

    def test_select_field_mul_equals_rows_not_logical_result(self):
        for rows in (1, 5, 100):
            c = e0_fetch_counters(rows, False)
            self.assertEqual(c.select_compose_field_mul, c.select_compose_rows)
            self.assertNotEqual(c.select_compose_field_mul, c.logical_selection_results)


class CrossConditionTests(unittest.TestCase):
    def test_read_only_threshold_is_T_over_2(self):
        for T in (16, 64, 1024):
            self.assertAlmostEqual(cross_threshold_n(T, 0, P, True), T / 2, places=9)

    def test_threshold_predicts_sign_read_only(self):
        for T in (16, 64):
            thr = cross_threshold_n(T, 0, P, True)
            self.assertLess(e1_total(T, int(thr) - 1, 0, P), e0_total(T, P))
            self.assertGreater(e1_total(T, int(thr) + 1, 0, P), e0_total(T, P))

    def test_all_store_separate_eq_threshold_near_T_over_4(self):
        T = 1024
        thr = cross_threshold_n(T, T - 1, P, False)
        self.assertTrue(T / 4.1 < thr < T / 3.9, thr)

    def test_high_store_ratio_degrades_threshold(self):
        T = 1024
        self.assertLess(cross_threshold_n(T, T - 1, P, False), cross_threshold_n(T, 0, P, True))

    def test_scaled_parameters_change_threshold(self):
        T, W = 256, 0
        p_high = P.scaled(1000, 1)
        p_low = P.scaled(1, 1)
        # read-only threshold is n < T/2 (i.e. T/n > 2); c_eq ratio cancels in K
        self.assertAlmostEqual(cross_threshold_n(T, 0, p_low, True), T / 2, places=6)
        self.assertAlmostEqual(cross_threshold_n(T, 0, p_high, True), T / 2, places=6)
        # with writes, relative update weight matters
        self.assertGreater(cross_threshold_n(T, 128, p_high, True), cross_threshold_n(T, 128, p_low, True))

    def test_k_scales_with_eq_ratio(self):
        self.assertEqual(P.scaled(1, 1).K, 5)
        self.assertEqual(P.scaled(100, 1).K, 104)


class ExtremeAndBoundaryTests(unittest.TestCase):
    def test_zero_steps(self):
        self.assertEqual(e0_total(0, P), 0)
        self.assertEqual(e1_total(0, 5, 0, P), 0)

    def test_single_step(self):
        # no Fetch at step 0; only a STORE may trigger E1 update
        self.assertEqual(e0_total(1, P), 0)
        self.assertEqual(e1_total(1, 5, 0, P), 0)
        self.assertEqual(e1_total(1, 5, 1, P, share_eq=True), 5)

    def test_n_equals_1(self):
        self.assertEqual(fetch_mults(1, P), 391)
        self.assertEqual(e1_total(4, 1, 0, P), 3 * 391)
        self.assertLess(e1_total(4, 1, 0, P), e0_total(4, P))

    def test_zero_store_and_full_store(self):
        T, n = 64, 16
        self.assertEqual(store_steps(T, 0.0), set())
        self.assertEqual(len(store_steps(T, 1.0)), T - 1)
        self.assertEqual(len(store_steps(T, 0.5)), int(round(0.5 * (T - 1))))
        self.assertLess(e1_total(T, n, 0, P), e0_total(T, P))
        self.assertLess(e1_total(T, n, T - 1, P, share_eq=True), e0_total(T, P))

    def test_n_near_T_e1_is_worse(self):
        T = 64
        self.assertGreater(e1_total(T, T, 0, P), e0_total(T, P))
        # n = T/2 is exactly the read-only crossover (equal); beyond it E1 is worse
        self.assertEqual(e1_total(T, T // 2, 0, P), e0_total(T, P))
        self.assertGreater(e1_total(T, T // 2 + 1, 0, P), e0_total(T, P))

    def test_dummy_fetch_is_not_free(self):
        # STORE/NOOP Fetch has identical scan cost to LOAD Fetch
        self.assertEqual(e1_step(3, 16, False, P), e1_step(3, 16, True, P) - 16)
        self.assertEqual(e0_step(3, P), e0_step(3, P))


if __name__ == "__main__":
    unittest.main()
