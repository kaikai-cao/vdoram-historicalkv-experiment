#!/usr/bin/env python3
"""Independent oracle: ground-truth memory semantics for the unified trace.

Computes the expected Load return values with a plain dictionary, WITHOUT any
historical scan and WITHOUT consulting E0/E1. Used only after execution to score
correctness (task §三: value is not an input to the implementations).
"""

from __future__ import annotations

DUMMY_ADDR = (1 << 32) - 1


class Oracle:
    def __init__(self) -> None:
        self.state: dict[int, int] = {}
        self.expected_returns: list[int] = []

    def execute_step(self, op: str, address: int, value, step: int) -> int:
        # Memory state is keyed by the trace address (out_trace_mem_addr):
        # for LOAD/STORE it equals reg0 = the actual memory address; NOOP does
        # not touch state. This matches how E0/E1 replay_state key historical rows.
        if op == "NOOP":
            ret = 0
        elif op == "LOAD":
            ret = self.state.get(address, 0)
        else:
            ret = int(value)
            self.state[address] = ret
        self.expected_returns.append(ret)
        return ret

    def run(self, trace: list[dict]) -> list[int]:
        for rec in trace:
            # R1 traces carry trace_address for the memory key; legacy traces
            # use the single `address` field.
            addr = rec.get("trace_address", rec.get("address"))
            self.execute_step(rec["op"], addr, rec.get("value"), rec["step"])
        return self.expected_returns

    def final_state(self) -> dict[int, int]:
        return dict(self.state)


def expected_returns(trace: list[dict]) -> list[int]:
    return Oracle().run(trace)
