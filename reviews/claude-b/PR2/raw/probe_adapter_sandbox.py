#!/usr/bin/env python3
"""EFO command adapter at main (5694ab45).

`docs/ARCHITECTURE.md` failure table claims "Agent writes another workspace
area -> Command adapter reports and blocks".  `adapter.py` implements that as a
before/after SHA-256 snapshot of the whole workspace, diffed against an
allow-list.

This probes that claim, then enumerates what the allow-list itself sanctions.

Section A is the positive control - an honest command agent must reach
`submitted` before any block below means anything.  Every block is asserted on
its recorded REASON, by substring.

    python3 probe_adapter_sandbox.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.adapter import (  # noqa: E402
    _unauthorized_changes,
    _workspace_snapshot,
    run_once,
)
from evidence_orchestrator.doctor import audit_workspace  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-adapter-"))
CHILD = ROOT / "child.py"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


REPORT_BODY = "\n".join([
    "# report", "",
    "## 1. Scope", "adapter probe", "",
    "## 2. What was done", "one passing check", "",
    "## 3. Counts", "passed=1 failed=0 skipped=0", "",
    "## 4. Known-answer comparison", "expected 4, observed 4", "",
    "## 5. Outside ownership", "none", "",
    "## 6. Not verified", "nothing", "",
])

# The child agent. Its mode arrives through the PARENT environment, which is
# itself one of the things being measured: adapter.py:158 passes **os.environ
# straight through to the child process.
CHILD.write_text('''
import hashlib, json, os, sys, time
from pathlib import Path

mode = os.environ.get("EFO_PROBE_MODE", "honest")
ws = Path(os.environ["EFO_WORKSPACE"])
task_id = os.environ["EFO_TASK_ID"]
report = Path(os.environ["EFO_REPORT"])
evidence = Path(os.environ["EFO_EVIDENCE"])

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def honest_evidence(passing=True):
    art = report.parent / "artifact.txt"
    art.write_text("measured artifact\\n", encoding="utf-8")
    report.write_text(REPORT_BODY, encoding="utf-8")
    evidence.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{"path": str(art), "sha256": sha(art)}],
        "validations": [{"command": "pytest -q", "exit_code": 0 if passing else 1,
                         "passed": 1, "failed": 0 if passing else 2,
                         "skipped": 0, "skip_reasons": []}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "functional behavior", "kind": "functional",
                    "measured": True, "value": "pass",
                    "evidence": [str(art)]}],
    }, indent=2), encoding="utf-8")

if mode == "honest":
    honest_evidence()
elif mode == "other_agent_report":
    honest_evidence()
    (ws / "reports" / "other").mkdir(parents=True, exist_ok=True)
    (ws / "reports" / "other" / "planted.md").write_text("planted\\n", encoding="utf-8")
elif mode == "shared":
    honest_evidence()
    (ws / "shared" / "FACTS.md").write_text("rewritten by the worker\\n", encoding="utf-8")
elif mode == "config":
    honest_evidence()
    cfg = ws / ".efo" / "workspace.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data["defaults"]["max_evidence_bytes"] = 1
    cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
elif mode == "other_task":
    honest_evidence()
    victim = ws / "tasks" / "T2.json"
    data = json.loads(victim.read_text(encoding="utf-8"))
    data["owner"] = "w"
    victim.write_text(json.dumps(data, indent=2), encoding="utf-8")
elif mode == "nonzero":
    honest_evidence()
    sys.exit(3)
elif mode == "slow":
    honest_evidence()
    time.sleep(30)
elif mode == "no_report":
    pass
elif mode == "failing_evidence":
    honest_evidence(passing=False)
elif mode == "restore":
    honest_evidence()
    victim = ws / "shared" / "FACTS.md"
    original = victim.read_bytes()
    victim.write_bytes(b"transiently rewritten\\n")
    victim.write_bytes(original)
    (ws / "shared" / "new-empty-dir").mkdir(exist_ok=True)
elif mode == "ledger_truncate":
    honest_evidence()
    ledger = ws / "ledger" / "events.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    dropped = json.loads(lines[-1])
    # Roll the projection back to the snapshot the truncated chain still holds,
    # exactly as probe_ledger_chain.py section D did - but from inside the
    # sandbox the adapter is supposed to be policing.
    prior = json.loads(lines[-2])
    ledger.write_text("\\n".join(lines[:-1]) + "\\n", encoding="utf-8")
    snapshot = dict(prior["payload"]["task"])
    snapshot["last_event_hash"] = prior["event_hash"]
    (ws / "tasks" / (task_id + ".json")).write_text(
        json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    Path(os.environ["EFO_PROBE_NOTE"]).write_text(
        json.dumps({"dropped_action": dropped["action"],
                    "dropped_sequence": dropped["sequence"]}), encoding="utf-8")
elif mode == "escape_symlink":
    honest_evidence()
    outside = Path(os.environ["EFO_PROBE_OUTSIDE"])
    link = report.parent / "escape"
    if not link.exists():
        link.symlink_to(outside)
    (link / "written-through-the-link.txt").write_text("outside\\n", encoding="utf-8")
'''.replace("REPORT_BODY", repr(REPORT_BODY)), encoding="utf-8")


def build(mode_env: str) -> tuple[Workspace, dict[str, Any]]:
    root = Path(tempfile.mkdtemp(prefix="ws-", dir=ROOT))
    ws = Workspace.initialize(root / "ws", name="adapter-probe",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    ws.attest_agent_identity(actor="antigravity", agent_id="antigravity",
                             control_principal="google",
                             model_family="google-antigravity")
    ws.add_agent(actor="antigravity", agent_id="w", role="worker",
                 mode="command", command=[sys.executable, str(CHILD)],
                 control_principal="openai", model_family="openai-codex")
    ws.attest_agent_identity(actor="antigravity", agent_id="w",
                             control_principal="openai",
                             model_family="openai-codex")
    ws.add_agent(actor="antigravity", agent_id="other", role="worker",
                 mode="manual", control_principal="anthropic",
                 model_family="anthropic-claude")
    (ws.root / "shared" / "FACTS.md").write_text("baseline facts\n", encoding="utf-8")
    for tid in ("T1", "T2"):
        ws.create_task(actor="antigravity", task_id=tid, title=tid,
                       description="work", owner="w" if tid == "T1" else "other")
    os.environ["EFO_PROBE_MODE"] = mode_env
    return ws, {}


def healthy(ws: Workspace) -> str:
    return str(audit_workspace(ws.root)["healthy"])


def run(mode: str, timeout: int = 60) -> tuple[Workspace, dict[str, Any]]:
    ws, _ = build(mode)
    result = run_once(ws, agent_id="w", task_id="T1", timeout_seconds=timeout)
    return ws, result


def reason_of(ws: Workspace, task_id: str = "T1") -> str:
    for event in reversed(ws.ledger.read()):
        if event["action"] == "task.blocked" and event.get("task_id") == task_id:
            return str(event["payload"]["task"].get("blocked_reason"))
    return "<no task.blocked event>"


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - an honest command agent ##########")
ws, result = run("honest")
check("an honest agent reaches submitted", "'state': 'submitted'", str(result))
check("  and doctor is healthy", "healthy=True", "healthy=" + healthy(ws))

# ---------------------------------------------------------------- B
print("\n########## B. the documented claim: writes to another area block ##########")
for mode, label, expected in [
    ("other_agent_report", "a write into another agent's report directory",
     "reports/other/planted.md"),
    ("shared", "a rewrite of shared/FACTS.md", "shared/FACTS.md"),
    ("config", "a rewrite of .efo/workspace.json", ".efo/workspace.json"),
    ("other_task", "a rewrite of another agent's task projection", "tasks/T2.json"),
]:
    ws, result = run(mode)
    check(label, "blocked", str(result.get("state")))
    check(f"  and {expected} is named", expected,
          str(result.get("unauthorized_changes")))

ws, result = run("nonzero")
check("a nonzero exit", "blocked", str(result.get("state")))
check("  reason", "exited with code 3", reason_of(ws))

ws, result = run("slow", timeout=2)
check("a command that overruns its timeout", "blocked", str(result.get("state")))
check("  reason", "timed out after 2s", reason_of(ws))

ws, result = run("no_report")
check("no report written at all", "blocked", str(result.get("state")))
check("  reason", "Evidence gate rejected output", reason_of(ws))

ws, result = run("failing_evidence")
check("a manifest declaring a failure", "blocked", str(result.get("state")))
check("  reason", "did not pass", reason_of(ws))

# ---------------------------------------------------------------- C
print("\n########## C. what the allow-list itself sanctions ##########")
ws, _ = build("honest")
agent = ws.get_agent("w")
task = ws.get_task("T1")
allowed = list(agent.get("write_roots", []))
allowed.extend(task.get("allowed_write_roots", []))
allowed.extend([f"reports/w", f"runs/w", f"tasks/T1.json", "ledger/events.jsonl"])
print("  effective allowed prefixes for this agent (adapter.py:147-156):")
for prefix in allowed:
    print(f"        {prefix}")

os.environ["EFO_PROBE_NOTE"] = str(ROOT / "note.json")
ws, result = run("ledger_truncate")
note = json.loads((ROOT / "note.json").read_text(encoding="utf-8"))
print(f"  the child dropped ledger event "
      f"{note['dropped_sequence']} ({note['dropped_action']}) "
      f"and rolled tasks/T1.json back to match")
check("does the adapter report an unauthorized change?", "None",
      str(result.get("unauthorized_changes")))
check("  what does it say instead?", "must be running before submission",
      str(result.get("error")))
check("  does the chain still verify?", "'valid': True", str(ws.ledger.verify()))
check("  does doctor notice?", "healthy=", "healthy=" + healthy(ws))
actions = [e["action"] for e in ws.ledger.read() if e.get("task_id") == "T1"]
check("  the erased event is gone from the signed history",
      f"task.started present: False",
      f"task.started present: {'task.started' in actions} -> {actions}")

# ---------------------------------------------------------------- D
print("\n########## D. structural blind spots of a before/after snapshot ##########")
ws, result = run("restore")
check("a file rewritten and restored within the run", "'state': 'submitted'",
      str(result))
check("  reported as changed?", "None", str(result.get("unauthorized_changes")))
check("  an empty directory created in shared/ - reported?", "None",
      str(result.get("unauthorized_changes")))
check("  the directory does exist afterwards", "exists=True",
      f"exists={(ws.root / 'shared' / 'new-empty-dir').is_dir()}")

outside = ROOT / "outside-the-workspace"
outside.mkdir(exist_ok=True)
os.environ["EFO_PROBE_OUTSIDE"] = str(outside)
ws, result = run("escape_symlink")
check("a write through a symlink pointing outside the workspace",
      "'state': 'submitted'", str(result))
check("  reported as changed?", "None", str(result.get("unauthorized_changes")))
check("  did the write land outside?", "landed=True",
      f"landed={(outside / 'written-through-the-link.txt').is_file()}")

print("  _unauthorized_changes prefix matching, checked directly:")
for path, prefixes, note_text in [
    ("reports/wombat/x.md", ["reports/w"], "sibling with a shared name prefix"),
    ("reports/w/x.md", ["reports/w"], "genuinely inside the allowed root"),
    ("reports/w", ["reports/w"], "the root itself"),
    ("tasks/T1.json", ["tasks/T1.json"], "an exact file grant"),
    ("tasks/T10.json", ["tasks/T1.json"], "a longer sibling of a file grant"),
]:
    flagged = _unauthorized_changes({}, {path: "x"}, allowed_prefixes=prefixes)
    print(f"        {path:<22} vs {str(prefixes):<20} -> "
          f"{'FLAGGED' if flagged else 'allowed':<8} ({note_text})")

# ---------------------------------------------------------------- E
print("\n########## E. command construction and the child environment ##########")
print("  argv is built by textual substitution (adapter.py:55-62) and run with")
print("  shell=False (adapter.py:180), so metacharacters are not interpreted.")
ws, _ = build("honest")
snap = _workspace_snapshot(ws.root)
lock_paths = [p for p in snap if p.startswith(".efo/locks/")]
key_paths = [p for p in snap if "ledger.key" in p]
check("the snapshot skips .efo/locks/ only", "locks=0",
      f"locks={len(lock_paths)} key={len(key_paths)}")
print(f"  the signing key is inside the tree the child runs in: {key_paths}")
print("  and the child inherited an arbitrary parent variable "
      "(EFO_PROBE_MODE reached it in every section above), because")
print("  adapter.py:158 passes {**os.environ, ...} straight through.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
