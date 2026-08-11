#!/usr/bin/env python3
"""EFO `ledger.projected_tasks` at main (5694ab45): the reconstruction every
integrity check compares against.

`get_task`, `list_tasks` and `_audit_projections` all decide whether a
projection is trustworthy by comparing it with `projected_tasks()`. That makes
this eleven-line fold the reference the whole integrity story rests on, so it
is worth asking what it does with input the API cannot produce - and, more
importantly, whether anything can reach it without verifying the chain first.

Section A is the positive control. Section B enumerates every caller from the
source and FAILS the run on any caller this probe has not adjudicated, so a
future call site cannot slip past unread.

    python3 probe_projected_tasks.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.ledger import Ledger  # noqa: E402
from evidence_orchestrator.util import canonical_json  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-proj-"))
SOURCE = Path("/tmp/efo-prov/src/evidence_orchestrator")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def attempt(name: str, expected: str, fn) -> None:
    try:
        value = fn()
        check(name, expected, f"accepted ({value})")
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - a real workspace ##########")
ws = Workspace.initialize(ROOT / "ws", name="projection-probe",
                          orchestrator="antigravity",
                          preset="antigravity-codex-claude")
ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                         control_principal="anthropic",
                         model_family="anthropic-claude")
for tid in ("T1", "T2"):
    ws.create_task(actor="antigravity", task_id=tid, title=tid,
                   description="work", owner="claude")
ws.claim(actor="claude", task_id="T1")

projected = ws.ledger.projected_tasks()
check("the fold reconstructs every task", "['T1', 'T2']",
      str(sorted(projected)))
on_disk = json.loads((ws.tasks_dir / "T1.json").read_text(encoding="utf-8"))
comparable = {key: value for key, value in on_disk.items()
              if key != "last_event_hash"}
check("  and matches the on-disk projection byte for byte", "match: True",
      f"match: {comparable == projected['T1']}")
check("  the latest snapshot wins, not the first", "state=claimed",
      f"state={projected['T1']['state']}")

# ---------------------------------------------------------------- B
print("\n########## B. every caller, enumerated from the source ##########")
print("  projected_tasks() never verifies the chain itself - it calls read(),")
print("  which only refuses malformed JSON. So the question is whether every")
print("  caller verifies first.")
text = (SOURCE / "workspace.py").read_text(encoding="utf-8").splitlines()
ledger_text = (SOURCE / "ledger.py").read_text(encoding="utf-8")
check("projected_tasks itself calls verify", "verify present: False",
      f"verify present: "
      f"{'verify' in ledger_text.split('def projected_tasks')[1]}")

ADJUDICATED = {
    468: "get_task - self.ledger.verify() at workspace.py:467",
    489: "list_tasks - self.ledger.verify() at workspace.py:488",
    1498: "_audit_projections - ledger_status = self.ledger.verify() at 1497",
}
callers = [index + 1 for index, line in enumerate(text)
           if "projected_tasks()" in line]
print(f"  call sites found: {callers}")
uncovered = 0
for line_number in callers:
    window = "\n".join(text[max(0, line_number - 6):line_number])
    verifies = "self.ledger.verify()" in window
    note = ADJUDICATED.get(line_number)
    if note is None:
        uncovered += 1
        print(f"        !! workspace.py:{line_number}  NOT ADJUDICATED")
        continue
    print(f"        workspace.py:{line_number}  verify() within 5 lines above: "
          f"{verifies}")
    print(f"                     -> {note}")
check("every call site is adjudicated", "uncovered: 0", f"uncovered: {uncovered}")
check("  and every one of them verifies first", "all verify: True",
      "all verify: " + str(all(
          "self.ledger.verify()" in "\n".join(text[max(0, n - 6):n])
          for n in callers)))
others = []
for path in sorted(SOURCE.glob("*.py")):
    if path.name in {"ledger.py", "workspace.py"}:
        continue
    if "projected_tasks" in path.read_text(encoding="utf-8"):
        others.append(path.name)
check("  no other module reaches it", "other modules: []",
      f"other modules: {others}")

# ---------------------------------------------------------------- C
print("\n########## C. what the fold does with input the API cannot make ##########")
print("  These are properties of the function, NOT reachable states: every")
print("  shipped caller verifies the chain first (section B), and forging a")
print("  chain needs the signing key. The events below are written directly.")

KEY = ROOT / "probe.key"
KEY.write_bytes(b"0" * 32)


def crafted(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Write raw events and fold them, bypassing the chain entirely."""
    directory = Path(tempfile.mkdtemp(dir=ROOT))
    path = directory / "events.jsonl"
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False, sort_keys=True)
                  for event in events) + "\n",
        encoding="utf-8")
    ledger = Ledger(path, directory / "lock", KEY)
    return ledger.projected_tasks()


