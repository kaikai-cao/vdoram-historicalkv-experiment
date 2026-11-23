#!/usr/bin/env python3
"""Symbolic SelectCompose / eq-vector semantics checks for EXP-DORAM-08-R1.

Pure functions over integer address domains; no upstream import, no MPC.
Used by tests to validate the construction-correctness claims in
docs/exp-doram-08-r1/construction-comparison.md (P1/P2/P3).
"""

from __future__ import annotations


def eq_vector(addr: int | None, n: int, in_domain: bool = True) -> list[int]:
    """Raw eq_j = [addr == j] for j in [0,n-1].

    addr=None represents a domain-outside / dummy fetch (no match).
    j is the PUBLIC slot index; equality is structural.
    """
    out = []
    for j in range(n):
        out.append(1 if (addr is not None and in_domain and addr == j) else 0)
    return out


def select_compose(sel: list[int], values: list[int]) -> int:
    """out = sum_j sel_j * values_j; runs all terms even if all sel=0.

    This mirrors SelectComposeGadget (dc19cb7a): k FieldMul + (k-1) FieldAdd,
    no early exit. Return value is the arithmetic sum (default 0 if no match).
    """
    if len(sel) != len(values):
        raise ValueError("sel and values must have equal length")
    total = 0
    for j in range(len(sel)):
        total += sel[j] * values[j]
    return total


def lowbit_onehot(raw: list[int]) -> list[int]:
    """Compress raw eq bits to one-hot, selecting the LAST 1 (latest in E0 order).

    E1-A uses this; E1-B skips it. Mirrors LowBit selecting the last raw=1.
    """
    ones = [i for i, b in enumerate(raw) if b == 1]
    out = [0] * len(raw)
    if ones:
        out[ones[-1]] = 1
    return out


def e1_a_read(addr: int | None, n: int, values: list[int],
              in_domain: bool = True) -> int:
    """E1-A read: eq -> LowBit -> SelectCompose."""
    raw = eq_vector(addr, n, in_domain)
    sel = lowbit_onehot(raw)
    return select_compose(sel, values)


def e1_b_read(addr: int | None, n: int, values: list[int],
              in_domain: bool = True) -> int:
    """E1-B read: eq -> SelectCompose (no LowBit). Valid when eq is one-hot/zero."""
    raw = eq_vector(addr, n, in_domain)
    return select_compose(raw, values)


def select_compose_field_mul_count(n: int) -> int:
    """SelectComposeGadget does exactly n FieldMul regardless of selector values."""
    return n
