#!/usr/bin/env python3
"""ABA-01-C1 certificate generation and independent structured-rule checker.

The checker does NOT call analyze(). It re-derives, from the *bound program*
and the declared input constraint, the loop/guard structure and the fixed
Bubble Sort proof rules (R-INPUT / R-INNER / R-OUTPUT), then checks the
certificate's structured proof fields against them. Human-readable
``address_expr``/``dependencies`` strings are retained for display but never
used as evidence.

This is a fixed-program rule matcher, not a Lean/Coq/SMT theorem prover, and
it binds no runtime register/memory trace or R1CS relation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .analyzer import ANALYZER_VERSION, InputConstraint, analyze
from .cfg import BIT_SIZE, FIELD_PRIME, Instr, Program

CERT_SCHEMA = "aba-01-c1/v1"
SCOPE = "STATIC_CERTIFICATE_PROTOTYPE"

# Independent (not imported from analyzer) fixed-program expectations.
_EXPECTED_WRITERS = {
    0: (2, 5, 15, 17, 21, 23, 27, 29, 30, 33, 35, 38),
    1: (1, 32),
    2: (3, 6, 7, 10, 26, 36, 39, 40),
    3: (12,),
    6: (11, 25),
    8: (9,),
    15: (0,),
}
_KEY_INSTR = {
    0: Instr("Set", 15, 1), 1: Instr("PublicInput", 1),
    2: Instr("Set", 0, 0), 5: Instr("Add", 0, 0, 15),
    6: Instr("LessThan", 2, 0, 1), 7: Instr("Not", 2, 2),
    8: Instr("JumpIfZero", 2, 3), 9: Instr("Move", 8, 1),
    10: Instr("Set", 2, 0), 11: Instr("Set", 6, 0),
    12: Instr("Add", 3, 2, 15), 13: Instr("LessThan", 4, 3, 1),
    14: Instr("JumpIfZero", 4, 29), 20: Instr("JumpIfZero", 7, 26),
    25: Instr("Add", 6, 6, 15), 26: Instr("Move", 2, 3),
    30: Instr("LessThan", 0, 0, 6), 31: Instr("JumpIfZero", 0, 35),
    32: Instr("Sub", 1, 1, 15), 35: Instr("Set", 0, 0),
    38: Instr("Add", 0, 0, 15), 39: Instr("LessThan", 2, 0, 8),
    40: Instr("Not", 2, 2), 41: Instr("JumpIfZero", 2, 36),
}
_LOOP_HEADS = (3, 10, 12, 36)
_RULE_BY_HEAD = {3: "R-INPUT", 12: "R-INNER", 36: "R-OUTPUT"}


def build_certificate(program: Program, constraint: InputConstraint,
                      p: int = FIELD_PRIME) -> dict:
    a = analyze(program, constraint, p)
    digest = program.digest()
    return {
        "schema": CERT_SCHEMA,
        "scope": SCOPE,
        "status": a.status,
        "program": {
            "code_name": program.code_name,
            "source_commit": program.source_commit,
            "source_path": program.source_path,
            "program_hash": digest,
            "instruction_sequence_id": digest.removeprefix("sha256:")[:12],
            "instruction_count": len(program.instrs),
        },
        "field": {"prime_hex": hex(p), "bit_size": BIT_SIZE},
        "nmax": constraint.n_max,
        "input_constraint": {
            "n_min": constraint.n_min,
            "n_max": constraint.n_max,
            "bound_register": constraint.bound_register,
        },
        "memory_accesses": [
            {**asdict(x), "dependencies": list(x.dependencies)}
            for x in a.accesses
        ],
        "invariants": list(a.invariants),
        "field_conditions": [asdict(x) for x in a.field_conditions],
        "analyzer_version": ANALYZER_VERSION,
        "reasons": list(a.reasons),
    }


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    errors: tuple[str, ...] = ()


# --- independent CFG helpers (own implementation; no analyzer calls) ------------

def _backedges(program: Program) -> tuple[tuple[int, int], ...]:
    return tuple((pc, s) for pc in range(len(program.instrs))
                 for s in program.successors(pc) if s <= pc)


def _enclosing(program: Program, pc: int) -> tuple[int, int] | None:
    candidates = [(head, tail) for tail, head in _backedges(program)
                  if head <= pc <= tail]
    return max(candidates, key=lambda x: x[0]) if candidates else None


def _guard(program: Program, head: int, tail: int) -> tuple[int, int, int, bool] | None:
    for pc in range(head, tail + 1):
        ins = program.instrs[pc]
        if ins.op != "JumpIfZero" or not (ins.arg1 == head or ins.arg1 > tail):
            continue
        cond = ins.arg0
        w = program.last_writer_before(cond, pc)
        if w is None:
            continue
        inv = False
        if program.instrs[w].op == "Not" and program.instrs[w].arg0 == cond:
            cond = program.instrs[w].arg1
            inv = True
            w = program.last_writer_before(cond, w)
            if w is None:
                continue
        if program.instrs[w].op == "LessThan" and program.instrs[w].arg0 == cond:
            return pc, program.instrs[w].arg1, program.instrs[w].arg2, inv
    return None


def _structure_problems(program: Program) -> list[str]:
    problems: list[str] = []
    for reg, expected in _EXPECTED_WRITERS.items():
        actual = program.writers_of(reg)
        if actual != expected:
            problems.append(f"independent structure: R{reg} writers {actual} != {expected}")
    for pc, expected in _KEY_INSTR.items():
        if program.instrs[pc] != expected:
            problems.append(
                f"independent structure: PC{pc} {program.instrs[pc].as_row()} != {expected.as_row()}"
            )
    tails = {tail: head for tail, head in _backedges(program)}
    for head in _LOOP_HEADS:
        if head not in tails.values():
            problems.append(f"independent structure: no loop head {head}")
    if _guard(program, 3, 8) != (8, 0, 1, True):
        problems.append("independent structure: input guard not R0<R1 inverted")
    if _guard(program, 12, 28) != (14, 3, 1, False):
        problems.append("independent structure: inner guard not R3<R1")
    if _guard(program, 10, 34) != (31, 0, 6, False):
        problems.append("independent structure: outer guard not 0<R6")
    if _guard(program, 36, 41) != (41, 0, 8, True):
        problems.append("independent structure: output guard not R0<R8 inverted")
    return problems


def _rule_input(program: Program, entry: dict, errors: list[str], tag: str) -> None:
    def req(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(f"{tag} R-INPUT: {msg}")

    req(entry["op"] == "Store", "input-loop store op changed")
    req(program.instrs[0] == Instr("Set", 15, 1), "R15 is not constant 1")
    req(program.instrs[2] == Instr("Set", 0, 0), "R0 not initialised at PC2")
    req(program.instrs[5] == Instr("Add", 0, 0, 15), "R0 increment at PC5 changed")
    req(program.instrs[6] == Instr("LessThan", 2, 0, 1)
        and program.instrs[7] == Instr("Not", 2, 2)
        and program.instrs[8] == Instr("JumpIfZero", 2, 3),
        "input-loop guard sequence changed")
    req(program.instrs[1] == Instr("PublicInput", 1)
        and program.writers_of(1) == (1, 32)
        and program.instrs[32] == Instr("Sub", 1, 1, 15),
        "bound register R1 is not public n with guarded decrement")
    req(entry["address_def_pc"] in (2, 5), "address def is not input counter")


def _rule_inner(program: Program, entry: dict, errors: list[str], tag: str) -> None:
    def req(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(f"{tag} R-INNER: {msg}")

    req(program.instrs[0] == Instr("Set", 15, 1), "R15 is not constant 1")
    req(program.instrs[10] == Instr("Set", 2, 0), "R2 not initialised to 0 at PC10")
    req(program.writers_of(2) == (3, 6, 7, 10, 26, 36, 39, 40),
        "R2 has unexpected writers")
    req(program.instrs[12] == Instr("Add", 3, 2, 15), "R3 != R2+R15 at PC12")
    req(program.writers_of(3) == (12,), "R3 has unexpected writers")
    req(program.instrs[26] == Instr("Move", 2, 3), "R2 not updated from R3 at PC26")
    req(program.instrs[11] == Instr("Set", 6, 0)
        and program.instrs[25] == Instr("Add", 6, 6, 15)
        and program.writers_of(6) == (11, 25),
        "swap counter R6 structure changed")
    req(program.instrs[13] == Instr("LessThan", 4, 3, 1)
        and program.instrs[14] == Instr("JumpIfZero", 4, 29),
        "inner guard R3<R1 / exit changed")
    req(program.instrs[20] == Instr("JumpIfZero", 7, 26),
        "swap branch no longer merges at PC26")
    req(program.instrs[1] == Instr("PublicInput", 1)
        and program.writers_of(1) == (1, 32)
        and program.instrs[32] == Instr("Sub", 1, 1, 15),
        "bound register R1 changed")
    req(entry["address_def_pc"] in (15, 17, 21, 23),
        "R0 address definition is not a guarded R2/R3 move")
    if entry["address_def_pc"] in (15, 17, 21, 23):
        expected_src = 2 if entry["address_def_pc"] in (15, 21) else 3
        req(entry["address_source_register"] == expected_src,
            f"address source must be R{expected_src}")


def _rule_output(program: Program, entry: dict, errors: list[str], tag: str) -> None:
    def req(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(f"{tag} R-OUTPUT: {msg}")

    req(entry["op"] == "Load", "output-loop load op changed")
    req(program.instrs[9] == Instr("Move", 8, 1)
        and program.writers_of(8) == (9,),
        "R8 is not the unchanged copy of n")
    req(program.instrs[35] == Instr("Set", 0, 0), "R0 not initialised at PC35")
    req(program.instrs[38] == Instr("Add", 0, 0, 15), "R0 increment at PC38 changed")
    req(program.instrs[39] == Instr("LessThan", 2, 0, 8)
        and program.instrs[40] == Instr("Not", 2, 2)
        and program.instrs[41] == Instr("JumpIfZero", 2, 36),
        "output guard R0<R8 changed")
    req(entry["address_def_pc"] in (35, 38), "address def is not output counter")


_RULES = {"R-INPUT": _rule_input, "R-INNER": _rule_inner, "R-OUTPUT": _rule_output}


def verify_certificate(cert: dict, program: Program, *,
                       require_pass: bool = False,
                       p: int = FIELD_PRIME) -> CheckResult:
    """Independently verify the certificate's structured proof relations."""
    errors: list[str] = []

    def need(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    need(isinstance(cert, dict), "certificate is not an object")
    if not isinstance(cert, dict):
        return CheckResult(False, tuple(errors))

    need(cert.get("schema") == CERT_SCHEMA, "schema mismatch")
    need(cert.get("scope") == SCOPE, "scope is not static certificate prototype")
    status = cert.get("status")
    need(status in {"PASS", "FAIL", "UNKNOWN"}, "invalid status")
    need(cert.get("analyzer_version") == ANALYZER_VERSION, "analyzer version mismatch")

    prog = cert.get("program")
    need(isinstance(prog, dict), "missing program block")
    if isinstance(prog, dict):
        need(prog.get("code_name") == program.code_name, "code name mismatch")
        need(prog.get("source_commit") == program.source_commit,
             "source commit mismatch")
        need(prog.get("source_path") == program.source_path, "source path mismatch")
        need(prog.get("program_hash") == program.digest(),
             "program hash mismatch (instruction sequence changed)")
        need(prog.get("instruction_count") == len(program.instrs),
             "instruction count mismatch")
        need(isinstance(prog.get("program_hash"), str)
             and prog.get("program_hash", "").startswith("sha256:"),
             "program_hash is not a sha256 digest")

    fld = cert.get("field")
    need(isinstance(fld, dict) and fld.get("prime_hex") == hex(p)
         and fld.get("bit_size") == BIT_SIZE, "field parameters mismatch")

    con = cert.get("input_constraint")
    need(isinstance(con, dict), "missing input constraint")
    n_min = n_max = None
    if isinstance(con, dict):
        n_min, n_max = con.get("n_min"), con.get("n_max")
        need(isinstance(n_min, int) and isinstance(n_max, int), "n bounds must be ints")
        need(con.get("bound_register") == 1, "bound register must be R1")
        if isinstance(n_min, int) and isinstance(n_max, int):
            need(1 <= n_min <= n_max, "input constraint inconsistent (n=0 or n>Nmax)")
    need(cert.get("nmax") == n_max, "certificate Nmax disagrees with input constraint")
    if isinstance(n_max, int):
        need(n_max < p and n_max * n_max < p, "Nmax too large for field/no-wrap")

    structure = _structure_problems(program)
    accesses = cert.get("memory_accesses")
    need(isinstance(accesses, list), "missing memory access list")
    actual = set(program.memory_pcs())
    seen: set[int] = set()
    if isinstance(accesses, list):
        for entry in accesses:
            need(isinstance(entry, dict), "access entry is not an object")
            if not isinstance(entry, dict):
                continue
            pc = entry.get("pc")
            tag = f"PC {pc}"
            need(isinstance(pc, int) and 0 <= pc < len(program.instrs),
                 f"invalid access PC {pc!r}")
            if not isinstance(pc, int) or not (0 <= pc < len(program.instrs)):
                continue
            need(pc in actual, f"PC {pc} is not a Load/Store in the bound program")
            need(entry.get("op") == program.instrs[pc].op,
                 f"PC {pc} op does not match bound program")
            need(entry.get("status") in {"PASS", "FAIL", "UNKNOWN"},
                 f"PC {pc} has invalid status")
            need(entry.get("interval") in {"[0, n-1]", "UNKNOWN"},
                 f"PC {pc} has unrecognised interval")
            need(entry.get("address_register") == 0,
                 f"PC {pc} address register is not the VM address line R0")
            need(pc not in seen, f"duplicate access PC {pc}")
            seen.add(pc)

            # Independently derived expectations from the bound program.
            loop = _enclosing(program, pc)
            head = loop[0] if loop else None
            guard = _guard(program, *loop) if loop else None
            guard_pc = guard[0] if guard else None
            def_pc = program.last_writer_before(0, pc)
            def_ins = program.instrs[def_pc] if def_pc is not None else None
            expected_src = (def_ins.arg1 if def_ins is not None
                            and def_ins.op == "Move" and def_ins.arg0 == 0 else None)
            expected_rule = _RULE_BY_HEAD.get(head, "UNKNOWN")
            need(entry.get("loop_head") == head,
                 f"PC {pc} loop_head {entry.get('loop_head')!r} != program-derived {head!r}")
            need(entry.get("guard_pc") == guard_pc,
                 f"PC {pc} guard_pc {entry.get('guard_pc')!r} != program-derived {guard_pc!r}")
            need(entry.get("address_def_pc") == def_pc,
                 f"PC {pc} address_def_pc {entry.get('address_def_pc')!r} "
                 f"!= program-derived {def_pc!r}")
            need(entry.get("address_source_register") == expected_src,
                 f"PC {pc} address_source_register "
                 f"{entry.get('address_source_register')!r} != {expected_src!r}")
            need(entry.get("proof_rule") == expected_rule,
                 f"PC {pc} proof_rule {entry.get('proof_rule')!r} "
                 f"!= program-derived {expected_rule!r}")

            if entry.get("status") == "PASS":
                need(entry.get("interval") == "[0, n-1]",
                     f"PC {pc} claims PASS without [0,n-1] interval")
                need(bool(entry.get("dependencies")),
                     f"PC {pc} claims PASS without proof dependencies")
                # Text fields are NOT evidence; the rule is checked from the
                # bound program and structured fields only.
                rule = _RULES.get(expected_rule)
                if rule is None:
                    errors.append(f"PC {pc} has PASS but no supported proof rule")
                else:
                    rule(program, entry, errors, tag)
        need(seen == actual,
             f"access coverage mismatch: declared {sorted(seen)}, actual {sorted(actual)}")

    need(isinstance(cert.get("invariants"), list) and len(cert["invariants"]) >= 4,
         "missing invariant set")
    conds = cert.get("field_conditions")
    need(isinstance(conds, list) and bool(conds), "missing field conditions")
    if isinstance(conds, list):
        for c in conds:
            need(isinstance(c, dict)
                 and c.get("status") in {"PASS", "UNKNOWN", "ASSUMED"},
                 "invalid field condition status")

    if status == "PASS":
        need(not structure, "PASS certificate on a program failing fixed structure rules")
        need(all(a.get("status") == "PASS" for a in accesses or []),
             "overall PASS but some access is not PASS")
        need(not cert.get("reasons"), "overall PASS but analyzer reported reasons")
    if status == "UNKNOWN":
        need(any(a.get("status") == "UNKNOWN" for a in accesses or [])
             or bool(cert.get("reasons")),
             "overall UNKNOWN without any unresolved access/reason")
    if require_pass:
        need(status == "PASS", "certificate is not PASS")

    return CheckResult(not errors, tuple(errors))


def certificate_example(cert: dict) -> str:
    """Compact human-readable certificate sample (no file I/O)."""
    return json.dumps({
        "status": cert["status"],
        "program_hash": cert["program"]["program_hash"],
        "nmax": cert["nmax"],
        "accesses": [(a["pc"], a["op"], a["proof_rule"], a["interval"], a["status"])
                     for a in cert["memory_accesses"]],
        "field_conditions": [c["name"] + ":" + c["status"]
                             for c in cert["field_conditions"]],
    }, ensure_ascii=False)
