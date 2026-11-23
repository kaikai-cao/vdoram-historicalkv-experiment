#!/usr/bin/env python3
"""E1 — CurrentStateStore + Append-only HistoricalLog functional reference model.

This is a PLAIN in-memory data structure. It is NOT an ORAM and provides NO
access-pattern hiding. Its only purpose (per task package) is to check that a
two-structure design preserves HistoricalKV semantics and retains all fields the
public proof needs (the 5-column trace rows: addr, step, is_mem_op, is_mem_write,
val, plus the MiMC-style per-row commitment we model as a hash digest).

Fixed access order (task §四 EXP-01-B):
  1. read old value from CurrentStateStore
  2. compute Load/Store return value
  3. update CurrentStateStore
  4. append one row to HistoricalLog
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from src.baseline.e0_linear_scan import DUMMY_ADDR, TraceRow, make_row, replay_state


class CurrentStateStore:
    """Latest value per address. Read(a)=0 for never-written a. O(1) hash lookup."""

    def __init__(self) -> None:
        self._data: dict[int, int] = {}
        self.lookups: int = 0
        self.read_time_s: float = 0.0
        self.read_addresses: list[int] = []  # R1: exact lookup input sequence

    def read(self, address: int) -> int:
        t0 = time.perf_counter()
        value = self._data.get(address, 0)
        self.read_time_s += time.perf_counter() - t0
        self.lookups += 1
        self.read_addresses.append(address)
        return value

    def write(self, address: int, value: int) -> None:
        self._data[address] = value

    def snapshot(self) -> dict[int, int]:
        return dict(self._data)


def row_commitment(row: TraceRow, enc_key: int = 0) -> str:
    """Model of out_{i}_hash_mem_trace = H(magic, step, is_mem_op, is_mem_write, addr, val, enc_key).

    Real circuit uses MiMC; here a deterministic SHA-256 is sufficient to model
    the *binding* role (detect row deletion/reorder/value-tamper) in functional tests.
    """
    pre = f"{row.global_step_counter}|{row.is_mem_op}|{row.is_mem_write}|{row.mem_addr}|{row.mem_val}|{enc_key}"
    return hashlib.sha256(pre.encode("ascii")).hexdigest()


@dataclass
class HistoricalLog:
    """Append-only log of 5-column trace rows + per-row commitment.

    Retains everything required to (a) replay final state and (b) run the same
    historical consistency checks as MemoryTraceProveCircuitBoardGenerator.
    """

    enc_key: int = 0
    rows: list[TraceRow] = field(default_factory=list)
    commitments: list[str] = field(default_factory=list)

    def append(self, row: TraceRow) -> str:
        c = row_commitment(row, self.enc_key)
        self.rows.append(row)
        self.commitments.append(c)
        return c

    def replay(self) -> dict[int, int]:
        return replay_state(self.rows)

    def check_order_and_integrity(self) -> tuple[bool, str]:
        """Functional counterpart of MemoryTraceProveCircuitBoardGenerator.

        The C# Prove circuit first sorts rows by (mem_addr, global_step_counter),
        then enforces two constraint families on each adjacent pair (row-1, row):

          * order: if `last_access` (addr[row-1] != addr[row]) then addr must be
            strictly increasing; otherwise (same address) the global_step_counter
            must be strictly increasing.  Source: L121-166.
          * value integrity: if row-1 is NOT a write (is_mem_write=0) and it is
            NOT the last access to its address, then mem_val[row-1] must equal
            mem_val[row-2].  Source: L171-197.

        We reproduce these on the sorted array. Return (ok, reason).
        """
        if not self.rows:
            return True, "empty"
        ordered = sorted(self.rows, key=lambda r: (r.mem_addr, r.global_step_counter))
        n = len(ordered)
        for i in range(1, n):
            prev, cur = ordered[i - 1], ordered[i]
            last_access = prev.mem_addr != cur.mem_addr
            if last_access:
                if not cur.mem_addr > prev.mem_addr:
                    return False, "address order violated"
            else:
                if not cur.global_step_counter > prev.global_step_counter:
                    return False, "timestamp order violated (same address)"
        # value integrity: a non-write row not at the end of its address group
        # must carry the same value as the row before it in that group.
        for i in range(1, n - 1):
            cur = ordered[i]
            if cur.is_mem_op == 0 or cur.mem_addr == DUMMY_ADDR:
                continue
            if cur.is_mem_write == 0:  # a Load row
                prev = ordered[i - 1]
                if prev.mem_addr == cur.mem_addr and cur.mem_val != prev.mem_val:
                    return False, f"load value integrity violated at addr {cur.mem_addr} step {cur.global_step_counter}"
        return True, "ok"

    def hash_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.commitments:
            counts[c] = counts.get(c, 0) + 1
        return counts

    def recomputed_hash_counts(self) -> dict[str, int]:
        """Hash counts recomputed from the CURRENT rows (as the Prove circuit does)."""
        counts: dict[str, int] = {}
        for r in self.rows:
            c = row_commitment(r, self.enc_key)
            counts[c] = counts.get(c, 0) + 1
        return counts

    def check_hash_consistency(self) -> tuple[bool, str]:
        """Model of ZkProgramExecutor L571-587: Prove-time hashes must match the
        per-step hashes accumulated during VM execution. Tampering with any
        committed field (incl. the timestamp) without updating the commitment
        breaks this check."""
        if self.recomputed_hash_counts() != self.hash_counts():
            return False, "per-row hash commitment mismatch"
        return True, "ok"


class E1DualStore:
    def __init__(self) -> None:
        self.current = CurrentStateStore()
        self.log = HistoricalLog()
        self.actual_returns: list[int] = []

    def execute_step(self, op: str, fetch_address: int, trace_address: int,
                     value, step: int) -> int:
        """R1: one Fetch-equivalent lookup on EVERY non-initial step, like E0.

        - step 0: zeroShare special case; no lookup (matches E0 / source L205-207).
        - step > 0: exactly one CurrentStateStore.read(fetch_address), for ALL
          ops -- including STORE and NOOP whose return value does not use it.
          This mirrors the Fetch circuit always running with in_mem_addr=reg0.
        - The read result is consumed only by LOAD; STORE returns the write value,
          NOOP returns 0.
        - State writes and the historical row are keyed by ``trace_address``
          (= out_trace_mem_addr), NOT by the Fetch input address. For NOOP the
          two differ: fetch_address is an ordinary address, trace_address=NegOne.
        """
        if step == 0:
            old = 0                              # zeroShare; no lookup
        else:
            old = self.current.read(fetch_address)

        if op == "NOOP":
            returned = 0
        elif op == "LOAD":
            returned = old
        else:
            returned = int(value)

        if op == "STORE":
            self.current.write(trace_address, returned)
        # Load/NOOP: M_{t+1}[a] = M_t[a], no write

        self.log.append(make_row(op, trace_address, step, returned))
        self.actual_returns.append(returned)
        return returned

    def run(self, trace: list[dict]) -> dict:
        for rec in trace:
            # R1: separated addresses; legacy `address` fallback for old traces.
            fa = rec.get("fetch_address", rec.get("address"))
            ta = rec.get("trace_address", rec.get("address"))
            self.execute_step(rec["op"], fa, ta, rec.get("value"), rec["step"])
        return self.summary()

    def final_state(self) -> dict[int, int]:
        return self.log.replay()

    def summary(self) -> dict:
        return {
            "history_rows": len(self.log.rows),
            "hash_lookups": self.current.lookups,
            "queries": self.current.lookups,
            "query_time_s": self.current.read_time_s,
            "fetch_addresses": list(self.current.read_addresses),
            "integrity_ok": self.log.check_order_and_integrity()[0],
        }
