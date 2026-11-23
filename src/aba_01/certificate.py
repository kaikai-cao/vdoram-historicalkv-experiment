#!/usr/bin/env python3
"""ABA-01 certificate generation and independent structural checking.

The checker does NOT re-run the analyzer. It verifies schema, program binding
(hash + instruction count), that every declared access is a real Load/Store
in the bound program, and that range declarations are consistent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from .analyzer import ANALYZER_VERSION, InputConstraint, analyze
from .cfg import BIT_SIZE, FIELD_PRIME, Program

CERT_SCHEMA = "aba-01/v1"
SCOPE = "STATIC_CERTIFICATE_PROTOTYPE"


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


def verify_certificate(cert: dict, program: Program, *,
                       require_pass: bool = False,
                       p: int = FIELD_PRIME) -> CheckResult:
    """Independently check certificate structure/hash/ranges (no re-analysis)."""
    errors: list[str] = []

    def need(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    need(isinstance(cert, dict), "certificate is not an object")
    if not isinstance(cert, dict):
        return CheckResult(False, tuple(errors))

    need(cert.get("schema") == CERT_SCHEMA, "schema mismatch")
    need(cert.get("scope") == SCOPE, "scope is not static certificate prototype")
    need(cert.get("status") in {"PASS", "FAIL", "UNKNOWN"}, "invalid status")
    need(cert.get("analyzer_version") == ANALYZER_VERSION, "analyzer version mismatch")

    prog = cert.get("program")
    need(isinstance(prog, dict), "missing program block")
    if isinstance(prog, dict):
        need(prog.get("program_hash") == program.digest(),
             "program hash mismatch (instruction sequence changed)")
        need(prog.get("instruction_count") == len(program.instrs),
             "instruction count mismatch")
        need(isinstance(prog.get("program_hash"), str)
             and prog.get("program_hash", "").startswith("sha256:"),
             "program_hash is not a sha256 digest")
        need(prog.get("source_commit") == program.source_commit,
             "source commit mismatch")

    fld = cert.get("field")
    need(isinstance(fld, dict) and fld.get("prime_hex") == hex(p)
         and fld.get("bit_size") == BIT_SIZE, "field parameters mismatch")

    con = cert.get("input_constraint")
    need(isinstance(con, dict), "missing input constraint")
    n_min = n_max = None
    if isinstance(con, dict):
        n_min, n_max = con.get("n_min"), con.get("n_max")
        need(isinstance(n_min, int) and isinstance(n_max, int), "n bounds must be ints")
        if isinstance(n_min, int) and isinstance(n_max, int):
            need(1 <= n_min <= n_max, "input constraint inconsistent (n=0 or n>Nmax)")
    need(cert.get("nmax") == n_max, "certificate Nmax disagrees with input constraint")
    if isinstance(n_max, int):
        need(n_max < p and n_max * n_max < p, "Nmax too large for field/no-wrap")

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
            need(bool(entry.get("address_expr")), f"PC {pc} missing address expression")
            if entry.get("status") == "PASS":
                need(entry.get("interval") == "[0, n-1]",
                     f"PC {pc} claims PASS without [0,n-1] interval")
                need(bool(entry.get("dependencies")),
                     f"PC {pc} claims PASS without proof dependencies")
            need(pc not in seen, f"duplicate access PC {pc}")
            seen.add(pc)
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

    status = cert.get("status")
    if status == "PASS":
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
        "accesses": [(a["pc"], a["op"], a["interval"], a["status"])
                     for a in cert["memory_accesses"]],
        "field_conditions": [c["name"] + ":" + c["status"]
                             for c in cert["field_conditions"]],
    }, ensure_ascii=False)
