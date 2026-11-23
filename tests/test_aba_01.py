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


class TestC1ProgramMutations(unittest.TestCase):
    """M1-M10: any broken key-register relation must not yield PASS."""

    def _not_pass(self, mutated, label):
        a = analyze(mutated, C)
        self.assertNotEqual(a.status, "PASS", label)
        cert = build_certificate(mutated, C)
        self.assertNotEqual(cert["status"], "PASS", label)
        self.assertFalse(verify_certificate(cert, mutated, require_pass=True).ok, label)

    def test_m1_r2_init_prime_minus_one(self):
        # The exact bug this patch fixes: (p-1)+1 == 0 mod p makes the guard
        # pass while R2 stays at p-1. Must never be PASS.
        mutated = P.with_instr(10, Instr("Set", 2, FIELD_PRIME - 1))
        a = analyze(mutated, C)
        self.assertNotEqual(a.status, "PASS")
        self.assertTrue(any("PC10" in r for r in a.reasons))
        self._not_pass(mutated, "M1")

    def test_m2_r2_init_unknown_constant(self):
        self._not_pass(P.with_instr(10, Instr("Set", 2, 3)), "M2")

    def test_m3_r2_init_unconstrained_register(self):
        self._not_pass(P.with_instr(10, Instr("Move", 2, 7)), "M3")

    def test_m4_r3_not_r2_plus_one(self):
        self._not_pass(P.with_instr(12, Instr("Add", 3, 2, 7)), "M4")

    def test_m5_r2_not_updated_from_r3(self):
        self._not_pass(P.with_instr(26, Instr("Move", 2, 7)), "M5")

    def test_m6_extra_r2_writer(self):
        # PC33 was Set R0,0; make it also write R2.
        self._not_pass(P.with_instr(33, Instr("Set", 2, 0)), "M6")

    def test_m7_extra_r3_writer(self):
        self._not_pass(P.with_instr(33, Instr("Set", 3, 0)), "M7")

    def test_m8_guard_operands_changed(self):
        self._not_pass(P.with_instr(13, Instr("LessThan", 4, 2, 1)), "M8")

    def test_m9_loop_guard_removed(self):
        self._not_pass(P.with_instr(14, Instr("Noop")), "M9")

    def test_m10_branch_address_definition_changed(self):
        self._not_pass(P.with_instr(20, Instr("JumpIfZero", 7, 29)), "M10")


class TestC1CertificateTamper(unittest.TestCase):
    """12 structured-field tamper cases: none may pass verification."""

    def setUp(self):
        self.cert = build_certificate(P, C)
        self.assertIn(self.cert["status"], ("PASS", "UNKNOWN"))

    def _reject(self, mutate, label):
        tampered = copy.deepcopy(self.cert)
        mutate(tampered)
        res = verify_certificate(tampered, P)
        self.assertFalse(res.ok, f"{label}: {res}")

    def test_t01_address_def_pc(self):
        self._reject(lambda c: c["memory_accesses"][0].update(address_def_pc=999),
                     "address_def_pc")

    def test_t02_address_source_register(self):
        self._reject(lambda c: c["memory_accesses"][1].update(address_source_register=9),
                     "address_source_register")

    def test_t03_guard_pc(self):
        self._reject(lambda c: c["memory_accesses"][2].update(guard_pc=999),
                     "guard_pc")

    def test_t04_loop_head(self):
        self._reject(lambda c: c["memory_accesses"][3].update(loop_head=3),
                     "loop_head")

    def test_t05_proof_rule(self):
        self._reject(lambda c: c["memory_accesses"][1].update(proof_rule="R-OUTPUT"),
                     "proof_rule")

    def test_t06_interval(self):
        self._reject(lambda c: c["memory_accesses"][0].update(interval="[0, n]"),
                     "interval")

    def test_t07_access_pc(self):
        self._reject(lambda c: c["memory_accesses"][0].update(pc=16),
                     "access_pc")

    def test_t08_bound_register(self):
        self._reject(lambda c: c["input_constraint"].update(bound_register=8),
                     "bound_register")

    def test_t09_source_path(self):
        self._reject(lambda c: c["program"].update(source_path="forged/Path.cs"),
                     "source_path")

    def test_t10_program_hash(self):
        self._reject(lambda c: c["program"].update(program_hash="sha256:" + "0" * 64),
                     "program_hash")

    def test_t11_instruction_count(self):
        self._reject(lambda c: c["program"].update(instruction_count=42),
                     "instruction_count")  # 42 is the OLD wrong count; real count is 43

    def test_t12_field_prime(self):
        self._reject(lambda c: c["field"].update(prime_hex=hex(FIELD_PRIME + 2)),
                     "field.prime_hex")

    def test_t13_text_fields_are_not_evidence(self):
        # Even perfectly plausible text cannot compensate for a broken relation.
        def tamper(c):
            e = c["memory_accesses"][0]
            e["address_expr"] = "looks valid"
            e["dependencies"] = ["R15=1", "n<=Nmax"]
            e["address_def_pc"] = 5   # real def is PC2 for PC4's R0
        self._reject(tamper, "text fields")


class TestC1CheckerIndependence(unittest.TestCase):
    def test_checker_never_calls_analyze(self):
        import src.aba_01.certificate as cm
        cert = build_certificate(P, C)
        original = cm.analyze

        def boom(*args, **kwargs):
            raise AssertionError("verify_certificate must not call analyze()")

        cm.analyze = boom
        try:
            res = cm.verify_certificate(cert, P, require_pass=True)
        finally:
            cm.analyze = original
        self.assertTrue(res.ok, res)

    def test_forged_pass_on_broken_program_is_rejected(self):
        mutated = P.with_instr(10, Instr("Set", 2, FIELD_PRIME - 1))
        forged = build_certificate(mutated, C)
        forged["status"] = "PASS"
        forged["reasons"] = []
        for e in forged["memory_accesses"]:
            e["status"] = "PASS"
            e["interval"] = "[0, n-1]"
        res = verify_certificate(forged, mutated, require_pass=True)
        self.assertFalse(res.ok)
        self.assertTrue(any("PC10" in err for err in res.errors))

    def test_instruction_count_is_43(self):
        self.assertEqual(len(P.instrs), 43)
        cert = build_certificate(P, C)
        self.assertEqual(cert["program"]["instruction_count"], 43)


if __name__ == "__main__":
    unittest.main()