def event(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "sequence": 1, "timestamp": "2026-08-02T00:00:00Z", "actor": "a",
        "action": "task.created", "task_id": "T1",
        "payload": {"task": {"id": "T1", "state": "pending"}},
        "previous_hash": "0" * 64, "event_hash": "x", "signature": "y",
    }
    base.update(over)
    return base


result = crafted([event()])
check("a well-formed event folds", "{'T1': {'id': 'T1', 'state': 'pending'}}",
      str(result))

result = crafted([event(action="something.unknown")])
check("an UNKNOWN action carrying a task payload still folds", "'T1'",
      str(sorted(result)))
print("        -> the fold filters on payload shape, not on the action name.")

result = crafted([event(task_id="T1",
                        payload={"task": {"id": "T2", "state": "verified"}})])
check("task_id and payload.task.id disagreeing", "keyed under 'T1'",
      f"keyed under {list(result)!r} with id="
      f"{result['T1']['id']!r}".replace("['T1']", "'T1'", 1))
print("        -> keyed on the ENVELOPE's task_id, not the snapshot's own id.")

result = crafted([event(task_id=None)])
check("a null task_id is ignored", "{}", str(result))
result = crafted([event(payload={"task": "not a dict"})])
check("a non-dict task payload is ignored", "{}", str(result))
result = crafted([event(payload={})])
check("an event with no task payload is ignored", "{}", str(result))

result = crafted([event(sequence=1, action="task.verified",
                        payload={"task": {"id": "T1", "state": "verified"}})])
check("a task with no task.created still projects", "'state': 'verified'",
      str(result))
print("        -> the fold has no notion of a lifecycle; last write wins.")

# ---------------------------------------------------------------- D
print("\n########## D. does the mismatch survive a real read? ##########")
print("  Section C's id mismatch is the one shape worth chasing, because it")
print("  would put a T2-shaped snapshot under the key T1. Rebuilt here with a")
print("  VALID chain, so get_task actually reaches the comparison.")
directory = Path(tempfile.mkdtemp(dir=ROOT))
ws2 = Workspace.initialize(directory / "ws", name="mismatch",
                           orchestrator="antigravity")
key = (ws2.root / ".efo" / "ledger.key").read_bytes()
lines = ws2.ledger.path.read_text(encoding="utf-8").splitlines()
last = json.loads(lines[-1])
core = {
    "sequence": last["sequence"] + 1,
    "timestamp": "2026-08-02T00:00:00Z",
    "actor": "antigravity",
    "action": "task.created",
    "task_id": "T1",
    "payload": {"task": {"id": "T2", "state": "pending"}},
    "previous_hash": last["event_hash"],
}
event_hash = hashlib.sha256(canonical_json(core)).hexdigest()
signature = hmac.new(key, event_hash.encode("ascii"), hashlib.sha256).hexdigest()
forged = {**core, "event_hash": event_hash, "signature": signature}
ws2.ledger.path.write_text(
    "\n".join(lines) + "\n"
    + json.dumps(forged, ensure_ascii=False, sort_keys=True) + "\n",
    encoding="utf-8")
attempt("the chain still verifies with the mismatched event", "'valid': True",
        ws2.ledger.verify)
check("  and the fold keys it under T1", "id='T2'",
      f"id={ws2.ledger.projected_tasks()['T1']['id']!r}")
attempt("  but get_task refuses it", "Unknown task",
        lambda: ws2.get_task("T1"))
print("        -> no tasks/T1.json exists, so the projection check never")
print("           compares. The mismatch is inert unless a matching file is")
print("           also planted - which is the same filesystem access #9 needs.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
