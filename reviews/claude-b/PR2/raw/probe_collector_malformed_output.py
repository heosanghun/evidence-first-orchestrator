#!/usr/bin/env python3
"""What the redaction note fed - and the MALFORMED command output it never did.

Queue item 59, second of the five item 53 left after items 53 and 56. Item 47's
question, asked by hand of `NOTE-collector-redaction-holds.md`: WHAT INPUT CLASS
did its 15 checks feed?

     8  a well-formed fixture carrying SENSITIVE CONTENT, checked absent
     4  a well-formed fixture carrying an expected marker - the controls
     2  a FAILING nvidia-smi (exit 1 with stderr) - the one failure path fed
     1  a shape assertion over the emitted activity entries
    --
    15

Every one is a well-formed `CommandResult`. The CONTENT varies - secrets,
paths, UUIDs - and the SHAPE never does. `monitor/collector.py` parses the
output of external programs, so the class it never fed is the obvious one:
MALFORMED OUTPUT.

Driven, control first:

    good fixture                       snapshot OK, gpus=1        (control)
    nvidia-smi CSV with 3 fields       OK, gpus=0    degrades
    nvidia-smi empty stdout, exit 0    OK, gpus=0    degrades
    nvidia-smi binary garbage          OK, gpus=0    degrades
    docker ps INVALID JSON             OK, gpus=1    degrades
    docker inspect valid JSON OBJECT   AttributeError - CRASHES

FIVE of six degrade. The sixth raises out of `collect_snapshot` entirely, and
the asymmetry is visible in one function: `collector.py:325-327` catches
`json.JSONDecodeError` and nothing else, so a wrong-SHAPED but valid JSON walks
past the guard into `for request in requests: request.get(...)`, where
iterating a dict yields KEYS and `str.get` does not exist.

RECORDED, NOT FILED. The input is `docker inspect --format
'{{json .HostConfig.DeviceRequests}}'`, whose shape is docker's own contract -
a worker with container access cannot change it, so this is outside the
tampered-file threat model, the same standard items 38, 45, 47, 53, 54 and 56
applied. What IS worth recording is the coverage asymmetry: the guard the
author wrote covers the decode error and not the shape.

    python3 probe_collector_malformed_output.py

SCOPE, stated first: 1 note, 15 checks, 6 driven shapes, 1 control.
A MAP with a near miss recorded. `collector redaction is clean` is NOT
retracted.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
sys.path.insert(0, "/tmp/efo-prov")
os.environ["PYTHONPATH"] = "/tmp/efo-prov/src"
from evidence_orchestrator.workspace import Workspace  # noqa: E402
from monitor import collector  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
COMMITTED = REVIEWS / "raw" / "raw-collector-redaction.txt"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item59-")).resolve()


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {subprocess.run(['git', '-C', str(ANCHOR), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()!r}")

labels = [line.split("] ", 1)[1].strip()
          for line in COMMITTED.read_text(encoding="utf-8").splitlines()
          if line.startswith("  [ok]")]
check("  checks in the committed redaction output", "checks: 15",
      f"checks: {len(labels)}")
note = (REVIEWS / "NOTE-collector-redaction-holds.md").read_text(
    encoding="utf-8")
stated = re.search(r"\*\*(\d+) checks, (\d+) unexpected", note)
check("    and the note's headline agrees with the file",
      "stated: 15 / 0", f"stated: {stated.group(1)} / {stated.group(2)}")

# ---------------------------------------------------------------- B
print("\n########## B. the fifteen, classified BY HAND ##########")
CLASS_OF = {
    "the GPU name reaches the snapshot": "control marker",
    "the task title reaches the snapshot": "control marker",
    "the container name, as a project label reaches the snapshot":
        "control marker",
    "the ledger event stream, as activity reaches the snapshot":
        "control marker",
    "GPU UUIDs absent": "sensitive content",
    "PIDs absent": "sensitive content",
    "command lines (docker ps Command / inspect Cmd / logs) absent":
        "sensitive content",
    "a credential in a task description absent": "sensitive content",
    "a credential value in a task description absent": "sensitive content",
    "an absolute path in a blocked_reason absent": "sensitive content",
    "the first event's signature is absent": "sensitive content",
    "the first event's event_hash is absent": "sensitive content",
    "no field carrying free text beyond the title": "shape of the output",
    "nvidia-smi stderr reaches the published snapshot": "a FAILING command",
    "and the file path inside it survives sanitize_label": "a FAILING command",
}
unclassified = [label for label in labels if label not in CLASS_OF]
check("every one of the fifteen is classified - the table is exhaustive",
      "unclassified: []", f"unclassified: {unclassified}")
tally: dict[str, int] = {}
for label in labels:
    tally[CLASS_OF[label]] = tally.get(CLASS_OF[label], 0) + 1
for kind, count in sorted(tally.items(), key=lambda kv: -kv[1]):
    print(f"    {count:>3}  {kind}")
check("  sensitive CONTENT in a well-formed fixture", "sensitive content: 8",
      f"sensitive content: {tally['sensitive content']}")
check("    and exactly one failure path was fed - nvidia-smi exit 1",
      "a FAILING command: 2", f"a FAILING command: {tally['a FAILING command']}")
check("      the classes sum to the whole population", f"sum: {len(labels)}",
      f"sum: {sum(tally.values())}")
print("  Every input is a well-formed CommandResult. The CONTENT varies and")
print("  the SHAPE never does - so for a parser of external program output,")
print("  the un-fed class is MALFORMED OUTPUT.")

# ---------------------------------------------------------------- C
print("\n########## C. DRIVEN - six shapes, control first ##########")
workspace_root = ROOT / "ws"
workspace = Workspace.initialize(workspace_root, name="item59",
                                 orchestrator="antigravity",
                                 preset="antigravity-codex-claude")
workspace.create_task(actor="antigravity", task_id="T1", title="t",
                      description="d", owner="claude")
CONFIG: dict[str, Any] = {
    "efo_workspace": str(workspace_root),
    "efo_command": [sys.executable, "-m", "evidence_orchestrator"],
    "history_file": str(ROOT / "history.json"),
    "disk_path": "/",
    "workspace": {"name": "item59"},
}
REAL_RUN = collector.run_command
MODE = "good"

GOOD_PS = json.dumps({"ID": "abc123", "Names": "c1", "Status": "Up",
                      "Command": "x", "Image": "i"}) + "\n"
GOOD_INSPECT = json.dumps(
    [{"Capabilities": [["gpu"]], "DeviceIDs": ["0"]}]) + "\n"


def stub(args, timeout=12.0):
    argv = list(args)
    program = argv[0]
    if program == "nvidia-smi":
        if MODE == "csv with 3 fields":
            return collector.CommandResult(0, "0, only-two, fields\n", "")
        if MODE == "empty stdout, exit 0":
            return collector.CommandResult(0, "", "")
        if MODE == "binary garbage":
            return collector.CommandResult(0, "\x00� not csv at all\n", "")
        if any("query-compute-apps" in item for item in argv):
            return collector.CommandResult(0, "GPU-x, 1, 4096\n", "")
        return collector.CommandResult(
            0, "0, GPU-x, NVIDIA A100, 91, 40960, 81920, 71, 310.5\n", "")
    if program == "docker":
        if argv[1] == "ps":
            if MODE == "docker ps invalid JSON":
                return collector.CommandResult(0, "{not json\n", "")
            return collector.CommandResult(0, GOOD_PS, "")
        if argv[1] == "top":
            return collector.CommandResult(0, "PID\n1\n", "")
        if argv[1] == "inspect":
            if MODE == "docker inspect a JSON OBJECT":
                return collector.CommandResult(0, '{"a": 1}\n', "")
            return collector.CommandResult(0, GOOD_INSPECT, "")
        if argv[1] == "logs":
            return collector.CommandResult(0, "loading\n", "")
    return REAL_RUN(args, timeout)


collector.run_command = stub
outcomes: dict[str, str] = {}
try:
    for MODE in ("good", "csv with 3 fields", "empty stdout, exit 0",
                 "binary garbage", "docker ps invalid JSON",
                 "docker inspect a JSON OBJECT"):
        try:
            snapshot = collector.collect_snapshot(CONFIG)
            outcomes[MODE] = (f"OK, gpus={len(snapshot['gpus'])}, "
                              f"alerts={len(snapshot['alerts'])}")
        except Exception as exc:  # noqa: BLE001 - a RAISE is the finding
            outcomes[MODE] = f"RAISED {type(exc).__name__}: {exc}"
finally:
    collector.run_command = REAL_RUN
    shutil.rmtree(ROOT, ignore_errors=True)

for mode, outcome in outcomes.items():
    print(f"    {mode:<32}{outcome}")
check("the good fixture snapshots - CONTROL", "OK, gpus=1", outcomes["good"])
check("  a short CSV degrades to zero GPUs, no raise", "OK, gpus=0",
      outcomes["csv with 3 fields"])
check("    an empty stdout degrades", "OK, gpus=0",
      outcomes["empty stdout, exit 0"])
check("      binary garbage degrades", "OK, gpus=0",
      outcomes["binary garbage"])
check("  invalid JSON from docker ps degrades", "OK, gpus=1",
      outcomes["docker ps invalid JSON"])
check("    but a valid JSON OBJECT from docker inspect RAISES",
      "RAISED AttributeError", outcomes["docker inspect a JSON OBJECT"])
check("      five of the six degrade; exactly one escapes", "escapes: 1",
      "escapes: " + str(sum(1 for v in outcomes.values()
                            if v.startswith("RAISED"))))

# ---------------------------------------------------------------- D
print("\n########## D. the asymmetry, in one function ##########")
source = (ANCHOR / "monitor" / "collector.py").read_text(
    encoding="utf-8").splitlines()
for number in (325, 326, 327, 329, 330):
    print(f"    collector.py:{number}  {source[number - 1].strip()}")
check("the guard catches a DECODE error", "except json.JSONDecodeError:",
      source[325])
check("  and nothing else - a wrong-SHAPED valid JSON walks past it",
      "for request in requests:", source[328])
check("    into request.get, where iterating a dict yields KEYS",
      'request.get("Capabilities")', source[329])
print("  A dict is iterable and yields str, and str has no .get - which is")
print("  exactly the AttributeError section C measured.")

# ---------------------------------------------------------------- E
print("\n########## E. the verdict, narrowed and not retracted ##########")
print("  * `monitor/collector.py redaction is clean` STANDS. All 15 checks")
print("    still pass and nothing here contradicts one of them.")
print("  * What is now stated: those 15 fed sensitive CONTENT in a")
print("    well-formed shape, plus one failing command. Malformed SHAPE was")
print("    never fed, and five of six shapes degrade correctly.")
print("  * RECORDED, NOT FILED. The raising input is the output of")
print("    `docker inspect --format '{{json .HostConfig.DeviceRequests}}'`,")
print("    whose shape is docker's own contract. A worker with container")
print("    access cannot change it, so it is outside the tampered-file threat")
print("    model - items 38, 45, 47, 53, 54 and 56 applied the same standard.")
print("  * What IS worth recording is the coverage asymmetry: the author")
print("    guarded the decode error and not the shape, in the same three")
print("    lines.")

print("\n########## F. what this does NOT do ##########")
print("  * It does not retract the clean verdict, and does not re-run the 15.")
print("  * It does not claim six shapes are all the shapes. Timeouts,")
print("    partial reads and a non-zero docker exit were NOT driven - the")
print("    last is already handled at collector.py:322 by inspection, which")
print("    is not the same as being driven, and that is stated.")
print("  * It does not execute nvidia-smi or docker: neither exists in this")
print("    container, and every result above is a recorded fixture served")
print("    through run_command. The EFO half is a real workspace.")
print("  * It does not adjudicate the other four notes item 53 named. FOUR")
print("    remain after this one.")
print("  * No network. The workspace is a tempfile directory, removed above.")
print("  * MEASURED: the 15-label classification and its exhaustiveness, all")
print("    six driven shapes, the control, the three source lines.")
print("    REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("One clean note re-examined by hand and its un-fed input class driven.")
print("Anchor untouched, no `main` write, no issue filed, no verdict")
print("retracted. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
