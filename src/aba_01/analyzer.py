#!/usr/bin/env python3
"""ABA-01-C1 static address-domain analyzer (prototype).

The analyzer recognises loop/address-generation *patterns in the program*; it
does not whitelist PCs alone, it never uses sample input addresses, and it now
checks the full register-role structure (writes, initialisation values, data
flow and loop placement) of the pinned Bubble Sort program. Any control flow
or address expression it cannot classify yields UNKNOWN (or FAIL for an
inconsistent input constraint).

This is a fixed-program proof-rule checker, not a general-purpose static
analyzer or a formal verifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cfg import BIT_SIZE, FIELD_PRIME, Instr, Program

ANALYZER_VERSION = "aba01-static-analyzer-0.2-c1"


@dataclass(frozen=True)
class InputConstraint:
    n_min: int = 1
    n_max: int = 16
    bound_register: int = 1

    def inconsistency(self, p: int) -> str | None:
        if self.n_min < 1:
            return "n_min must be >= 1 (n=0 breaks the program semantics)"
        if self.n_max < self.n_min:
            return "n_max < n_min (e.g. n > Nmax)"
        if self.n_max >= p:
            return "Nmax >= p"
        if self.n_max * self.n_max >= p:
            return "Nmax^2 >= p (swap counter may wrap mod p)"
        return None


@dataclass(frozen=True)
class AccessFact:
    pc: int
    op: str
    address_register: int
    address_def_pc: int | None
    address_source_register: int | None
    loop_head: int | None
    guard_pc: int | None
    proof_rule: str
    address_expr: str
    interval: str
    status: str
    dependencies: tuple[str, ...]
    reason: str = ""


@dataclass(frozen=True)
class FieldCondition:
    name: str
    status: str
    basis: str


@dataclass
class Analysis:
    status: str
    accesses: tuple[AccessFact, ...] = ()
    field_conditions: tuple[FieldCondition, ...] = ()
    invariants: tuple[str, ...] = ()
    reasons: list[str] = field(default_factory=list)


# --- fixed-program register roles ------------------------------------------------

EXPECTED_WRITERS: dict[int, tuple[int, ...]] = {
    0: (2, 5, 15, 17, 21, 23, 27, 29, 30, 33, 35, 38),
    1: (1, 32),
    # R2 doubles as a scratch register in the input/output loops; the exact
    # write set matters, and PC10 must specifically be Set R2,0.
    2: (3, 6, 7, 10, 26, 36, 39, 40),
    3: (12,),
    6: (11, 25),
    8: (9,),
    15: (0,),
}

KEY_INSTRUCTIONS: dict[int, Instr] = {
    0: Instr("Set", 15, 1),
    1: Instr("PublicInput", 1),
    2: Instr("Set", 0, 0),
    5: Instr("Add", 0, 0, 15),
    6: Instr("LessThan", 2, 0, 1),
    7: Instr("Not", 2, 2),
    8: Instr("JumpIfZero", 2, 3),
    9: Instr("Move", 8, 1),
    10: Instr("Set", 2, 0),
    11: Instr("Set", 6, 0),
    12: Instr("Add", 3, 2, 15),
    13: Instr("LessThan", 4, 3, 1),
    14: Instr("JumpIfZero", 4, 29),
    20: Instr("JumpIfZero", 7, 26),
    25: Instr("Add", 6, 6, 15),
    26: Instr("Move", 2, 3),
    30: Instr("LessThan", 0, 0, 6),
    31: Instr("JumpIfZero", 0, 35),
    32: Instr("Sub", 1, 1, 15),
    35: Instr("Set", 0, 0),
    38: Instr("Add", 0, 0, 15),
    39: Instr("LessThan", 2, 0, 8),
    40: Instr("Not", 2, 2),
    41: Instr("JumpIfZero", 2, 36),
}

# (instruction PC, required enclosing loop head). PC10/PC12/PC26 are the
# inner-loop initialisation/definition/merge points; their placement matters.
REQUIRED_LOOP_HEAD = {
    5: 3, 10: 10, 11: 10, 12: 12, 26: 12,
    32: 10, 38: 36,
}
# Initialisation points PC2/PC35 sit immediately *before* their loop heads.
REQUIRED_PRE_HEAD = {2: 3, 35: 36}


def _guard_of(program: Program, head: int, tail: int) -> tuple[int, int, int, bool] | None:
    """Return (guard_pc, left_reg, right_reg, inverted) for a loop guard."""
    for pc in range(head, tail + 1):
        ins = program.instrs[pc]
        if ins.op != "JumpIfZero" or not (ins.arg1 == head or ins.arg1 > tail):
            continue
        cond = ins.arg0
        w = program.last_writer_before(cond, pc)
        if w is None:
            continue
        inverted = False
        if program.instrs[w].op == "Not" and program.instrs[w].arg0 == cond:
            cond = program.instrs[w].arg1
            inverted = True
            w = program.last_writer_before(cond, w)
            if w is None:
                continue
        if program.instrs[w].op == "LessThan" and program.instrs[w].arg0 == cond:
            return pc, program.instrs[w].arg1, program.instrs[w].arg2, inverted
    return None


def _backedges(program: Program) -> tuple[tuple[int, int], ...]:
    return tuple(
        (pc, succ)
        for pc in range(len(program.instrs))
        for succ in program.successors(pc)
        if succ <= pc
    )


def _enclosing_loop_cache(program: Program) -> tuple[tuple[int, int], ...]:
    return tuple((head, tail) for tail, head in _backedges(program))


def _enclosing_loop(program: Program, pc: int) -> tuple[int, int] | None:
    candidates = [(head, tail) for tail, head in _backedges(program)
                  if head <= pc <= tail]
    return max(candidates, key=lambda ht: ht[0]) if candidates else None


def _resolve_n_bound(program: Program, reg: int) -> bool:
    """True if reg is provably n (R1 initial) or its unchanged copy (R8)."""
    writers = program.writers_of(reg)
    if reg == 1:
        return (writers == (1, 32)
                and program.instrs[1] == Instr("PublicInput", 1)
                and program.instrs[32] == Instr("Sub", 1, 1, 15))
    if reg == 8:
        return writers == (9,) and program.instrs[9] == Instr("Move", 8, 1)
    return False


def _has_instr(program: Program, head: int, tail: int, instr: Instr) -> bool:
    return any(program.instrs[i] == instr for i in range(head, tail + 1))


def global_structure_reasons(program: Program) -> list[str]:
    """Check fixed-program register roles, initialisation and loop placement.

    Presence of an instruction somewhere is not enough: every key value must be
    written at its expected PC, by the expected instruction, inside the
    expected control-flow region, with no extra writer.
    """
    reasons: list[str] = []
    for reg, expected in EXPECTED_WRITERS.items():
        actual = program.writers_of(reg)
        if actual != expected:
            reasons.append(
                f"R{reg} writers {actual} != expected {expected} "
                "(uninitialised or unconstrained address source)"
            )
    for pc, expected in KEY_INSTRUCTIONS.items():
        if program.instrs[pc] != expected:
            reasons.append(
                f"PC{pc} is {program.instrs[pc].as_row()}, expected {expected.as_row()}"
            )
    for pc, head in REQUIRED_LOOP_HEAD.items():
        loop = _enclosing_loop(program, pc)
        if loop is None or loop[0] != head:
            reasons.append(f"PC{pc} is not inside the loop with head {head}")
    for pc, head in REQUIRED_PRE_HEAD.items():
        if pc + 1 != head or _enclosing_loop(program, pc) is not None:
            reasons.append(f"PC{pc} must initialise immediately before loop head {head}")
    if _enclosing_loop(program, 9) is not None:
        reasons.append("PC9 (R8=n copy) must be outside every loop")
    if not _resolve_n_bound(program, 1):
        reasons.append("R1 is not the public n with only the guarded decrement")
    if not _resolve_n_bound(program, 8):
        reasons.append("R8 is not an unchanged copy of initial R1 (n)")
    for head, tail, want in (
        (3, 8, (8, 0, 1, True)),
        (12, 28, (14, 3, 1, False)),
        (10, 34, (31, 0, 6, False)),
        (36, 41, (41, 0, 8, True)),
    ):
        if _guard_of(program, head, tail) != want:
            reasons.append(f"loop [{head},{tail}] guard does not match {want}")
    return reasons


def analyze(program: Program, constraint: InputConstraint,
            p: int = FIELD_PRIME) -> Analysis:
    bad = constraint.inconsistency(p)
    if bad is not None:
        return Analysis("FAIL", reasons=[f"input constraint invalid: {bad}"])

    reasons = global_structure_reasons(program)

    guards: dict[tuple[int, int], tuple[int, int, int, bool]] = {}
    for head, tail in _enclosing_loop_cache(program):
        g = _guard_of(program, head, tail)
        if g is None:
            reasons.append(f"loop [{head},{tail}] has no recognisable guard")
        else:
            guards[(head, tail)] = g

    inner_ok = any(
        (left == 3 and right == 1 and not inv
         and program.instrs[10] == Instr("Set", 2, 0)
         and program.instrs[12] == Instr("Add", 3, 2, 15)
         and program.instrs[26] == Instr("Move", 2, 3)
         and program.instrs[13] == Instr("LessThan", 4, 3, 1)
         and program.instrs[14] == Instr("JumpIfZero", 4, 29)
         and program.instrs[20] == Instr("JumpIfZero", 7, 26))
        for (head, tail), (gp, left, right, inv) in guards.items()
    )
    if not inner_ok:
        reasons.append(
            "sort inner-loop pattern (R2 init 0, R3=R2+1, guard R3<R1, "
            "R2=R3 merge, branch merge) not recognised"
        )
    outer_ok = any(
        (left == 0 and right == 6 and not inv
         and _resolve_n_bound(program, 1)
         and _has_instr(program, head, tail, Instr("Sub", 1, 1, 15)))
        for (head, tail), (gp, left, right, inv) in guards.items()
    )
    if not outer_ok:
        reasons.append("outer loop pattern (guard 0<R6, decrement R1) not recognised")

    accesses: list[AccessFact] = []
    for pc in program.memory_pcs():
        ins = program.instrs[pc]
        loop = _enclosing_loop(program, pc)
        def_pc = program.last_writer_before(0, pc)
        def_ins = program.instrs[def_pc] if def_pc is not None else None
        source = (def_ins.arg1 if def_ins is not None and def_ins.op == "Move"
                  and def_ins.arg0 == 0 else None)
        deps: list[str] = []
        expr = "UNKNOWN"
        interval = "UNKNOWN"
        status = "UNKNOWN"
        reason = ""
        rule = "UNKNOWN"
        guard_pc: int | None = None

        if loop is None:
            reason = "memory access outside any recognised loop"
        else:
            head, tail = loop
            g = guards.get((head, tail))
            if g is None:
                reason = f"loop [{head},{tail}] guard unrecognisable"
            else:
                gp, left, right, inv = g
                guard_pc = gp
                if head == 3 and left == 0 and _resolve_n_bound(program, right):
                    rule = "R-INPUT"
                    if (def_ins is not None
                            and (def_ins == Instr("Set", 0, 0)
                                 or def_ins == Instr("Add", 0, 0, 15))
                            and _has_instr(program, head, tail, Instr("Add", 0, 0, 15))):
                        expr = "R0 = input-loop counter, init 0, +1 per iteration"
                        interval = "[0, n-1]"
                        status = "PASS"
                        deps = ["input_loop_guard", "R15=1", "n<=Nmax", "n>=1"]
                    else:
                        reason = "input-loop R0 address source changed"
                elif head == 36 and left == 0 and _resolve_n_bound(program, right):
                    rule = "R-OUTPUT"
                    if (def_ins is not None
                            and def_ins == Instr("Set", 0, 0)
                            and _has_instr(program, head, tail, Instr("Add", 0, 0, 15))):
                        expr = "R0 = output-loop counter, init 0, +1 per iteration, bound R8=n"
                        interval = "[0, n-1]"
                        status = "PASS"
                        deps = ["output_loop_guard", "R8=n", "R15=1", "n<=Nmax"]
                    else:
                        reason = "output-loop R0 address source changed"
                elif inner_ok and outer_ok and left == 3 and right == 1 and not inv:
                    rule = "R-INNER"
                    if (def_ins is not None and def_ins.op == "Move"
                            and def_ins.arg0 == 0 and def_ins.arg1 in (2, 3)):
                        expr = f"R0 = R{def_ins.arg1} (R3=R2+1, guard R3<R1<=n, R2 init 0)"
                        interval = "[0, n-1]"
                        status = "PASS"
                        deps = ["inner_guard_R3<R1", "R2=0_init", "R3=R2+1",
                                "R2=R3_merge", "outer_R1>=1", "R1<=n",
                                "swap_counter=2", "branch_merge_PC26"]
                    else:
                        reason = "sort-loop address no longer copied from guarded R2/R3"

        accesses.append(AccessFact(
            pc=pc, op=ins.op, address_register=0, address_def_pc=def_pc,
            address_source_register=source, loop_head=(loop[0] if loop else None),
            guard_pc=guard_pc, proof_rule=rule, address_expr=expr,
            interval=interval, status=status, dependencies=tuple(deps), reason=reason,
        ))

    # Any global register-role failure downgrades every access.
    if reasons:
        accesses = tuple(
            AccessFact(a.pc, a.op, a.address_register, a.address_def_pc,
                       a.address_source_register, a.loop_head, a.guard_pc,
                       "UNKNOWN", a.address_expr, "UNKNOWN", "UNKNOWN",
                       a.dependencies,
                       (a.reason + "; " if a.reason else "")
                       + "global structure check failed: " + "; ".join(reasons))
            for a in accesses
        )

    field_conditions = (
        FieldCondition("n_range", "PASS" if not reasons else "UNKNOWN",
                       f"external assumption {constraint.n_min}<=n<={constraint.n_max}"),
        FieldCondition("field_no_wrap", "PASS" if not reasons else "UNKNOWN",
                       f"Nmax={constraint.n_max} < p and Nmax^2 < p, p={p:#x}"),
        FieldCondition("bit_decomposition", "ASSUMED",
                       "253-bit decomposition proof inserted by converter; not gate-audited"),
        FieldCondition("bool_not", "ASSUMED",
                       "Not does not check boolean inputs; here fed by LessThan only"),
    )

    status = "PASS" if (not reasons and accesses
                        and all(a.status == "PASS" for a in accesses)) else "UNKNOWN"
    invariants = (
        "I1 input loop: 0<=R0<=n, Store addr R0 in [0,n-1], R0=0 at PC2, +R15 at PC5",
        "I2 outer loop: 1<=R1<=n, R6 initialized 0 at PC11, increment at PC25, "
        "decrement R1 only when 0<R6",
        "I3 inner loop: R2=0 at PC10, R3=R2+1 at PC12, guard R3<R1 at PC13, "
        "R2=R3 at PC26, both branches merge at PC26",
        "I4 output loop: 0<=R0<=n, R8=initial n, R0=0 at PC35, "
        "Load addr R0 in [0,n-1]",
    )
    return Analysis(status, tuple(accesses), field_conditions, invariants, reasons)
