#!/usr/bin/env python3
"""Fetch pinned VDORAM artifact source files via GitHub API blobs (avoids truncated large git stream)."""
import json, base64, os, subprocess, sys

REPO = "BDS-SDU/vdoram-artifacts"
PIN = "10c90d35464620a35ddb1e2c29d2e8725acedd52"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE = os.path.join(BASE, "data", "_tree.json.tmp")
SNAP = os.path.join(BASE, "docs", "source-snapshot")

WANTED_SUFFIX = [
    "Computation/IMpcExecutorFactory.cs",
    "Computation/IMpcExecutor.cs",
    "Computation/MultiParty/MpcExecutorFactory.cs",
    "Computation/MultiParty/MpcExecutor.cs",
    "ZkPrograms/ZkProgramExecutor.cs",
    "ZkPrograms/ZkProgram.cs",
    "ZkPrograms/ZkProgramExecuteResult.cs",
    "ZkPrograms/ZkProgramInstance.cs",
    "ZkPrograms/ZkProgramOpcode.cs",
    "ZkVmCircuits/MemoryTraceFetchCircuitBoardGenerator.cs",
    "ZkVmCircuits/MemoryTraceProveCircuitBoardGenerator.cs",
    "ZkVmCircuits/MemoryTraceSortCircuitBoardGenerator.cs",
    "ZkVmCircuits/MemoryTraceSortInnerLoopCircuitBoardGenerator.cs",
    "ZkVmCircuits/ZkVmExecutorCircuitBoardGenerator.cs",
    "ZkVmCircuits/ZkVmOpType.cs",
    "ZkVmCircuits/MagicNumber.cs",
    "ZkPrograms/Examples/BubbleSortProgramGenerator.cs",
]

d = json.load(open(TREE, encoding="utf-8"))
tree = d["tree"]
bypath = {t["path"]: t for t in tree if t["type"] == "blob"}

selected = []
for w in WANTED_SUFFIX:
    matches = [p for p in bypath if p.endswith(w)]
    if not matches:
        print("WARN not found:", w, file=sys.stderr)
    for p in matches:
        selected.append(p)

os.makedirs(SNAP, exist_ok=True)
ok, fail = 0, 0
for p in selected:
    sha = bypath[p]["sha"]
    url = f"https://api.github.com/repos/{REPO}/git/blobs/{sha}"
    out = subprocess.run(["curl", "-s", "-m", "60", "--retry", "2", url],
                         capture_output=True, text=True)
    try:
        obj = json.loads(out.stdout)
        content = base64.b64decode(obj["content"]).decode("utf-8")
    except Exception as e:
        print("FAIL", p, str(e)[:80], file=sys.stderr)
        fail += 1
        continue
    dest = os.path.join(SNAP, p.replace("/", "__"))
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"// SOURCE: {REPO} @ {PIN}\n// PATH: {p}\n// BLOB SHA: {sha}\n\n")
        f.write(content)
    ok += 1
    print("OK", p)

print(f"\nFetched {ok} files, {fail} failed -> {SNAP}")
