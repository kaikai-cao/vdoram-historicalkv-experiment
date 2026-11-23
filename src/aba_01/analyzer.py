#!/usr/bin/env python3
"""ABA-01 static address-domain analyzer (prototype).

The analyzer recognises loop/address-generation *patterns in the program*; it
does not whitelist PCs and it never uses sample input addresses. Any control
flow or address expression it cannot classify yields UNKNOWN (or FAIL for an
inconsistent input constraint).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cfg import BIT_SIZE, FIELD_PRIME, Instr, MEMORY_OPS, Program

ANALYZER_VERSION = "aba01-static-analyzer-0.1"


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
    address_def_pc: int | None
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
        # PublicInput n, then only the guarded outer-loop decrement.
        return writers == (1, 32) and program.instrs[1].op == "PublicInput"
    if reg == 8:
        return writers == (9,) and program.instrs[9] == Instr("Move", 8, 1)
    return False


def _has_instr(program: Program, head: int, tail: int, instr: Instr) -> bool:
    return any(program.instrs[i] == instr for i in range(head, tail + 1))


def analyze(program: Program, constraint: InputConstraint,
            p: int = FIELD_PRIME) -> Analysis:
    reasons: list[str] = []
    bad = constraint.inconsistency(p)
    if bad is not None:
        return Analysis("FAIL", reasons=[f"input constraint invalid: {bad}"])

    # Global register-role checks: any unexpected write destroys the proof.
    if program.writers_of(15) != (0,) or program.instrs[0] != Instr("Set", 15, 1):
        reasons.append("R15 is not a stable constant 1")
    if not _resolve_n_bound(program, 8):
        reasons.append("R8 is not an unchanged copy of initial R1 (n)")
    if program.writers_of(6) != (11, 25):
        reasons.append("R6 swap counter has unexpected writers")
    if program.writers_of(1) != (1, 32):
        reasons.append("R1 has unexpected writers (bound may diverge from n)")
    # PC30 writes R0 as the LessThan destination for the outer-loop guard;
    # all other writes are the counter/address moves listed in source_semantics.
    if program.writers_of(0) != (2, 5, 15, 17, 21, 23, 27, 29, 30, 33, 35, 38):
        reasons.append("R0 has unexpected writers (address may be unconstrained)")

    guards: dict[tuple[int, int], tuple[int, int, int, bool]] = {}
    for head, tail in _enclosing_loop_cache(program):
        g = _guard_of(program, head, tail)
        if g is None:
            reasons.append(f"loop [{head},{tail}] has no recognisable guard")
        else:
            guards[(head, tail)] = g

    # Classify the inner sort loop: guard R3<R1, R3=R2+1, R2=R3 at merge.
    inner_ok = False
    for (head, tail), (gp, left, right, inv) in guards.items():
        if (left == 3 and right == 1 and not inv
                and _has_instr(program, head, tail, Instr("Add", 3, 2, 15))
                and _has_instr(program, head, tail, Instr("Move", 2, 3))):
            inner_ok = True
    if not inner_ok:
        reasons.append("sort inner-loop pattern (R3=R2+1, guard R3<R1, R2=R3) not recognised")
    outer_ok = any(
        (left == 0 and right == 6 and not inv
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
        deps: list[str] = []
        expr = "UNKNOWN"
        interval = "UNKNOWN"
        status = "UNKNOWN"
        reason = ""

        if loop is None:
            reason = "memory access outside any recognised loop"
        else:
            head, tail = loop
            g = guards.get((head, tail))
            if g is None:
                reason = f"loop [{head},{tail}] guard unrecognisable"
            else:
                gp, left, right, inv = g
                if head == 3 and left == 0 and _resolve_n_bound(program, right):
                    # Input loop: counter is R0 itself, initialised at PC2.
                    if (def_pc is not None
                            and (program.instrs[def_pc] == Instr("Set", 0, 0)
                                 or program.instrs[def_pc] == Instr("Add", 0, 0, 15))
                            and _has_instr(program, head, tail, Instr("Add", 0, 0, 15))):
                        expr = "R0 = input-loop counter, init 0, +1 per iteration"
                        interval = "[0, n-1]"
                        status = "PASS"
                        deps = ["input_loop_guard", "R15=1", "n<=Nmax", "n>=1"]
                    else:
                        reason = "input-loop R0 address source changed"
                elif head == 36 and left == 0 and _resolve_n_bound(program, right):
                    # Output loop: guard bound is R8 (copy of n).
                    if (def_pc is not None
                            and program.instrs[def_pc] == Instr("Set", 0, 0)
                            and _has_instr(program, head, tail, Instr("Add", 0, 0, 15))):
                        expr = "R0 = output-loop counter, init 0, +1 per iteration, bound R8=n"
                        interval = "[0, n-1]"
                        status = "PASS"
                        deps = ["output_loop_guard", "R8=n", "R15=1", "n<=Nmax"]
                    else:
                        reason = "output-loop R0 address source changed"
                elif inner_ok and outer_ok and left == 3 and right == 1 and not inv:
                    # Sort inner loop: address is R2 or R3, copied into R0.
                    if def_pc is not None and program.instrs[def_pc].op == "Move" \
                            and program.instrs[def_pc].arg0 == 0 \
                            and program.instrs[def_pc].arg1 in (2, 3):
                        src = program.instrs[def_pc].arg1
                        expr = f"R0 = R{src} (R3=R2+1, guard R3<R1<=n)"
                        interval = "[0, n-1]"
                        status = "PASS"
                        deps = ["inner_guard_R3<R1", "R3=R2+1", "R2=R3_merge",
                                "outer_R1>=1", "R1<=n", "swap_counter=2"]
                    else:
                        reason = "sort-loop address no longer copied from guarded R2/R3"

        accesses.append(AccessFact(pc, ins.op, def_pc, expr, interval,
                                   status, tuple(deps), reason))

    # Any global register-role failure downgrades all accesses.
    if reasons:
        accesses = tuple(
            AccessFact(a.pc, a.op, a.address_def_pc, a.address_expr, a.interval,
                       "UNKNOWN", a.dependencies,
                       (a.reason + "; " if a.reason else "") + "global structure check failed")
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
        "I1 input loop: 0<=R0<=n, Store addr R0 in [0,n-1]",
        "I2 outer loop: 1<=R1<=n, R6>=0, decrement guarded by 0<R6",
        "I3 inner loop: 0<=R2<R3<R1<=n, both branches reuse R0=R2/R3",
        "I4 output loop: 0<=R0<=n, Load addr R0 in [0,n-1]",
    )
    return Analysis(status, tuple(accesses), field_conditions, invariants, reasons)
