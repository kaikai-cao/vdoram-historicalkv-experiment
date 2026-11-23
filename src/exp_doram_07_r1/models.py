#!/usr/bin/env python3
"""EXP-DORAM-07-R1 shared primitives (independent of src.exp_doram_07).

We re-derive the 5-column trace row and step orchestration from the pinned
upstream source rather than importing the old package's counter logic, so that
a bug in the old counters cannot be inherited here. See fetch-semantics.md.

Counters are ABSTRACT reference-model operation counts, NOT MPC multiplication
gates, communication rounds, or R1CS constraints.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import NamedTuple

# NegOne sentinel used by upstream for non-memory trace rows
# (ZkVmExecutorCircuitBoardGenerator.cs L80, L946, L992 constNumberNegOneWire).
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
    """Build a 5-column row as upstream ZkVmExecutor does (L972-1011).

    STORE -> is_mem_op=1, is_mem_write=1, mem_val = written value
    LOAD  -> is_mem_op=1, is_mem_write=0, mem_val = fetched value
    NOOP  -> is_mem_op=0, is_mem_write=0, addr=NegOne, mem_val=0
    ``trace_address`` already carries NegOne for NOOP (caller supplies it).
    """
    if op == "STORE":
        return TraceRow(int(trace_address), step, 1, 1, int(returned_value))
    if op == "LOAD":
        return TraceRow(int(trace_address), step, 1, 0, int(returned_value))
    if op == "NOOP":
        return TraceRow(int(trace_address), step, 0, 0, 0)
    raise ValueError(f"unknown op {op!r}")


def row_commitment(row: TraceRow, enc_key: int = 0) -> str:
    """Deterministic stand-in for out_hash_mem_trace (MiMC upstream).

    Only for detecting row deletion/reorder/tamper in tests; NOT a MiMC
    implementation and makes no cryptographic claim.
    """
    import hashlib

    pre = (
        f"{row.global_step_counter}|{row.is_mem_op}|{row.is_mem_write}|"
        f"{row.mem_addr}|{row.mem_val}|{enc_key}"
    )
    return hashlib.sha256(pre.encode("ascii")).hexdigest()


def latest_value(history: list[TraceRow], address: int) -> int:
    """Canonical latest_value(HistoryLog, a): mem_val of LAST write row, else 0.

    Load rows are not writes; NOOP rows carry NegOne. Aligns with upstream
    MemoryTraceProveCircuitBoardGenerator.cs value-integrity rule.
    """
    value = 0
    for row in history:
        if row[3] == 1 and row[0] == address:  # is_mem_write == 1
            value = row[4]
    return value


@dataclass
class Counters:
    """Abstract operation counters, split per task 5.1 (history vs shadow)."""

    history_rows_scanned: int = 0
    history_equality_checks: int = 0
    shadow_slots_scanned: int = 0
    shadow_equality_checks: int = 0
    selection_operations: int = 0
    update_operations: int = 0
    history_append_operations: int = 0
    fetch_count: int = 0
    query_count: int = 0
    update_count: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


class BaseR1Model:
    """Shared step orchestration for the three R1 reference models.

    Subclasses implement ``_fetch_scan`` (and optionally ``_state_update``,
    ``_invariant``, ``shadow_snapshot``). The interface required by task 4.4
    is uniform: fetch / add / query / export / run.

    Pinned VDORAM step semantics (see fetch-semantics.md §4):
      step 0  -> memVal = zeroShare, NO Fetch circuit, but a trace row IS appended.
      step>0  -> exactly one Fetch on fetch_address for EVERY op (LOAD/STORE/NOOP),
                 result consumed only by LOAD.
    """

    def __init__(self) -> None:
        self.history: list[TraceRow] = []
        self.commitments: list[str] = []
        self.c = Counters()
        self.actual_returns: list[int] = []
        self.fetch_addresses: list[int] = []
        # time buckets (seconds); query_time is a SUBSET of fetch_time (LOAD only)
        self.fetch_time_s = 0.0
        self.query_time_s = 0.0
        self.update_time_s = 0.0
        self.append_time_s = 0.0
        self.export_time_s = 0.0
        self.execute_time_s = 0.0

    # -- subclass hooks -------------------------------------------------
    def _fetch_scan(self, address: int) -> int:
        raise NotImplementedError

    def _state_update(self, address: int, value: int) -> None:
        return None  # E0 has no shadow state

    def _invariant(self) -> tuple[bool, str]:
        return True, "n/a"

    # -- unified operations --------------------------------------------
    def fetch(self, address: int) -> int:
        """One Fetch scan. No data-dependent early exit in the circuit model."""
        import time

        t0 = time.perf_counter()
        value = self._fetch_scan(int(address))
        dt = time.perf_counter() - t0
        self.fetch_time_s += dt
        self.c.fetch_count += 1
        self.fetch_addresses.append(int(address))
        return value

    def query(self, address: int) -> int:
        """Workload-level Query; delegates to fetch; query_time is a subset."""
        import time

        t0 = time.perf_counter()
        value = self.fetch(address)
        self.query_time_s += time.perf_counter() - t0
        self.c.query_count += 1
        return value

    def add(self, op: str, trace_address: int, step: int, returned_value: int) -> None:
        """Update state (E1 only) then append one immutable history row."""
        import time

        t0 = time.perf_counter()
        if op == "STORE":
            self._state_update(int(trace_address), int(returned_value))
            self.c.update_count += 1
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
            fetched = 0  # zeroShare; no Fetch circuit (ZkProgramExecutor L205-207)
        elif op == "LOAD":
            fetched = self.query(fetch_address)
        else:
            fetched = self.fetch(fetch_address)  # STORE/NOOP: Fetch runs, unused

        if op == "LOAD":
            returned = fetched
        elif op == "STORE":
            returned = int(rec["value"])
        elif op == "NOOP":
            returned = 0
        else:
            raise ValueError(f"unknown op {op!r}")

        self.add(op, trace_address, step, returned)
        self.actual_returns.append(returned)
        return returned

    def run(self, trace: list[dict]) -> dict:
        """Execute all steps. Timing boundary EXCLUDES init and workload gen."""
        import gc
        import time

        gc.collect()
        t0 = time.perf_counter()
        for rec in trace:
            self.execute_step(rec)
        self.execute_time_s = time.perf_counter() - t0
        return self.summary()

    def export(self) -> list[TraceRow]:
        """Return the complete immutable history; time counted separately."""
        import time

        t0 = time.perf_counter()
        rows = list(self.history)
        self.export_time_s += time.perf_counter() - t0
        return rows

    def export_fields(self) -> list[tuple]:
        return [tuple(r) for r in self.export()]

    def invariant(self) -> tuple[bool, str]:
        return self._invariant()

    def summary(self) -> dict:
        d = self.c.as_dict()
        d.update(
            {
                "history_rows": len(self.history),
                "fetch_time_s": self.fetch_time_s,
                "query_time_s": self.query_time_s,
                "update_time_s": self.update_time_s,
                "append_time_s": self.append_time_s,
                "export_time_s": self.export_time_s,
                "execute_time_s": self.execute_time_s,
                "end_to_end_s": self.execute_time_s + self.export_time_s,
            }
        )
        return d
