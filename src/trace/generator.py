#!/usr/bin/env python3
"""EXP-DORAM-01: fixed-seed unified access-trace generator.

Produces the SAME trace for every implementation (E0/E1/oracle). No implementation
may see the expected LOAD result; the trace only carries write values. LOAD rows
have ``value = null`` and the ground truth is computed separately by the oracle.

Record format (JSONL, one object per line):
    {"step": 0, "op": "LOAD", "address": 17, "value": null, "pattern": "read_never_written"}

Non-memory instructions are represented by a unified dummy access:
    op = "NOOP", address = 2**32 - 1 (VDORAM's field NegOne), value = null.
Every instruction yields exactly one row, so the row count never reveals the op type.
"""

from __future__ import annotations

import json
import os
import random
from typing import Iterator

WORD_BITS = 32
WORD_MASK = (1 << WORD_BITS) - 1
DUMMY_ADDR = WORD_MASK  # NegOne in a 32-bit field, matching VDORAM non-mem trace rows

N_VALUES = (64, 128, 256, 512)
T_VALUES = (128, 256, 512, 1024)
SEED = 20261123

PATTERNS = (
    "read_never_written",   # 1. read an address that is never written
    "read_same_repeat",     # 2. repeatedly read one fixed address
    "write_same_repeat",    # 3. many writes to the same address
    "write_then_read",      # 4. write then read the same address
    "interleaved_addrs",    # 5. several addresses accessed alternately
    "dummy_noop",           # 6. non-memory instruction -> unified dummy access
)


def _p_read_never_written(rng: random.Random, lo: int, hi: int) -> Iterator[dict]:
    while True:
        yield {"op": "LOAD", "address": rng.randrange(lo, hi), "value": None}


def _p_read_same(rng: random.Random, lo: int, hi: int) -> Iterator[dict]:
    addr = rng.randrange(lo, hi)
    while True:
        yield {"op": "LOAD", "address": addr, "value": None}


def _p_write_same(rng: random.Random, lo: int, hi: int) -> Iterator[dict]:
    addr = rng.randrange(lo, hi)
    v = rng.randrange(0, 1 << WORD_BITS)
    while True:
        v = (v + 1) & WORD_MASK
        yield {"op": "STORE", "address": addr, "value": v}


def _p_write_then_read(rng: random.Random, lo: int, hi: int) -> Iterator[dict]:
    addr = rng.randrange(lo, hi)
    v = rng.randrange(0, 1 << WORD_BITS)
    phase = 0
    while True:
        if phase == 0:
            v = (v + 7) & WORD_MASK
            yield {"op": "STORE", "address": addr, "value": v}
            phase = 1
        else:
            yield {"op": "LOAD", "address": addr, "value": None}
            phase = 0


def _p_interleaved(rng: random.Random, lo: int, hi: int) -> Iterator[dict]:
    addrs = [rng.randrange(lo, hi) for _ in range(4)]
    i = 0
    v = rng.randrange(0, 1 << WORD_BITS)
    while True:
        addr = addrs[i % len(addrs)]
        v = (v + 13) & WORD_MASK
        yield {"op": "STORE", "address": addr, "value": v}
        yield {"op": "LOAD", "address": addr, "value": None}
        i += 1


def _p_dummy(rng: random.Random, lo: int, hi: int) -> Iterator[dict]:
    while True:
        yield {"op": "NOOP", "address": DUMMY_ADDR, "value": None}


_BUILDERS = (
    _p_read_never_written,
    _p_read_same,
    _p_write_same,
    _p_write_then_read,
    _p_interleaved,
    _p_dummy,
)


def generate_trace(n: int, t: int, seed: int = SEED) -> list[dict]:
    """Generate one deterministic trace of length ``t`` over address space ``n``.

    Writes are confined to ``[0, n//2)``; reads of never-written addresses are
    confined to ``[n//2, n)``. This makes the "read never written" property
    structurally guaranteed rather than probabilistic.
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
        row = {
            "step": len(trace),
            "op": obj["op"],
            "address": obj["address"],
            "value": obj["value"],
            "pattern": PATTERNS[gidx],
        }
        trace.append(row)
        gidx = (gidx + 1) % len(gens)
    return trace


def trace_path(data_dir: str, n: int, t: int) -> str:
    return os.path.join(data_dir, "traces", f"trace_N{n}_T{t}.jsonl")


def save_trace(trace: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for row in trace:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def load_trace(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_all(data_dir: str, seed: int = SEED) -> list[tuple[int, int, str]]:
    """Generate all N×T traces (16 files). Returns [(N, T, path), ...]."""
    made = []
    for n in N_VALUES:
        for t in T_VALUES:
            tr = generate_trace(n, t, seed)
            p = trace_path(data_dir, n, t)
            save_trace(tr, p)
            made.append((n, t, p))
    return made


if __name__ == "__main__":
    import sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    made = generate_all(os.path.join(root, "data"))
    for n, t, p in made:
        print(f"N={n:4d} T={t:5d} -> {p}")
    print(f"generated {len(made)} traces, seed={SEED}")
