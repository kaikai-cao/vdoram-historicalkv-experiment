#!/usr/bin/env python3
"""ABA-01: pinned Bubble Sort program representation and CFG.

The instruction list is transcribed from BDS-SDU/vdoram-artifacts @ 10c90d35
CompatCircuit/CollaborativeZkVm/ZkPrograms/Examples/BubbleSortProgramGenerator.cs
L16-L74. PC == instruction index. No upstream code is modified or imported.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace

SOURCE_COMMIT = "10c90d35464620a35ddb1e2c29d2e8725acedd52"
SOURCE_PATH = (
    "CompatCircuit/CollaborativeZkVm/ZkPrograms/Examples/"
    "BubbleSortProgramGenerator.cs"
)
FIELD_PRIME = int(
    "12ab655e9a2ca55660b44d1e5c37b00159aa76fed00000010a11800000000001", 16
)
BIT_SIZE = 253

MEMORY_OPS = frozenset({"Load", "Store"})


@dataclass(frozen=True)
class Instr:
    op: str
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0

    def as_row(self) -> list[object]:
        return [self.op, self.arg0, self.arg1, self.arg2]


@dataclass(frozen=True)
class Program:
    code_name: str
    instrs: tuple[Instr, ...]
    source_commit: str = SOURCE_COMMIT
    source_path: str = SOURCE_PATH

    def canonical_bytes(self) -> bytes:
        payload = {
            "code_name": self.code_name,
            "source_commit": self.source_commit,
            "source_path": self.source_path,
            "instrs": [i.as_row() for i in self.instrs],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()

    def successors(self, pc: int) -> tuple[int, ...]:
        """CFG edges. JumpIfZero has target-on-zero and fallthrough edges."""
        if pc < 0 or pc >= len(self.instrs):
            return ()
        ins = self.instrs[pc]
        if ins.op == "Halt":
            return ()
        if ins.op == "JumpIfZero":
            out = {ins.arg1, pc + 1}
            return tuple(sorted(x for x in out if 0 <= x < len(self.instrs)))
        nxt = pc + 1
        return (nxt,) if nxt < len(self.instrs) else ()

    def memory_pcs(self) -> tuple[int, ...]:
        return tuple(
            pc for pc, i in enumerate(self.instrs) if i.op in MEMORY_OPS
        )

    def writes(self, pc: int) -> frozenset[int]:
        """Register indices written by instruction at pc (conservative)."""
        ins = self.instrs[pc]
        if ins.op in {
            "PublicInput", "PrivateInput", "Move", "Set", "Hash", "Load",
            "Add", "Sub", "Mul", "Inv", "Norm", "And", "Or", "Xor", "Not",
            "LessThan", "RightShift",
        }:
            return frozenset({ins.arg0})
        return frozenset()

    def writers_of(self, reg: int) -> tuple[int, ...]:
        return tuple(pc for pc in range(len(self.instrs)) if reg in self.writes(pc))

    def last_writer_before(self, reg: int, pc: int) -> int | None:
        for i in range(pc - 1, -1, -1):
            if reg in self.writes(i):
                return i
        return None

    def with_instr(self, pc: int, instr: Instr) -> "Program":
        rows = list(self.instrs)
        rows[pc] = instr
        return replace(self, instrs=tuple(rows))


def _s(op: str, a0: int = 0, a1: int = 0, a2: int = 0) -> Instr:
    return Instr(op, a0, a1, a2)


# Transcribed from source_semantics.md section 1 (42 instructions, PC 0..42).
BUBBLE_SORT_INSTRUCTIONS: tuple[Instr, ...] = (
    _s("Set", 15, 1),                 # 0
    _s("PublicInput", 1),             # 1  n -> R1
    _s("Set", 0, 0),                  # 2
    _s("PrivateInput", 2),            # 3
    _s("Store", 2),                   # 4  mem[R0] = R2
    _s("Add", 0, 0, 15),              # 5
    _s("LessThan", 2, 0, 1),          # 6
    _s("Not", 2, 2),                  # 7
    _s("JumpIfZero", 2, 3),           # 8
    _s("Move", 8, 1),                 # 9  R8 = n
    _s("Set", 2, 0),                  # 10
    _s("Set", 6, 0),                  # 11
    _s("Add", 3, 2, 15),              # 12 R3 = R2+1
    _s("LessThan", 4, 3, 1),          # 13
    _s("JumpIfZero", 4, 29),          # 14
    _s("Move", 0, 2),                 # 15
    _s("Load", 4),                    # 16
    _s("Move", 0, 3),                 # 17
    _s("Load", 5),                    # 18
    _s("LessThan", 7, 5, 4),          # 19
    _s("JumpIfZero", 7, 26),          # 20
    _s("Move", 0, 2),                 # 21
    _s("Store", 5),                   # 22
    _s("Move", 0, 3),                 # 23
    _s("Store", 4),                   # 24
    _s("Add", 6, 6, 15),              # 25
    _s("Move", 2, 3),                 # 26
    _s("Set", 0, 0),                  # 27
    _s("JumpIfZero", 0, 12),          # 28
    _s("Set", 0, 0),                  # 29
    _s("LessThan", 0, 0, 6),          # 30
    _s("JumpIfZero", 0, 35),          # 31
    _s("Sub", 1, 1, 15),              # 32 R1 = R1-1
    _s("Set", 0, 0),                  # 33
    _s("JumpIfZero", 0, 10),          # 34
    _s("Set", 0, 0),                  # 35
    _s("Load", 2),                    # 36
    _s("PublicOutput", 2),            # 37
    _s("Add", 0, 0, 15),              # 38
    _s("LessThan", 2, 0, 8),          # 39
    _s("Not", 2, 2),                  # 40
    _s("JumpIfZero", 2, 36),          # 41
    _s("Halt"),                       # 42
)

BUBBLE_SORT = Program("BubbleSort", BUBBLE_SORT_INSTRUCTIONS)
