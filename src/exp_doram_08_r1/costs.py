#!/usr/bin/env python3
"""EXP-DORAM-08-R1 symbolic cost model (E0 / E1-A / E1-B).

All secret-multiplication counts are DERIVED from pinned upstream 10c90d35 gadget
chain (see docs/exp-doram-08-r1/source-corrections.md). Nothing in this module is
an MPC benchmark, a measured latency, or an R1CS constraint count.

Key R1 corrections vs EXP-DORAM-08:
  R1-1: c_upd_shared = 2 (was 1); c_upd_separate = c_eq + 2 (was c_eq + 1).
  R1-2: two read constructions: E1-A (with LowBit) and E1-B (no LowBit).
  R1-3: step-0 STORE always uses c_upd_separate; store steps are explicit.

Units:
  *_mults  : count of BeaverMulti (secret multiplications)
  *_linear : count of local FieldAdd operations
  rounds   : online barrier rounds under the CURRENT serial executor only
  preproc  : FieldBeaverTripleShare field elements (3 per mult)
  online   : exposed field elements per party (2 per mult); bytes UNKNOWN
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CostParams:
    """Explicit cost parameters. Defaults are source-derived (conservative).

    VERIFIED / DERIVED defaults (pinned upstream, see source-corrections.md):
      c_eq            = 389  = FieldNeg(1) + FieldInverse(386) + FieldNorm mul(1) + BoolNot(1)
      c_eq_e1_opt     = 388  = same but FieldNeg on public slot index -> local (0)
      c_sel           = 1    = one SelectCompose FieldMul per row
      lowbit_not      = 1, lowbit_and = 2  -> LowBit(k) = 3k-2
      c_upd_shared    = 2    = FieldNeg(value-old) 1 + FieldMul(eq*delta) 1  [R1-1]
      c_eq (for separate recompute) feeds c_upd_separate = c_eq + 2
      rounds_per_mult = 1    (current serial executor only)
      triple_elems    = 3    (FieldBeaverTripleShare{X,Y,XY})
      exposed_elems   = 2    (ExposeFieldValues([dA,dB]) per BeaverMulti)
      append_mults    = 0    (Fetch circuit excludes history append)
    """

    c_eq: int = 389
    c_sel: int = 1
    lowbit_not: int = 1
    lowbit_and: int = 2
    c_upd_shared: int = 2          # R1-1 corrected value
    rounds_per_mult: int = 1
    triple_elems: int = 3
    exposed_elems: int = 2
    append_mults: int = 0

    @property
    def lowbit_mults_per_slot(self) -> int:
        return self.lowbit_not + 2 * self.lowbit_and  # 3 per slot

    @property
    def lowbit_constant(self) -> int:
        return -self.lowbit_and  # LowBit(k) = 3k - 2

    @property
    def c_upd_separate(self) -> int:
        """R1-1: independent eq recompute + two update mults."""
        return self.c_eq + self.c_upd_shared

    def lowbit(self, k: int) -> int:
        if k <= 0:
            return 0
        return k * self.lowbit_not + (k - 1) * self.lowbit_and

    def fetch_e0(self, s: int) -> int:
        """E0 Fetch multiplications with s visible history rows."""
        if s <= 0:
            return 0
        return s * (self.c_eq + self.c_sel) + self.lowbit(s)
        # = 389s + s + (3s-2) = 393s - 2

    def fetch_a(self, n: int) -> int:
        """E1-A Fetch mults (with LowBit) over n slots."""
        if n <= 0:
            return 0
        return n * self.c_eq + self.lowbit(n) + n * self.c_sel
        # = 393n - 2

    def fetch_b(self, n: int) -> int:
        """E1-B Fetch mults (no LowBit, unique-slot construction) over n slots."""
        if n <= 0:
            return 0
        return n * self.c_eq + n * self.c_sel
        # = 390n

    def scaled(self, eq_ratio: float | int, upd_ratio: float | int) -> "CostParams":
        """Return params with c_eq = eq_ratio*c_sel and c_upd_shared = upd_ratio*c_sel.

        eq_ratio / upd_ratio are ASSUMPTION PARAMETERS (sensitivity scan), not
        measurements. c_upd_separate follows as c_eq + c_upd_shared.
        """
        return replace(
            self,
            c_eq=int(round(self.c_sel * eq_ratio)),
            c_upd_shared=int(round(self.c_sel * upd_ratio)),
        )


# ---------------------------------------------------------------------------
# per-step costs (explicit STORE step set; step 0 forced separate)
# ---------------------------------------------------------------------------

def e0_step(step: int, p: CostParams) -> int:
    """E0 mults at step (0-based): visible history length == step."""
    return p.fetch_e0(step) + p.append_mults


def e1a_step(step: int, n: int, is_store: bool, p: CostParams,
             share_eq: bool = True) -> int:
    """E1-A mults at step: scan n slots (with LowBit); STORE adds n updates.

    step 0: no Fetch; if STORE, updates forced to c_upd_separate.
    """
    total = 0
    if step > 0:
        total += p.fetch_a(n)
    if is_store:
        per = p.c_upd_separate if step == 0 or not share_eq else p.c_upd_shared
        total += n * per
    return total + p.append_mults


def e1b_step(step: int, n: int, is_store: bool, p: CostParams,
             share_eq: bool = True) -> int:
    """E1-B mults at step: scan n slots (no LowBit); STORE same as E1-A."""
    total = 0
    if step > 0:
        total += p.fetch_b(n)
    if is_store:
        per = p.c_upd_separate if step == 0 or not share_eq else p.c_upd_shared
        total += n * per
    return total + p.append_mults


# ---------------------------------------------------------------------------
# totals: independent step summation + closed forms
# ---------------------------------------------------------------------------

def e0_total_by_sum(T: int, p: CostParams) -> int:
    return sum(e0_step(s, p) for s in range(T))


def e0_total_closed(T: int, p: CostParams) -> int:
    if T <= 0:
        return 0
    K = p.c_eq + p.c_sel + 3  # 393 with defaults
    b = p.lowbit_and           # 2
    return K * T * (T - 1) // 2 - b * (T - 1) + T * p.append_mults


def e1a_total_by_sum(T: int, n: int, store_steps: set[int], p: CostParams,
                     share_eq: bool = True) -> int:
    return sum(e1a_step(s, n, s in store_steps, p, share_eq) for s in range(T))


def e1b_total_by_sum(T: int, n: int, store_steps: set[int], p: CostParams,
                     share_eq: bool = True) -> int:
    return sum(e1b_step(s, n, s in store_steps, p, share_eq) for s in range(T))


def e1a_total_closed(T: int, n: int, store_steps: set[int], p: CostParams,
                     share_eq: bool = True) -> int:
    if T <= 0 or n <= 0:
        return 0
    fetch = p.fetch_a(n)
    w0 = 1 if 0 in store_steps else 0
    wpos = sum(1 for s in store_steps if 0 <= s < T and s > 0)
    upd0 = w0 * n * p.c_upd_separate
    updpos = wpos * n * (p.c_upd_shared if share_eq else p.c_upd_separate)
    return (T - 1) * fetch + upd0 + updpos + (T - 1) * p.append_mults


def e1b_total_closed(T: int, n: int, store_steps: set[int], p: CostParams,
                     share_eq: bool = True) -> int:
    if T <= 0 or n <= 0:
        return 0
    fetch = p.fetch_b(n)
    w0 = 1 if 0 in store_steps else 0
    wpos = sum(1 for s in store_steps if 0 <= s < T and s > 0)
    upd0 = w0 * n * p.c_upd_separate
    updpos = wpos * n * (p.c_upd_shared if share_eq else p.c_upd_separate)
    return (T - 1) * fetch + upd0 + updpos + (T - 1) * p.append_mults


def cross_threshold_n(T: int, store_steps: set[int], variant: str,
                      p: CostParams, share_eq: bool = True) -> float:
    """Continuous n upper bound for E1_X < E0, derived from exact sums.

    variant: 'A' or 'B'. Returns 0.0 for T<=1. Not an empirical threshold.
    """
    if T <= 1:
        return 0.0
    fetch_coef = p.fetch_a(1) if variant == "A" else p.fetch_b(1)
    # fetch_X(n) = fetch_coef*n + const; const cancels at exact-cross derivation
    w0 = 1 if 0 in store_steps else 0
    wpos = sum(1 for s in store_steps if 0 <= s < T and s > 0)
    upd_per_pos = p.c_upd_shared if share_eq else p.c_upd_separate
    denom = (T - 1) * fetch_coef + w0 * p.c_upd_separate + wpos * upd_per_pos
    if denom <= 0:
        return float("inf")
    K = p.c_eq + p.c_sel + 3
    numer = K * T * (T - 1) // 2 - p.lowbit_and * (T - 1)
    return numer / denom


# ---------------------------------------------------------------------------
# linear / rounds / preprocessing / online
# ---------------------------------------------------------------------------

def e0_linear(T: int, p: CostParams) -> int:
    if T <= 0:
        return 0
    return (T - 1) * (2 * T - 1)


def e1a_linear(T: int, n: int, store_steps: set[int], p: CostParams) -> int:
    if T <= 0 or n <= 0:
        return 0
    fetch = (T - 1) * (4 * n - 1)  # 2n eq + n LowBit NOT + (n-1) select sums
    upd = 2 * n * len([s for s in store_steps if 0 <= s < T])
    return fetch + upd


def e1b_linear(T: int, n: int, store_steps: set[int], p: CostParams) -> int:
    if T <= 0 or n <= 0:
        return 0
    fetch = (T - 1) * (3 * n - 1)  # 2n eq + (n-1) select sums; no LowBit
    upd = 2 * n * len([s for s in store_steps if 0 <= s < T])
    return fetch + upd


def rounds_from_mults(mults: int, p: CostParams) -> int:
    """Current serial executor: one barrier per BeaverMulti. NOT generalizable."""
    return mults * p.rounds_per_mult


def preproc_field_elems(mults: int, p: CostParams) -> int:
    return mults * p.triple_elems


def online_field_elems(mults: int, p: CostParams) -> int:
    """Per party, excluding input distribution and final outputs."""
    return mults * p.exposed_elems
