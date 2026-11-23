#!/usr/bin/env python3
"""E1 -- fixed-domain Shadow State Table + immutable History Log.

E1 keeps the SAME 5-column history and the SAME append rule as E0 (so Export is
byte-for-byte identical), but answers Query and performs Update by a fixed-length
full scan over [0, n-1] using address-equality selection:

  Query(addr):  for j in 0..n-1: eq = (j == addr); select shadow[j] where eq
  Update(addr): for j in 0..n-1: eq = (j == addr); write value where eq

There is NO secret-index dictionary lookup and NO data-dependent early exit.
This is a PLAIN array reference model, NOT an ORAM: it leaks n, T, operation
mix and public control flow, and provides no obliviousness or verifiability.
"""

from __future__ import annotations

from .models import BaseKV, latest_value


class ShadowStateTable(BaseKV):
    """E1: O(n) fixed-domain scan per Fetch query and per Update."""

    def __init__(self, n: int) -> None:
        super().__init__()
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n = int(n)
        # All addresses start at the HistoricalKV default value 0.
        self.shadow: list[int] = [0] * self.n

    def _in_domain(self, address: int) -> bool:
        return 0 <= address < self.n

    def _fetch_scan(self, address: int) -> int:
        """Fixed full-domain scan; select the slot whose index equals addr.

        Counter increments are batched after the loop (the scan length is a
        fixed n regardless of data), which is numerically identical to
        incrementing per slot but avoids per-iteration Python overhead.
        """
        value = 0
        n = self.n
        for j in range(n):
            if j == address:            # [addr == j]
                value = self.shadow[j]
        self.c.shadow_slots_scanned += n
        self.c.equality_checks += n
        if 0 <= address < n:
            self.c.selection_operations += 1
        # Out-of-domain address matches no slot -> returns default 0.
        return value

    def _state_update(self, address: int, value: int) -> None:
        """Fixed full-domain update; write only the matching slot."""
        n = self.n
        for j in range(n):
            if j == address:            # [addr == j]
                self.shadow[j] = int(value)
                self.c.update_operations += 1
        self.c.shadow_slots_scanned += n
        self.c.equality_checks += n

    def invariant(self) -> tuple[bool, str]:
        """After every step: shadow[a] == latest_value(HistoryLog, a) for all a.

        This is a REFERENCE-MODEL correctness invariant only; it is NOT an R1CS
        constraint and NOT a public proof.
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
