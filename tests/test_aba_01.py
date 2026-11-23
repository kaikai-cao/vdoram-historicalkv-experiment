#!/usr/bin/env python3
"""ABA-01 tests: positive, negative, boundary and certificate-invalidation cases.

These verify the static certificate prototype only. They are not MPC/R1CS
performance or execution-binding tests.
"""

import copy
import unittest

from src.aba_01.analyzer import ANALYZER_VERSION, InputConstraint, analyze
from src.aba_01.cfg import BUBBLE_SORT, FIELD_PRIME, Instr
from src.aba_01.certificate import (
    CERT_SCHEMA, SCOPE, build_certificate, certificate_example,
    verify_certificate,
)

P = BUBBLE_SORT
C = InputConstraint(1, 16)
MEM_PCS = (4, 16, 18, 22, 24, 36)


class TestProgramBinding(unittest.TestCase):
    def test_program_hash_is_stable_and_binds_instructions(self):
        self.assertEqual(P.digest(), BUBBLE_SORT.digest())
        self.assertTrue(P.digest().startswith("sha256:"))
        mutated = P.with_instr(16, Instr("Load", 7))
        self.assertNotEqual(P.digest(), mutated.digest())

    def test_memory_pcs_match_source_semantics(self):
        self.assertEqual(P.memory_pcs(), MEM_PCS)
        self.assertEqual([P.instrs[pc].op for pc in MEM_PCS],
                         ["Store", "Load", "Load", "Store", "Store", "Load"])

    def test_cfg_backedges(self):
        edges = [(pc, s) for pc in range(len(P.instrs))
                 for s in P.successors(pc) if s <= pc]
        self.assertEqual(set(edges), {(8, 3), (28, 12), (34, 10), (41, 36)})


class TestPositiveCertificate(unittest.TestCase):
    def test_analysis_passes_all_accesses(self):
        a = analyze(P, C)
        self.assertEqual(a.status, "PASS")
        self.assertEqual(a.reasons, [])
        self.assertEqual(tuple(x.pc for x in a.accesses), MEM_PCS)
        for x in a.accesses:
            self.assertEqual(x.status, "PASS")
            self.assertEqual(x.interval, "[0, n-1]")
            self.assertTrue(x.dependencies)

    def test_certificate_structure_and_independent_check(self):
        cert = build_certificate(P, C)
        self.assertEqual(cert["schema"], CERT_SCHEMA)
        self.assertEqual(cert["scope"], SCOPE)
        self.assertEqual(cert["status"], "PASS")
        self.assertEqual(cert["program"]["program_hash"], P.digest())
        self.assertEqual(cert["program"]["instruction_count"], len(P.instrs))
        self.assertEqual(cert["nmax"], 16)
        self.assertEqual(cert["analyzer_version"], ANALYZER_VERSION)
        self.assertEqual(cert["field"]["prime_hex"], hex(FIELD_PRIME))
        self.assertTrue(verify_certificate(cert, P, require_pass=True).ok)
        self.assertIn(P.digest(), certificate_example(cert))

    def test_certificate_never_uses_sample_input_values(self):
        cert = build_certificate(P, C)
        text = repr(cert)
        for sample in ("114", "514", "1919", "810", "114514"):
            self.assertNotIn(sample, text)

    def test_checker_rejects_non_pass_when_pass_required(self):
        mutated = P.with_instr(21, Instr("Move", 0, 7))
        cert = build_certificate(mutated, C)
        self.assertEqual(cert["status"], "UNKNOWN")
        self.assertTrue(verify_certificate(cert, mutated).ok)  # structurally valid
        self.assertFalse(verify_certificate(cert, mutated, require_pass=True).ok)


