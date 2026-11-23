#!/usr/bin/env python3
"""E0 — faithful *reference* of VDORAM's HistoricalKV linear-scan selection.

Source of truth (pinned commit 10c90d35464620a35ddb1e2c29d2e8725acedd52):
  CompatCircuit/CollaborativeZkVm/ZkVmCircuits/MemoryTraceFetchCircuitBoardGenerator.cs
    - ColumnNames = [mem_addr, global_step_counter, is_mem_op, is_mem_write, mem_val]
    - for row in traceCount-1 .. 0: FieldEqualsGadget(mem_addr[row], in_mem_addr)
      -> row_selection_{row}_raw  (reversed order)
    - LowBitGadget(raw bits) -> selects the LOWEST set bit of the reversed list,
      i.e. the LARGEST original row index == the most recent matching record
    - SelectComposeGadget -> out_trace_mem_val (0 if no row matched)
  MemoryTraceProveCircuitBoardGenerator.cs: sort by (addr, step) + value integrity.

This module reproduces that SELECTION SEMANTIC exactly (full-history scan, latest
match wins, no match -> 0) and logs the exact same 5-column rows the C# circuit
consumes. It is NOT a cryptographic circuit and makes no security claim.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

DUMMY_ADDR = (1 << 32) - 1

COLUMNS = ("mem_addr", "global_step_counter", "is_mem_op", "is_mem_write", "mem_val")


@dataclass(frozen=True)
class TraceRow:
    mem_addr: int
    global_step_counter: int
    is_mem_op: int
    is_mem_write: int
    mem_val: int

    def as_dict(self) -> dict:
        return {
            "mem_addr": self.mem_addr,
            "global_step_counter": self.global_step_counter,
            "is_mem_op": self.is_mem_op,
            "is_mem_write": self.is_mem_write,
            "mem_val": self.mem_val,
        }


def make_row(op: str, address: int, step: int, returned_value: int) -> TraceRow:
    """Build the 5-column trace row exactly as ZkVmExecutorCircuitBoardGenerator does.

    - Store: is_mem_op=1, is_mem_write=1, mem_val=value being written
    - Load : is_mem_op=1, is_mem_write=0, mem_val=value fetched from memory
    - NOOP : is_mem_op=0, is_mem_write=0, addr=NegOne, mem_val=0
    """
    if op == "STORE":
        return TraceRow(address, step, 1, 1, returned_value)
    if op == "LOAD":
        return TraceRow(address, step, 1, 0, returned_value)
    if op == "NOOP":
        return TraceRow(DUMMY_ADDR, step, 0, 0, 0)
    raise ValueError(f"unknown op {op!r}")


class E0LinearScan:
    """Linear-scan HistoricalKV reference. One instance per independent run."""

    def __init__(self) -> None:
        self.history: list[TraceRow] = []
        self.scanned_rows: int = 0          # total FieldEquals-style comparisons
        self.queries: int = 0
        self.query_time_s: float = 0.0      # pure fetch (linear scan) time
        self.actual_returns: list[int] = []
        self.fetch_addresses: list[int] = []  # R1: exact Fetch input sequence

    def fetch(self, address: int) -> tuple[int, int]:
        """Full-history scan, latest match wins, no match -> 0.

        Returns (value, scanned_row_count). Mirrors the reversed LowBitGadget:
        iterate newest-to-oldest and return the FIRST address match.
        """
        t0 = time.perf_counter()
        scanned = 0
        value = 0
        for row in reversed(self.history):
            scanned += 1
            if row.mem_addr == address:
                value = row.mem_val
                break
        self.query_time_s += time.perf_counter() - t0
        self.scanned_rows += scanned
        self.queries += 1
        self.fetch_addresses.append(address)
        return value, scanned

    def execute_step(self, op: str, fetch_address: int, trace_address: int,
                     value, step: int) -> int:
        """R1: run Fetch on EVERY non-initial step (ZkProgramExecutor L205-236).

        - step 0: `memVal = zeroShare`; no Fetch circuit is built/run.
        - step > 0: Fetch circuit runs with in_mem_addr = reg0 = ``fetch_address``
          for ALL ops (LOAD / STORE / NOOP). The full-history scan cost is
          incurred even when the VM does not consume the returned value.
        - The Fetch result is used only by LOAD (in_mem_val -> out_mem_val).
          STORE returns the write value; NOOP returns 0.
        - The historical row is keyed by ``trace_address`` (= out_trace_mem_addr:
          actual addr for LOAD/STORE, NegOne for NOOP), which is a DIFFERENT
          concept from the Fetch input address.
        """
        if step == 0:
            fetched = 0                      # zeroShare; Fetch circuit not run
        else:
            fetched, _ = self.fetch(fetch_address)

        if op == "LOAD":
            returned = fetched
        elif op == "STORE":
            returned = int(value)            # Fetch ran, result unused by STORE
        else:  # NOOP: Fetch ran, result unused
            returned = 0
        self.history.append(make_row(op, trace_address, step, returned))
        self.actual_returns.append(returned)
        return returned

    def run(self, trace: list[dict]) -> dict:
        for rec in trace:
            # R1 records carry separate fetch_address / trace_address. Fall back
            # to the legacy single `address` field for the original 16 traces so
            # the original 12 correctness tests keep working unchanged.
            fa = rec.get("fetch_address", rec.get("address"))
            ta = rec.get("trace_address", rec.get("address"))
            self.execute_step(rec["op"], fa, ta, rec.get("value"), rec["step"])
        return self.summary()

    def final_state(self) -> dict[int, int]:
        """Reconstruct final memory: last Store per address.

        Addresses that were only ever Loaded are NOT in the dict (Read returns 0
        via the fetch path, not via a stored entry). This matches the oracle's
        dictionary exactly and avoids phantom zero-valued keys.
        """
        return replay_state(self.history)

    def summary(self) -> dict:
        return {
            "history_rows": len(self.history),
            "scanned_rows": self.scanned_rows,
            "queries": self.queries,
            "query_time_s": self.query_time_s,
            "fetch_addresses": list(self.fetch_addresses),
        }


def replay_state(rows: list[TraceRow]) -> dict[int, int]:
    """Replay HistoricalKV rows -> final memory state (last Store wins).

    Only Store rows create/update an entry; a never-written address is absent
    from the dict and reads as 0. This mirrors M_{t+1}[a]=M_t[a] for Load.
    """
    state: dict[int, int] = {}
    for row in rows:
        if row.is_mem_op == 1 and row.mem_addr != DUMMY_ADDR and row.is_mem_write == 1:
            state[row.mem_addr] = row.mem_val
    return state
