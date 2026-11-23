#!/usr/bin/env python3
"""E0-FullScan -- faithful full-history Fetch reference model (EXP-DORAM-07-R1).

Faithful to the pinned upstream MemoryTraceFetchCircuitBoardGenerator.cs:
  * every visible history row is scanned (L52-63 loop over ALL rows, no break);
  * each row gets one address-equality check (FieldEqualsGadget, L56);
  * the LATEST matching row's mem_val is selected (LowBit one-hot, L65-74);
  * no match -> default 0 (SelectCompose of all-zero selections);
  * step 0 -> zeroShare, no Fetch (ZkProgramExecutor L205-207);
  * dummy Fetch (STORE/NOOP steps) scans the full history too (L208-236).

Implementation choice for "latest value": FORWARD scan over history with
OVERWRITE of the running candidate on each address match. This never reduces
the scan range; it is equivalent to upstream's reversed raw bits + LowBit
one-hot selection (see fetch-semantics.md §2). Recorded here per task 4.2.

This is an INDEPENDENT model: it does NOT import src.exp_doram_07's counters.
"""

from __future__ import annotations

from .models import BaseR1Model


class E0FullScan(BaseR1Model):
    """Original scheme with the FULL-history Fetch semantics of the circuit."""

    def __init__(self, n: int | None = None) -> None:
        super().__init__()
        # n is an OPTIONAL declared domain used only for the "never written"
        # default; it does NOT shorten the scan (unlike old E0's _in_domain
        # early return). The circuit scans all rows regardless of address.
        self.n = n

    def _fetch_scan(self, address: int) -> int:
        """Scan EVERY visible history row; pick latest match; no early exit."""
        value = 0
        matched = False
        for row in self.history:  # forward order (oldest -> newest)
            self.c.history_rows_scanned += 1
            self.c.history_equality_checks += 1
            if row[0] == address:  # mem_addr equality
                value = row[4]     # overwrite -> newest match wins
                matched = True
        if matched:
            self.c.selection_operations += 1  # one selected output value
        return value
