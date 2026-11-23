#!/usr/bin/env python3
"""E0 -- original HistoricalKV linear-scan reference (EXP-DORAM-07).

Semantics are those of EXP-DORAM-01's E0 (kept unchanged): append every row,
Fetch scans the history NEWEST-FIRST and returns on the first address match
(plain-text early exit), no match -> 0. This is the EFFICIENT faithful reference;
we deliberately do NOT slow it down (task 4.1).

The early exit here is a PLAINTEXT reference-model shortcut. In the real circuit
(MemoryTraceFetchCircuitBoardGenerator.cs L52-63) all rows are compared and a
LowBitGadget selects the latest; a reviewer must not read the Python early exit
as an MPC property. See design.md / decision.md for this distinction.
"""

from __future__ import annotations

from .models import BaseKV


class HistoricalKVLinearScan(BaseKV):
    """Original scheme: O(current_history_length) per Fetch query."""

    def __init__(self, n: int | None = None) -> None:
        super().__init__()
        # n is the declared address domain. None => unbounded (legacy traces).
        # Out-of-domain addresses are treated as "never written" -> 0, identically
        # in E0 and E1. This is a MODEL convention (upstream has no fixed n),
        # recorded in semantic-audit.md S1.4.
        self.n = n

    def _in_domain(self, address: int) -> bool:
        return self.n is None or (0 <= address < self.n)

    def _fetch_scan(self, address: int) -> int:
        if not self._in_domain(address):
            return 0
        # Newest-first scan, return on first match (faithful to EXP-DORAM-01 E0).
        for row in reversed(self.history):
            self.c.history_rows_scanned += 1
            self.c.equality_checks += 1
            if row[0] == address:  # mem_addr
                self.c.selection_operations += 1
                return row[4]      # mem_val
        return 0  # never written -> default 0

    def shadow_snapshot(self) -> None:
        """E0 has no shadow state; provided only for API symmetry."""
        return None
