#!/usr/bin/env python3
"""E0-EarlyExit -- READ-ONLY adapter over the untouched EXP-DORAM-07 E0.

Per task 4.1: keep the original early-exit behaviour, reuse the original
implementation directly (no second copy of its logic), and treat it ONLY as a
plain-text reference -- NOT as the VDORAM Fetch circuit baseline.

The inner object is src.exp_doram_07.historical_kv.HistoricalKVLinearScan,
unchanged. This module only translates its interface/counters into the uniform
R1 shape. It is a NEW file; no original file is modified.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.exp_doram_07.historical_kv import HistoricalKVLinearScan as _OriginalE0  # noqa: E402

from .models import Counters  # noqa: E402


class E0EarlyExitAdapter:
    """Uniform R1 interface delegating to the original early-exit E0.

    Counter translation (original -> R1):
      history_rows_scanned -> history_rows_scanned
      equality_checks      -> history_equality_checks  (all are history checks)
      selection_operations-> selection_operations
      update_operations    -> update_operations (0 for E0)
      history_append_operations -> history_append_operations
      fetch_count/query_count/update_count unchanged
      shadow_* counters = 0 (E0 has no shadow table)

    Timing note: the original model does not split fetch vs query time; its
    ``query_time_s`` is the fetch time. We map it to fetch_time_s and mirror it
    into query_time_s, and mark execute/end-to-end from the original total.
    """

    def __init__(self, n: int | None = None) -> None:
        self._inner = _OriginalE0(n=n)
        self.n = n
        self.c = Counters()

    # -- uniform operations (delegate, do not reimplement) --------------
    def fetch(self, address: int) -> int:
        return self._inner.fetch(address)

    def query(self, address: int) -> int:
        return self._inner.query(address)

    def add(self, op: str, trace_address: int, step: int, returned_value: int) -> None:
        return self._inner.add(op, trace_address, step, returned_value)

    def execute_step(self, rec: dict) -> int:
        return self._inner.execute_step(rec)

    def export(self):
        return self._inner.export()

    def export_fields(self) -> list[tuple]:
        return self._inner.export_fields()

    def run(self, trace: list[dict]) -> dict:
        """Run original model, then translate its summary into R1 counters."""
        inner_summary = self._inner.run(trace)
        o = self._inner.c
        self.c = Counters(
            history_rows_scanned=o.history_rows_scanned,
            history_equality_checks=o.equality_checks,
            shadow_slots_scanned=0,
            shadow_equality_checks=0,
            selection_operations=o.selection_operations,
            update_operations=o.update_operations,
            history_append_operations=o.history_append_operations,
            fetch_count=o.fetch_count,
            query_count=o.query_count,
            update_count=o.update_count,
        )
        # translate timing from original buckets
        execute = float(inner_summary.get("total_time_s", 0.0))
        export = float(self._inner.export_time_s)
        d = self.c.as_dict()
        d.update(
            {
                "history_rows": len(self._inner.history),
                "fetch_time_s": float(self._inner.query_time_s),
                "query_time_s": float(self._inner.query_time_s),
                "update_time_s": float(self._inner.update_time_s),
                "append_time_s": float(self._inner.append_time_s),
                "export_time_s": export,
                "execute_time_s": execute,
                "end_to_end_s": execute + export,
            }
        )
        self._last_summary = d
        return d

    def summary(self) -> dict:
        return getattr(self, "_last_summary", self.c.as_dict())

    def invariant(self) -> tuple[bool, str]:
        return True, "n/a (E0 has no shadow state)"

    @property
    def history(self):
        return self._inner.history

    @property
    def actual_returns(self):
        return self._inner.actual_returns
