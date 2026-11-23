#!/usr/bin/env python3
"""EXP-DORAM-07 deterministic workload generator (5 workload families).

All workloads emit the SAME record schema so E0 and E1 consume byte-identical
operation sequences:

  {step, op, fetch_address, trace_address, value, workload}

Semantics follow the pinned upstream (see semantic-audit.md):
  * step 0        : no Fetch circuit; value = zeroShare (returned 0 on STORE/LOAD
                    only via execute_step's zeroShare branch)
  * step > 0      : exactly one Fetch on fetch_address, for ALL ops
  * STORE / LOAD  : fetch_address == trace_address == actual address in [0,n-1]
  * NOOP          : fetch_address = ordinary address (reg0), trace_address = NegOne
  * address domain: [0, n-1]; out-of-range queries handled in models

The workload controls only (op, address, value); the fetch/trace address
separation is applied here exactly as in EXP-DORAM-01-R1.
"""

from __future__ import annotations

import random

from .models import DUMMY_ADDR

WORKLOADS = ("uniform", "hotspot", "single_hot", "sparse_write", "dense_write")


def _noop_fetch_address(step: int, n: int) -> int:
    """Ordinary reg0 value for a NOOP step; deterministic, inside [0,n-1]."""
    return (step * 2654435761 + n) % n


def generate_workload(
    n: int,
    t: int,
    workload: str,
    seed: int = 20261123,
) -> list[dict]:
    """Generate one deterministic trace of length ``t`` over domain ``n``.

    Parameters
    ----------
    n : address domain size (>=1). Addresses are integers in [0, n-1].
    t : number of execution steps (must be > 0).
    workload : one of WORKLOADS.
    seed : fixed RNG seed; identical seed -> identical operation sequence.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    if t < 1:
        raise ValueError("t must be >= 1")
    if workload not in WORKLOADS:
        raise ValueError(f"unknown workload {workload!r}")

    rng = random.Random(f"{seed}|{n}|{t}|{workload}")

    hot_hi = max(1, n // 5)                    # top 20% addresses
    single = 0                                 # single hot address

    def pick_address() -> int:
        if workload == "single_hot":
            if rng.random() < 0.80:
                return single
            return rng.randrange(n)
        if workload == "hotspot":
            if rng.random() < 0.80:
                return rng.randrange(hot_hi)
            return rng.randrange(n)
        return rng.randrange(n)                # uniform / sparse / dense

    def pick_op() -> str:
        if workload == "sparse_write":
            r = rng.random()
            if r < 0.10:
                return "STORE"
            if r < 0.75:
                return "LOAD"
            return "NOOP"
        if workload == "dense_write":
            r = rng.random()
            if r < 0.75:
                return "STORE"
            if r < 0.95:
                return "LOAD"
            return "NOOP"
        # uniform / hotspot / single_hot: balanced memory workload
        r = rng.random()
        if r < 0.35:
            return "STORE"
        if r < 0.80:
            return "LOAD"
        return "NOOP"

    trace: list[dict] = []
    for step in range(t):
        op = pick_op()
        address = pick_address()
        if op == "NOOP":
            fetch_address = _noop_fetch_address(step, n)
            trace_address = DUMMY_ADDR
            value = None
        else:
            fetch_address = address
            trace_address = address
            value = rng.randrange(1, 1000) if op == "STORE" else None
        trace.append(
            {
                "step": step,
                "op": op,
                "fetch_address": fetch_address,
                "trace_address": trace_address,
                "value": value,
                "workload": workload,
            }
        )
    return trace


def op_counts(trace: list[dict]) -> dict:
    counts = {"STORE": 0, "LOAD": 0, "NOOP": 0}
    for rec in trace:
        counts[rec["op"]] += 1
    return counts
