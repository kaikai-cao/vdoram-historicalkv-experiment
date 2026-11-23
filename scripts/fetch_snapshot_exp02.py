#!/usr/bin/env python3
"""Fetch EXP-DORAM-02 audit source files via GitHub API blobs (avoids truncated pack stream)."""
import json, base64, os, subprocess, sys

REPO = "BDS-SDU/vdoram-artifacts"
PIN = "10c90d35464620a35ddb1e2c29d2e8725acedd52"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREE = os.path.join(BASE, "data", "_tree2.json.tmp")
DEST = os.path.join(BASE, "docs", "exp-doram-02", "source-evidence")

# Suffixes of files needed for the 4-component audit. All resolved against the
# pinned tree; exact paths recorded in each file's header.
WANTED = [
    # select / comparison / equality primitives
    "Gadgets/SelectComposeGadget.cs",
    "Gadgets/SelectComposeOtherwiseGadget.cs",
    "Gadgets/FieldEqualsGadget.cs",
    "Gadgets/FieldLessThanGadget.cs",
    "Gadgets/BitsLessThanGadget.cs",
    "Gadgets/FieldGreaterEqualThanGadget.cs",
    "Gadgets/LowBitGadget.cs",
    "Gadgets/LowBitWithCarryGadget.cs",
    "Gadgets/BoolAndGadget.cs",
    "Gadgets/BitDecompositionGadget.cs",
    # commitment / hash / encryption
    "Gadgets/MimcHashGadget.cs",
    "Gadgets/MimcEncryptGadget.cs",
    # cross-step / cross-session state persistence
    "SharedStorages/IMpcSharedStorage.cs",
    "SharedStorages/IMpcSharedStorageFactory.cs",
    "SharedStorages/MpcSharedStorage.cs",
    "SharedStorages/MpcSharedStorageFactory.cs",
    "SharedStorages/MpcSharedStorageCachedFactory.cs",
    "SharedStorages/IMpcSharedStorageSessionManager.cs",
    "SharedStorages/MpcSharedStorageSessionManager.cs",
    "SharedStorages/DummyMpcSharedStorageSessionManager.cs",
    # preprocessing / share lifecycle
    "BeaverTriples/FieldBeaverTripleShare.cs",
    "EdaBitsKai/EdaBitsKaiShare.cs",
    "DaBitPrioPlus/DaBitPrioPlusShare.cs",
    # MPC executor internals + session lifecycle (may reference storage)
    "Computation/MultiParty/MpcExecutor.cs",
    "Computation/MultiParty/MpcExecutorFactory.cs",
    "Computation/IMpcExecutor.cs",
]

d = json.load(open(TREE, encoding="utf-8"))
bypath = {t["path"]: t for t in d["tree"] if t["type"] == "blob"}
os.makedirs(DEST, exist_ok=True)
ok = 0
for w in WANTED:
    matches = [p for p in bypath if p.endswith(w)]
    if not matches:
        print("WARN not found:", w, file=sys.stderr)
        continue
    for p in matches:
        sha = bypath[p]["sha"]
        url = f"https://api.github.com/repos/{REPO}/git/blobs/{sha}"
        out = subprocess.run(["curl", "-s", "-m", "60", "--retry", "2", url],
                             capture_output=True, text=True)
        try:
            obj = json.loads(out.stdout)
            content = base64.b64decode(obj["content"]).decode("utf-8")
        except Exception as e:
            print("FAIL", p, str(e)[:80], file=sys.stderr)
            continue
        dest = os.path.join(DEST, p.replace("/", "__"))
        with open(dest, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"// SOURCE: {REPO} @ {PIN}\n// PATH: {p}\n// BLOB SHA: {sha}\n\n")
            f.write(content)
        ok += 1
        print("OK", p, f"({len(content.splitlines())} lines)")
print(f"\nFetched {ok} files -> {DEST}")
