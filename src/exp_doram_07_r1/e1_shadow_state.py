#!/usr/bin/env python3
"""E1-ShadowState -- fixed-domain shadow table (EXP-DORAM-07-R1).

Fresh implementation in the R1 package (does NOT modify src.exp_doram_07).
Semantics preserved from EXP-DORAM-07's E1:

  Query(addr): for j in 0..n-1: eq = (j == addr); select shadow[j] where eq
  Update(addr): for j in 0..n-1: eq = (j == addr); write value where eq

No secret-index access, no data-dependent early exit. The 5-column history log
is appended by the shared BaseR1Model.add() with the SAME rule as E0-FullScan,
so Export is field-for-field identical across models (task 4.3 / 6.1.11).

E1 is a plain array reference model, NOT an ORAM. It leaks n, T, operation mix
and public control flow; no obliviousness or verifiability is claimed.

Counters are split per task 5.1: shadow_slots_scanned + shadow_equality_checks
(note equality checks on the shadow domain are counted separately from the
history equality checks of E0).
"""

from __future__ import annotations

from .models import BaseR1Model, latest_value


class E1ShadowState(BaseR1Model):
    """E1: O(n) fixed-domain scan per Fetch query and per Update."""

    def __init__(self, n: int) -> None:
        super().__init__()
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n = int(n)
        self.shadow: list[int] = [0] * self.n  # default = HistoricalKV default 0

    def _fetch_scan(self, address: int) -> int:
        """Fixed full-domain scan; select the slot whose index == address."""
        value = 0
        n = self.n
        for j in range(n):
            self.c.shadow_slots_scanned += 1
            self.c.shadow_equality_checks += 1
            if j == address:  # [addr == j]
                value = self.shadow[j]
        if 0 <= address < n:
            self.c.selection_operations += 1
        # out-of-domain address matches no slot -> default 0
        return value

    def _state_update(self, address: int, value: int) -> None:
        """Fixed full-domain update; write only the matching slot."""
        n = self.n
        for j in range(n):
            self.c.shadow_slots_scanned += 1
            self.c.shadow_equality_checks += 1
            if j == address:  # [addr == j]
                self.shadow[j] = int(value)
                self.c.update_operations += 1

    def _invariant(self) -> tuple[bool, str]:
        """shadow[a] == latest_value(HistoryLog, a) for all a in [0,n-1].

        Reference-model correctness invariant only; NOT an R1CS constraint.
        """
        for a in range(self.n):
            expected = latest_value(self.history, a)
            if self.shadow[a] != expected:
                return False, (
                    f"addr {a}: shadow={self.shadow[a]} "
                    f"latest_value(history)={expected}"
                )
        return True, "ok"

    def shadow_snapshot(self) -> list[int]:
        return list(self.shadow)