class TestNegativeCases(unittest.TestCase):
    """Eight required negative cases; each must FAIL, UNKNOWN, or be rejected."""

    def test_01_n_greater_than_nmax(self):
        a = analyze(P, InputConstraint(17, 16))
        self.assertEqual(a.status, "FAIL")
        self.assertTrue(any("n_max < n_min" in r for r in a.reasons))
        cert = build_certificate(P, InputConstraint(17, 16))
        self.assertEqual(cert["status"], "FAIL")
        self.assertFalse(verify_certificate(cert, P, require_pass=True).ok)

    def test_02_store_address_from_unbounded_register(self):
        prog = P.with_instr(21, Instr("Move", 0, 7))
        a = analyze(prog, C)
        self.assertEqual(a.status, "UNKNOWN")
        bad = [x for x in a.accesses if x.pc == 22]
        self.assertEqual(bad[0].status, "UNKNOWN")
        self.assertIn("address", bad[0].reason)

    def test_03_load_address_from_unconstrained_expression(self):
        prog = P.with_instr(15, Instr("Move", 0, 5))
        a = analyze(prog, C)
        self.assertEqual(a.status, "UNKNOWN")
        self.assertEqual([x for x in a.accesses if x.pc == 16][0].status, "UNKNOWN")

    def test_04_loop_boundary_removed(self):
        prog = P.with_instr(14, Instr("Noop"))
        a = analyze(prog, C)
        self.assertEqual(a.status, "UNKNOWN")
        self.assertTrue(any("guard" in r for r in a.reasons))
        self.assertTrue(all(x.status == "UNKNOWN" for x in a.accesses))

    def test_05_wrapping_increment_replaces_add(self):
        prog = P.with_instr(5, Instr("Mul", 0, 0, 15))
        a = analyze(prog, C)
        self.assertEqual(a.status, "UNKNOWN")
        self.assertEqual([x for x in a.accesses if x.pc == 4][0].status, "UNKNOWN")

    def test_06_address_register_overwritten_on_branch(self):
        # Swap-branch instruction at PC23 is replaced by an R0 write from R7.
        prog = P.with_instr(23, Instr("Move", 0, 7))
        a = analyze(prog, C)
        self.assertEqual(a.status, "UNKNOWN")
        self.assertEqual([x for x in a.accesses if x.pc == 24][0].status, "UNKNOWN")

    def test_07_old_certificate_after_program_change(self):
        cert = build_certificate(P, C)
        changed = P.with_instr(16, Instr("Load", 7))
        res = verify_certificate(cert, changed)
        self.assertFalse(res.ok)
        self.assertTrue(any("program hash mismatch" in e for e in res.errors))

    def test_08_input_constraint_disagrees_with_nmax(self):
        cert = build_certificate(P, C)
        tampered = copy.deepcopy(cert)
        tampered["nmax"] = 32
        res = verify_certificate(tampered, P)
        self.assertFalse(res.ok)
        self.assertTrue(any("Nmax disagrees" in e for e in res.errors))


class TestBoundaryAndTamper(unittest.TestCase):
    def test_n_equals_one(self):
        a = analyze(P, InputConstraint(1, 1))
        self.assertEqual(a.status, "PASS")

    def test_n_zero_is_invalid_program_assumption(self):
        a = analyze(P, InputConstraint(0, 16))
        self.assertEqual(a.status, "FAIL")
        self.assertTrue(any("n=0" in r for r in a.reasons))

    def test_n_equals_nmax(self):
        a = analyze(P, InputConstraint(16, 16))
        self.assertEqual(a.status, "PASS")

    def test_fake_pc_whitelist_is_rejected(self):
        cert = build_certificate(P, C)
        tampered = copy.deepcopy(cert)
        entry = dict(tampered["memory_accesses"][0])
        entry["pc"] = 6  # LessThan, not a memory op
        entry["op"] = "LessThan"
        tampered["memory_accesses"][0] = entry
        res = verify_certificate(tampered, P)
        self.assertFalse(res.ok)
        self.assertTrue(any("not a Load/Store" in e for e in res.errors))

    def test_widened_interval_is_rejected(self):
        cert = build_certificate(P, C)
        tampered = copy.deepcopy(cert)
        tampered["memory_accesses"][0]["interval"] = "[0, n]"
        res = verify_certificate(tampered, P)
        self.assertFalse(res.ok)

    def test_missing_access_is_rejected(self):
        cert = build_certificate(P, C)
        tampered = copy.deepcopy(cert)
        tampered["memory_accesses"] = tampered["memory_accesses"][:5]
        res = verify_certificate(tampered, P)
        self.assertFalse(res.ok)
        self.assertTrue(any("coverage mismatch" in e for e in res.errors))

    def test_overall_unknown_without_reason_is_rejected(self):
        cert = build_certificate(P, C)
        tampered = copy.deepcopy(cert)
        tampered["status"] = "UNKNOWN"
        res = verify_certificate(tampered, P)
        self.assertFalse(res.ok)


if __name__ == "__main__":
    unittest.main()
