#!/usr/bin/env python3
"""EFO `monitor/collector.py` at main (5694ab45): what reaches a public snapshot.

README.md:359-363 makes a specific, testable promise about the SSH collector:

    "Public snapshots omit passwords, secrets, environment variables, command
     lines, PIDs, GPU UUIDs, ledger signatures, hashes, and event payloads.
     Activity history contains only event time, sequence, actor alias,
     transition label, task ID, and task title."

That list is the standard applied here. The separate sentence at README.md:369
("Local collection sends no hostname...") sits in the Windows-PC-panel
paragraph and is NOT applied to this collector - `collect_system` does emit
`socket.gethostname()`, and that is measured below as an observation, not
scored against a claim it was not making.

Every marker is a unique token planted in one input; the whole snapshot is
serialized and searched for it. Section A is the positive control: the markers
that are SUPPOSED to appear must appear, or a clean scan proves nothing.

nvidia-smi and docker are not present in this container. Their output is
served from recorded fixtures through `run_command`; the real binaries were NOT
executed. The EFO half runs the real CLI against a real workspace.

    python3 probe_collector_redaction.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
sys.path.insert(0, "/tmp/efo-prov")
# The collector shells out; the child needs the package on its own path.
os.environ["PYTHONPATH"] = "/tmp/efo-prov/src"
from evidence_orchestrator.workspace import Workspace  # noqa: E402
from monitor import collector  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-collector-"))

# Unique markers: each appears in exactly one input.
M_UUID = "GPU-MARKERUUID0000-1111-2222-333344445555"
M_PID = "918273645"
M_CMDLINE = "python train.py --api-key=MARKERCMDLINE"
M_CONTAINER = "cts-trainer-MARKERNAME"
M_GPUNAME = "NVIDIA MARKERGPU A100"
M_TASKDESC = "MARKERDESC api_key=AKIA1234567890EXAMPLE"
M_TASKTITLE = "MARKERTITLE train the model"
M_BLOCKED = "/abs/path/MARKERBLOCKED/run.sh"
M_STDERR = "MARKERSTDERR /home/operator/.config/efo/ingest-secret"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


REAL_RUN = collector.run_command
FAIL_NVIDIA = False


def stub_run(args, timeout=12.0):
    """Serve recorded nvidia-smi/docker output; run everything else for real."""
    argv = list(args)
    program = argv[0]
    if program == "nvidia-smi":
        if FAIL_NVIDIA:
            return collector.CommandResult(1, "", M_STDERR)
        if any("query-compute-apps" in item for item in argv):
            return collector.CommandResult(
                0, f"{M_UUID}, {M_PID}, 4096\n", "")
        return collector.CommandResult(
            0,
            f"0, {M_UUID}, {M_GPUNAME}, 91, 40960, 81920, 71, 310.5\n",
            "")
    if program == "docker":
        if argv[1] == "ps":
            return collector.CommandResult(0, json.dumps({
                "ID": "abc123def456",
                "Names": M_CONTAINER,
                "Status": "Up 3 hours",
                "Command": M_CMDLINE,
                "Image": "pytorch/pytorch:latest",
            }) + "\n", "")
        if argv[1] == "top":
            return collector.CommandResult(0, f"PID\n{M_PID}\n", "")
        if argv[1] == "inspect":
            return collector.CommandResult(0, json.dumps([{
                "HostConfig": {"DeviceRequests": [
                    {"DeviceIDs": ["0"]}]},
                "Config": {"Cmd": [M_CMDLINE]},
            }]) + "\n", "")
        if argv[1] == "logs":
            return collector.CommandResult(
                0, f"loading {M_CMDLINE}\n 45%|####      | 45/100 [00:10<00:12, 4.5it/s]\n",
                "")
    return REAL_RUN(args, timeout)


collector.run_command = stub_run


def build_workspace() -> Path:
    root = ROOT / "ws"
    ws = Workspace.initialize(root, name="collector-probe",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                             control_principal="anthropic",
                             model_family="anthropic-claude")
    ws.create_task(actor="antigravity", task_id="T1", title=M_TASKTITLE,
                   description=M_TASKDESC, owner="claude")
    claim = ws.claim(actor="claude", task_id="T1")
    ws.block(actor="claude", task_id="T1",
             lease_token=claim["lease_token"],
             reason=f"Evidence gate rejected output: Report does not exist: {M_BLOCKED}")
    return root


WS = build_workspace()
CONFIG: dict[str, Any] = {
    "efo_workspace": str(WS),
    "efo_command": [sys.executable, "-m", "evidence_orchestrator"],
    "history_file": str(ROOT / "history.json"),
    "disk_path": "/",
    "workspace": {"name": "collector probe"},
}


def snapshot() -> tuple[dict[str, Any], str]:
    value = collector.collect_snapshot(CONFIG)
    return value, json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - the markers that SHOULD appear ##########")
snap, blob = snapshot()
for label, marker in [("the GPU name", M_GPUNAME),
                      ("the task title", "MARKERTITLE"),
                      ("the container name, as a project label", "MARKERNAME"),
                      ("the ledger event stream, as activity", "task.created")]:
    check(f"{label} reaches the snapshot", f"{marker} present: True",
          f"{marker} present: {marker in blob}")
print(f"        gpus={len(snap['gpus'])} tasks={len(snap['tasks'])} "
      f"activity={len(snap['activity'])} alerts={len(snap['alerts'])}")

# ---------------------------------------------------------------- B
print("\n########## B. the documented omission list ##########")
print("  README.md:359-361 - each marker planted in exactly one input.")
for label, marker in [
    ("GPU UUIDs", M_UUID),
    ("PIDs", M_PID),
    ("command lines (docker ps Command / inspect Cmd / logs)", "MARKERCMDLINE"),
    ("a credential in a task description", "MARKERDESC"),
    ("a credential value in a task description", "AKIA1234567890EXAMPLE"),
    ("an absolute path in a blocked_reason", "MARKERBLOCKED"),
]:
    check(f"{label} absent", f"{marker} present: False",
          f"{marker} present: {marker in blob}")

print("  ledger signatures, hashes and event payloads:")
raw_ledger = (WS / "ledger" / "events.jsonl").read_text(encoding="utf-8")
first = json.loads(raw_ledger.splitlines()[0])
for label, value in [
    ("signature", first["signature"]),
    ("event_hash", first["event_hash"]),
]:
    check(f"  the first event's {label} is absent",
          f"{label} present: False", f"{label} present: {value in blob}")

# ---------------------------------------------------------------- C
print("\n########## C. activity history: exactly the documented fields? ##########")
print("  documented: event time, sequence, actor alias, transition label,")
print("              task ID, task title")
keys = sorted({key for entry in snap["activity"] for key in entry})
print(f"  emitted:    {keys}")
check("no field carrying free text beyond the title", "payload present: False",
      f"payload present: {'payload' in keys}")
sample = snap["activity"][0] if snap["activity"] else {}
print(f"  one entry:  {json.dumps(sample, ensure_ascii=False)}")

# ---------------------------------------------------------------- D
print("\n########## D. the one channel that publishes external text ##########")
print("  query_gpus (collector.py:200-209) and collect_efo (1038-1048) put")
print("  subprocess stderr into a public alert via sanitize_label.")
FAIL_NVIDIA = True
snap2, blob2 = snapshot()
FAIL_NVIDIA = False
check("nvidia-smi stderr reaches the published snapshot",
      "MARKERSTDERR present: True",
      f"MARKERSTDERR present: {'MARKERSTDERR' in blob2}")
for alert in snap2["alerts"]:
    if "MARKERSTDERR" in json.dumps(alert, ensure_ascii=False):
        print(f"        {json.dumps(alert, ensure_ascii=False)}")
check("  and the file path inside it survives sanitize_label",
      "/home/operator/.config/efo/ingest-secret present: True",
      "/home/operator/.config/efo/ingest-secret present: "
      f"{'/home/operator/.config/efo/ingest-secret' in blob2}")

print("  what sanitize_label actually removes, checked directly:")
for sample_text in [
    "/home/operator/.ssh/id_ed25519",
    "python train.py --api-key=sk-ant-0123",
    "token=abc; rm -rf /",
    "user@host:/srv/data",
    "$(whoami)`id`",
]:
    print(f"        {sample_text!r:<44} -> "
          f"{collector.sanitize_label(sample_text)!r}")

# ---------------------------------------------------------------- E
print("\n########## E. hostname - measured, against no claim ##########")
print("  README.md:369 'Local collection sends no hostname' sits in the")
print("  Windows-PC-panel paragraph; the collector's own list at 359-361 does")
print("  not name hostname. Recorded, not scored.")
print(f"        system.hostname = {snap['system']['hostname']!r}")
print(f"        source.host     = {snap['source']['host']!r}")
print("        source.host falls back to system.hostname when display_host")
print("        is unset (collector.py:1277-1280).")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
