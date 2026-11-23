#!/usr/bin/env python3
"""Symbolic secret-multiplication cost model for EXP-DORAM-08.

All primitive counts are DERIVED from source evidence in
docs/exp-doram-08/source-evidence.md (pinned upstream 10c90d35).
Nothing here is an MPC benchmark or a latency measurement.

Units:
  - *_mults : count of BeaverMulti invocations (secret multiplications)
  - *_rounds: online barrier rounds under the CURRENT serial executor only
  - R1CS constraints are NOT modelled (evidence status UNKNOWN)
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CostParams:
    """Explicit cost parameters; defaults are source-derived or labelled ASSUMED.

    VERIFIED/DERIVED defaults (pinned upstream):
      c_eq = 389   = 1 (FieldNeg) + 386 (FieldInverse) + 1 (FieldNorm mul) + 1 (BoolNot)
      lowbit_not_per_bit = 1, lowbit_and_per_bit = 2  -> LowBit(k) = 3k-2
      c_sel = 1    = one SelectCompose FieldMul per row
      c_upd = 1    = one conditional-update FieldMul per slot (SHARED eq: ASSUMED feasible)
    ASSUMED in sensitivity scans:
      eq_ratio / upd_ratio vary c_eq / c_upd relative to c_sel.
    """

    c_eq: int = 389
    c_sel: int = 1
    lowbit_not_per_bit: int = 1
    lowbit_and_per_bit: int = 2
    c_upd: int = 1  # per slot, eq bits reused from the read scan (ASSUMED)
    rounds_per_mult: int = 1  # VERIFIED for current serial executor only
    field_elems_per_triple: int = 3  # FieldBeaverTripleShare{X,Y,XY}
    field_elems_exposed_per_mult: int = 2  # ExposeFieldValues([dA,dB])
    append_mults: int = 0  # Fetch circuit does not process history append

    @property
    def K(self) -> int:
        """Per-row coefficient of fetch_mults: K*k - lowbit_and_per_bit."""
        return self.c_eq + self.lowbit_not_per_bit + self.c_sel + self.lowbit_and_per_bit

    @property
    def c_upd_separate(self) -> int:
        """Per-slot update cost when eq must be recomputed (DERIVED)."""
        return self.c_eq + self.c_upd

    def scaled(self, eq_ratio: float | int, upd_ratio: float | int) -> "CostParams":
        """Return params with c_eq and c_upd expressed as multiples of c_sel.

        eq_ratio / upd_ratio are ASSUMPTION PARAMETERS, not measurements.
        """
        return replace(
            self,
            c_eq=int(round(self.c_sel * eq_ratio)),
            c_upd=int(round(self.c_sel * upd_ratio)),
        )


def lowbit_mults(k: int, p: CostParams) -> int:
    """Secret multiplications of LowBit over k selection rows."""
    if k <= 0:
        return 0
    return k * p.lowbit_not_per_bit + (k - 1) * p.lowbit_and_per_bit


def fetch_mults(k: int, p: CostParams) -> int:
    """Secret multiplications of one full scan over k rows/slots.

    = k*c_eq + LowBit(k) + k*c_sel = K*k - lowbit_and_per_bit  (k >= 1)
    """
    if k <= 0:
        return 0
    return k * p.c_eq + lowbit_mults(k, p) + k * p.c_sel


def fetch_linear_adds(k: int, p: CostParams) -> int:
    """Linear field additions of one scan (2 per eq, 1 per LowBit NOT, k-1 select sums)."""
    if k <= 0:
        return 0
    return 2 * k + k + (k - 1)


def e0_step(step: int, p: CostParams) -> int:
    """E0 mults at step `step` (0-based): visible history length == step."""
    return fetch_mults(step, p) + p.append_mults


def e1_step(step: int, n: int, is_store: bool, p: CostParams, share_eq: bool = True) -> int:
    """E1 mults at step `step`: scan n slots; STORE adds n conditional updates."""
    total = 0
    if step > 0:
        total += fetch_mults(n, p)
    if is_store:
        total += n * (p.c_upd if share_eq else p.c_upd_separate)
    return total + p.append_mults


def e0_total(T: int, p: CostParams) -> int:
    """Exact closed form: sum_{s=1}^{T-1} (K*s - b) = K*T*(T-1)/2 - b*(T-1)."""
    if T <= 0:
        return 0
    return p.K * T * (T - 1) // 2 - p.lowbit_and_per_bit * (T - 1)


def e1_total(T: int, n: int, W: int, p: CostParams, share_eq: bool = True) -> int:
    """Exact: (T-1)*(K*n-b) + W*n*(c_upd | c_eq+c_upd)."""
    if T <= 0 or n <= 0:
        return 0
    per_update = p.c_upd if share_eq else p.c_upd_separate
    return (T - 1) * fetch_mults(n, p) + W * n * per_update


def e0_total_by_sum(T: int, p: CostParams) -> int:
    """Independent step-by-step summation, used by tests to check the closed form."""
    return sum(e0_step(s, p) for s in range(T))


def e1_total_by_sum(
    T: int, n: int, store_steps: set[int], p: CostParams, share_eq: bool = True
) -> int:
    """Independent step-by-step summation with explicit STORE step indices."""
    return sum(e1_step(s, n, s in store_steps, p, share_eq) for s in range(T))


def cross_threshold_n(T: int, W: int, p: CostParams, share_eq: bool = True) -> float:
    """Largest (continuous) n for which E1 < E0, derived from the exact sums.

    n < K*T*(T-1) / (2*((T-1)*K + W*per_update))
    Common terms (append, Prove, setup/output rounds) cancel.
    """
    if T <= 1:
        return 0.0
    per_update = p.c_upd if share_eq else p.c_upd_separate
    denom = 2 * ((T - 1) * p.K + W * per_update)
    return p.K * T * (T - 1) / denom


def rounds_from_mults(mults: int, p: CostParams) -> int:
    """Current serial executor: one ExposeFieldValues barrier per BeaverMulti."""
    return mults * p.rounds_per_mult


def preproc_field_elems(mults: int, p: CostParams) -> int:
    return mults * p.field_elems_per_triple


def online_field_elems(mults: int, p: CostParams) -> int:
    """Per party, excluding input distribution and final outputs."""
    return mults * p.field_elems_exposed_per_mult
