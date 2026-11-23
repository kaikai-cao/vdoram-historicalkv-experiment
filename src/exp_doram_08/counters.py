#!/usr/bin/env python3
"""New SelectCompose counter semantics (EXP-DORAM-08 Q6).

Old R1 field `selection_operations` counted only the logical selection result.
These counters count the actual select-stage FieldMul work. No old files touched.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class SelectCounters:
    logical_selection_results: int = 0
    select_compose_rows: int = 0
    select_compose_field_mul: int = 0
    e1_read_select_rows: int = 0
    e1_write_select_rows: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def e0_fetch_counters(visible_history_rows: int, matched: bool, columns: int = 1) -> SelectCounters:
    """One E0 Fetch: every visible row enters SelectCompose, matched or not."""
    rows = max(0, int(visible_history_rows))
    return SelectCounters(
        logical_selection_results=1 if matched else 0,
        select_compose_rows=rows,
        select_compose_field_mul=rows * max(0, int(columns)),
    )


def e1_fetch_counters(n: int, in_domain: bool, is_store: bool = False, columns: int = 1) -> SelectCounters:
    """One E1 Fetch: n read-select rows; STORE adds n write-select rows."""
    n = max(0, int(n))
    cols = max(0, int(columns))
    return SelectCounters(
        logical_selection_results=1 if in_domain else 0,
        select_compose_rows=n,
        select_compose_field_mul=n * cols + (n * cols if is_store else 0),
        e1_read_select_rows=n,
        e1_write_select_rows=n if is_store else 0,
    )
