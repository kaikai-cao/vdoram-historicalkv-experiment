#!/usr/bin/env python3
"""EXP-DORAM-01-R1: unified trace with SEPARATED fetch and trace addresses.

Why R1 exists (source-verified against pinned commit 10c90d35464620a35ddb1e2c29d2e8725acedd52):
  * ZkProgramExecutor.cs L205-207: step 0 -> memVal = zeroShare (NO Fetch circuit).
  * ZkProgramExecutor.cs L208-236: EVERY non-initial step builds & runs
    MemoryTraceFetchCircuitBoardGenerator.
  * ZkProgramExecutor.cs L230: AddPrivate("in_mem_addr", thisRegisters[0])
    -> the Fetch input address is register 0, for ALL ops.
  * ZkProgramExecutor.cs L302: AddPrivate("in_mem_val", memVal)
    -> Fetch output is bound into the VM as in_mem_val.
  * ZkVmExecutorCircuitBoardGenerator.cs L990-1000: out_trace_mem_addr =
    SelectCompose(isStore, isLoad, outMemAddr, inMemAddr, NegOne):
    Store/Load -> actual address; otherwise -> NegOne sentinel.
  * ZkProgramExecutor.cs L348-353: out_mem_addr "equals reg0 if Op is Load,
    otherwise 0" -- a THIRD concept, irrelevant to R1 but confirms reg0 != trace addr.

Therefore a trace record must distinguish two address concepts:
  * fetch_address : thisRegisters[0], fed to Fetch on every non-initial step,
                    for STORE / LOAD / NOOP alike. Never the NegOne sentinel for
                    NOOP in R1 (reg0 holds an ordinary address).
  * trace_address : out_trace_mem_addr, written into the historical row;
                    NegOne for NOOP, actual address for STORE/LOAD.

For STORE/LOAD the two coincide (both are reg0). For NOOP they differ
(fetch_address = ordinary address, trace_address = NegOne) -- this is exactly
what test 4 of the R1 task exercises.

Old trace files (data/traces/trace_N*.jsonl, single `address` field) are kept
untouched. R1 files go to data/traces/r1/ and are NEVER written by generator.py.
"""

from __future__ import annotations

import os
import random

# Reuse the exact pattern builders / constants from the original generator so the
# access *distribution* is identical; only the address representation changes.
from src.trace.generator import (  # noqa: E402
    DUMMY_ADDR, N_VALUES, T_VALUES, SEED, PATTERNS, _BUILDERS,
)

R1_SUBDIR = "r1"


def _noop_fetch_address(step: int, n: int) -> int:
    """Ordinary (non-NegOne) reg0 value for a NOOP step, deterministic in step.

    Knuth multiplicative hash keeps NOOP fetch addresses spread over the write
    half of the address space so they may match historical Store rows -- which
    is fine: the NOOP does not consume the fetched value.
    """
    span = max(1, n // 2)
    return (step * 2654435761) % span


def generate_trace_r1(n: int, t: int, seed: int = SEED) -> list[dict]:
    """Generate one deterministic R1 trace of length ``t`` over address space ``n``.

    Identical access pattern to generator.generate_trace (same builders, same
    seed, same write/read halves), but every record carries both
    ``fetch_address`` and ``trace_address``.
    """
    if n < 2 or n not in N_VALUES:
        raise ValueError(f"unsupported N={n}")
    if t <= 0:
        raise ValueError("T must be positive")

    rng = random.Random(seed)
    write_lo, write_hi = 0, n // 2
    never_lo, never_hi = n // 2, n

    gens = [b(rng, write_lo, write_hi) if name != "read_never_written"
            else b(rng, never_lo, never_hi)
            for name, b in zip(PATTERNS, _BUILDERS)]

    trace: list[dict] = []
    gidx = 0
    while len(trace) < t:
        obj = next(gens[gidx])
        if len(trace) >= t:
            break
        step = len(trace)
        op = obj["op"]
        if op == "NOOP":
            fetch_address = _noop_fetch_address(step, n)
            trace_address = DUMMY_ADDR          # out_trace_mem_addr = NegOne
        else:
            # STORE / LOAD: reg0 holds the accessed address; trace addr == reg0.
            fetch_address = obj["address"]
            trace_address = obj["address"]
        trace.append({
            "step": step,
            "op": op,
            "fetch_address": fetch_address,
            "trace_address": trace_address,
            "value": obj["value"],
            "pattern": PATTERNS[gidx],
        })
        gidx = (gidx + 1) % len(gens)
    return trace


def r1_trace_path(data_dir: str, n: int, t: int) -> str:
    return os.path.join(data_dir, "traces", R1_SUBDIR, f"trace_N{n}_T{t}.jsonl")


def save_r1_trace(trace: list[dict], path: str) -> None:
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in trace:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_r1_trace(path: str) -> list[dict]:
    import json
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_all_r1(data_dir: str, seed: int = SEED) -> list[tuple[int, int, str]]:
    """Generate all 16 R1 traces under data/traces/r1/. Returns [(N, T, path), ...]."""
    made = []
    for n in N_VALUES:
        for t in T_VALUES:
            tr = generate_trace_r1(n, t, seed)
            p = r1_trace_path(data_dir, n, t)
            save_r1_trace(tr, p)
            made.append((n, t, p))
    return made


if __name__ == "__main__":
    import sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    made = generate_all_r1(os.path.join(root, "data"))
    for n, t, p in made:
        print(f"N={n:4d} T={t:5d} -> {p}")
    print(f"generated {len(made)} R1 traces, seed={SEED}")
