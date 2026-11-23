#!/usr/bin/env python3
"""EXP-DORAM-07 shared primitives: 5-column trace row, counters, helpers.

The five trace columns and their semantics mirror the pinned upstream source:
  MemoryTraceFetchCircuitBoardGenerator.cs L13-14 (column names)
  ZkVmExecutorCircuitBoardGenerator.cs L967-1007 (row construction)

No cryptographic claim is made. Counters are ABSTRACT reference-model operation
counts, NOT MPC multiplication gates, communication rounds, or R1CS constraints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import NamedTuple

# NegOne sentinel used by upstream for non-memory trace rows
# (ZkVmExecutorCircuitBoardGenerator.cs L992 constNumberNegOneWire).
DUMMY_ADDR = (1 << 32) - 1

COLUMNS = ("mem_addr", "global_step_counter", "is_mem_op", "is_mem_write", "mem_val")


class TraceRow(NamedTuple):
    """One immutable historical event; field order == upstream column order."""

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


def make_trace_row(op: str, trace_address: int, step: int, returned_value: int) -> TraceRow:
    """Build a 5-column row exactly as upstream ZkVmExecutor does.

    STORE -> is_mem_op=1, is_mem_write=1, mem_val = written value
    LOAD  -> is_mem_op=1, is_mem_write=0, mem_val = fetched value
    NOOP  -> is_mem_op=0, is_mem_write=0, addr=NegOne, mem_val=0

    NOTE: ``trace_address`` (== out_trace_mem_addr) already carries the NegOne
    sentinel for NOOP; the caller supplies that, matching L991-992.
    """
    if op == "STORE":
        return TraceRow(int(trace_address), step, 1, 1, int(returned_value))
    if op == "LOAD":
        return TraceRow(int(trace_address), step, 1, 0, int(returned_value))
    if op == "NOOP":
        return TraceRow(int(trace_address), step, 0, 0, 0)
    raise ValueError(f"unknown op {op!r}")


def row_commitment(row: TraceRow, enc_key: int = 0) -> str:
    """Deterministic stand-in for out_{row}_hash_mem_trace (MiMC in upstream).

    Used only to detect row deletion/reorder/tamper in functional tests; it is
    NOT a MiMC implementation and makes no cryptographic claim.
    """
    import hashlib

    pre = (
        f"{row.global_step_counter}|{row.is_mem_op}|{row.is_mem_write}|"
        f"{row.mem_addr}|{row.mem_val}|{enc_key}"
    )
    return hashlib.sha256(pre.encode("ascii")).hexdigest()


def latest_value(history: list[TraceRow], address: int) -> int:
    """Canonical latest_value(HistoryLog, a) used by the consistency invariant.

    Definition: the mem_val of the LAST row with is_mem_write=1 and
    mem_addr == address; 0 if the address was never written. Load rows are not
    writes, so they never create a value; NOOP rows carry the NegOne sentinel.
    This aligns with the upstream value-integrity rule
    (MemoryTraceProveCircuitBoardGenerator.cs L167-193).
    """
    value = 0
    for row in history:
        if row[3] == 1 and row[0] == address:  # is_mem_write == 1
            value = row[4]
    return value


@dataclass
class Counters:
    """Abstract operation counters for the reference models (see task 5.3)."""

    history_rows_scanned: int = 0
    shadow_slots_scanned: int = 0
    equality_checks: int = 0
    selection_operations: int = 0
    update_operations: int = 0
    history_append_operations: int = 0
    fetch_count: int = 0
    query_count: int = 0
    update_count: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


class BaseKV:
    """Shared step orchestration for E0 and E1.

    Both models expose the SAME four operations required by task 5.1:
      fetch(address)              -- one Fetch query (full-length, no early exit)
      query(address)              -- workload-level read; delegates to fetch
      add(op, trace_addr, step, returned) -- state update + history append
      export()                    -- the complete immutable history log

    ``execute_step`` applies the pinned VDORAM step semantics:
      step 0  -> memVal = zeroShare, no scan at all (ZkProgramExecutor L201-203)
      step>0  -> exactly one fetch on fetch_address for EVERY op
                (ZkProgramExecutor L205-230), result consumed only by LOAD.
    """

    def __init__(self) -> None:
        self.history: list[TraceRow] = []
        self.commitments: list[str] = []
        self.c = Counters()
        self.actual_returns: list[int] = []
        self.fetch_addresses: list[int] = []
        self.query_time_s = 0.0
        self.update_time_s = 0.0
        self.append_time_s = 0.0
        self.export_time_s = 0.0

    # -- subclass hooks -------------------------------------------------
    def _fetch_scan(self, address: int) -> int:
        raise NotImplementedError

    def _state_update(self, address: int, value: int) -> None:
        """E1 overrides with full-domain shadow update; E0 is a no-op."""
        return None

    # -- unified operations --------------------------------------------
    def fetch(self, address: int) -> int:
        """One fixed-length Fetch scan. No data-dependent early exit."""
        import time

        t0 = time.perf_counter()
        value = self._fetch_scan(int(address))
        self.query_time_s += time.perf_counter() - t0
        self.c.fetch_count += 1
        self.fetch_addresses.append(int(address))
        return value

    def query(self, address: int) -> int:
        """Workload-level Query; increases query_count and delegates to fetch."""
        self.c.query_count += 1
        return self.fetch(address)

    def add(self, op: str, trace_address: int, step: int, returned_value: int) -> None:
        """Update state (E1 only) then append one immutable history row."""
        import time

        t0 = time.perf_counter()
        if op == "STORE":
            self._state_update(int(trace_address), int(returned_value))
        self.update_time_s += time.perf_counter() - t0

        t1 = time.perf_counter()
        row = make_trace_row(op, trace_address, step, returned_value)
        self.history.append(row)
        self.commitments.append(row_commitment(row))
        self.c.history_append_operations += 1
        self.append_time_s += time.perf_counter() - t1

    def execute_step(self, rec: dict) -> int:
        """Execute one recorded step under pinned VDORAM Fetch semantics."""
        step = int(rec["step"])
        op = rec["op"]
        fetch_address = int(rec["fetch_address"])
        trace_address = int(rec["trace_address"])

        if step == 0:
            fetched = 0  # zeroShare; NO Fetch circuit (source L201-203)
        elif op == "LOAD":
            fetched = self.query(fetch_address)  # LOAD consumes the fetched value
        else:
            fetched = self.fetch(fetch_address)  # STORE/NOOP: Fetch runs, unused

        if op == "LOAD":
            returned = fetched
        elif op == "STORE":
            returned = int(rec["value"])
            self.c.update_count += 1
        elif op == "NOOP":
            returned = 0
        else:
            raise ValueError(f"unknown op {op!r}")

        self.add(op, trace_address, step, returned)
        self.actual_returns.append(returned)
        return returned

    def run(self, trace: list[dict]) -> dict:
        import time

        gc_collect = __import__("gc").collect
        gc_collect()
        t0 = time.perf_counter()
        for rec in trace:
            self.execute_step(rec)
        total = time.perf_counter() - t0
        return self.summary(total)

    def export(self) -> list[TraceRow]:
        """Return the complete immutable history (Export), unmodified."""
        import time

        t0 = time.perf_counter()
        rows = list(self.history)
        self.export_time_s += time.perf_counter() - t0
        return rows

    def export_fields(self) -> list[tuple]:
        """Export as plain tuples for exact cross-model field comparison."""
        return [tuple(r) for r in self.export()]

    def summary(self, total_time_s: float = 0.0) -> dict:
        d = self.c.as_dict()
        d.update(
            {
                "history_rows": len(self.history),
                "total_time_s": total_time_s,
                "query_time_s": self.query_time_s,
                "update_time_s": self.update_time_s,
                "append_time_s": self.append_time_s,
                "export_time_s": self.export_time_s,
            }
        )
        return d
