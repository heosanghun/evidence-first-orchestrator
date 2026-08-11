#!/usr/bin/env python3
"""EFO `doctor` at main (5694ab45): what the one shipped health command covers.

`efo doctor` is the only workspace-wide health command in the CLI. README.md:381
lists it under "Recovery and audit" with no enumerated scope, so this does not
treat every gap as a defect - it measures the boundary, and then asks one
question that is inside doctor's own scope: what happens when an operator
follows the repair path doctor points at.

Section A is the positive control.  Every verdict is asserted by substring.

    python3 probe_doctor_coverage.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.doctor import _scan_secrets, audit_workspace  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-doctor-"))


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


def build(**task_kwargs: Any) -> Workspace:
    root = Path(tempfile.mkdtemp(prefix="ws-", dir=ROOT))
    ws = Workspace.initialize(root / "ws", name="doctor-probe",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    ws.attest_agent_identity(actor="antigravity", agent_id="antigravity",
                             control_principal="google",
                             model_family="google-antigravity")
    ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                             control_principal="anthropic",
                             model_family="anthropic-claude")
    kwargs: dict[str, Any] = {
        "actor": "antigravity", "task_id": "T1", "title": "T1",
        "description": "work", "owner": "claude",
    }
    kwargs.update(task_kwargs)
    ws.create_task(**kwargs)
    return ws


def report(ws: Workspace) -> dict[str, Any]:
    return audit_workspace(ws.root)


def verdict(ws: Workspace) -> str:
    result = report(ws)
    parts = [f"healthy={result['healthy']}"]
    if "error" in result:
        parts.append(f"error={result['error']}")
    checks = result.get("checks", {})
    if checks.get("integrity", {}).get("mismatches"):
        parts.append(f"mismatches={checks['integrity']['mismatches']}")
    if checks.get("expired_leases"):
        parts.append(f"expired={checks['expired_leases']}")
    if checks.get("secret_findings"):
        parts.append(f"secrets={[f['key'] for f in checks['secret_findings']]}")
    return "  ".join(parts)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
ws = build()
check("a clean workspace is healthy", "healthy=True", verdict(ws))

ws = build(description="deploy with api_key=AKIA1234567890EXAMPLE and go")
check("a credential planted in a task description is found",
      "healthy=False", verdict(ws))

# ---------------------------------------------------------------- B
print("\n########## B. doctor's own checks all fire ##########")
ws = build()
path = ws.tasks_dir / "T1.json"
data = json.loads(path.read_text(encoding="utf-8"))
data["title"] = "quietly edited"
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
check("a projection edited on disk", "projection differs from ledger", verdict(ws))

ws = build()
(ws.tasks_dir / "T1.json").unlink()
check("a projection deleted", "projection missing", verdict(ws))

ws = build()
lease = ws.claim(actor="claude", task_id="T1", lease_seconds=10)
time.sleep(11)
check("an expired lease", "expired=['T1']", verdict(ws))

ws = build()
shutil.rmtree(ws.reports_dir / "claude")
check("a missing agent report directory", "healthy=False", verdict(ws))

# ---------------------------------------------------------------- C
print("\n########## C. the secret scanner: which files, which shapes ##########")
SECRET = "api_key=AKIA1234567890EXAMPLE"
print("  doctor.py:196-201 points the scanner at the config, agents/*.json and")
print("  tasks/*.json. Those three are ledger-bound, so the credential has to")
print("  be planted through the API, not by editing the file.")

probe = build(description=f"work {SECRET}")
found = report(probe)["checks"].get("secret_findings", [])
print(f"        tasks/T1.json    via create_task(description=...)  -> "
      f"{'SCANNED' if found else 'not scanned'}")

root = Path(tempfile.mkdtemp(prefix="ws-", dir=ROOT))
named = Workspace.initialize(root / "ws", name=f"deploy {SECRET}",
                             orchestrator="antigravity")
found = report(named)["checks"].get("secret_findings", [])
print(f"        .efo/workspace.json  via initialize(name=...)      -> "
      f"{'SCANNED' if found else 'not scanned'}")

probe = build()
agent_file = probe.agents_dir / "claude.json"
print(f"        agents/claude.json   no free-text field is reachable through")
print(f"                             the API; the scanner itself would find it:")
planted = ROOT / "agent-copy.json"
payload = json.loads(agent_file.read_text(encoding="utf-8"))
payload["note"] = SECRET
planted.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"                             _scan_secrets -> "
      f"{[f['key'] for f in _scan_secrets(planted)]}")

print("  the paths the scanner is NOT pointed at, planted directly:")
probe = build()
elsewhere = {
    "shared/FACTS.md": probe.root / "shared" / "FACTS.md",
    "reports/claude/notes.md": probe.reports_dir / "claude" / "notes.md",
    "runs/claude/stdout.txt": probe.runs_dir / "claude" / "stdout.txt",
    "submissions/T1/bundle.json": probe.submissions_dir / "T1" / "bundle.json",
    "archive/T1.json": probe.archive_dir / "T1.json",
}
for label, target in elsewhere.items():
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"note {SECRET}\n", encoding="utf-8")
found = report(probe)["checks"].get("secret_findings", [])
for label, target in elsewhere.items():
    hit = any(str(target) == f["path"] for f in found)
    direct = bool(_scan_secrets(target))
    print(f"        {label:<26} doctor: {'SCANNED' if hit else 'not scanned':<11}"
          f" scanner alone would match: {direct}")

print("  and the shapes it matches, checked against SECRET_RE directly:")
sample = ROOT / "shapes.txt"
shapes = [
    "api_key=AKIA1234567890EXAMPLE",
    "password: hunter2",
    "token = ghp_0123456789abcdefghij",
    "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY",
    "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc",
    "ghp_0123456789abcdefghijklmnopqrstuvwxyzAB",
    "sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
]
sample.write_text("\n".join(shapes) + "\n", encoding="utf-8")
hits = {f["line"] for f in _scan_secrets(sample)}
for index, shape in enumerate(shapes, start=1):
    label = shape if len(shape) <= 52 else shape[:49] + "..."
    print(f"        {'MATCHED ' if index in hits else 'missed  '} {label}")

print("  the underscore cases are the common ones. End to end, through the")
print("  API, in the one place doctor does scan:")
for name in ("AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN", "OPENAI_API_KEY",
             "DB_PASSWORD"):
    probe = build(description=f"export {name}=AKIA1234567890EXAMPLE")
    result = report(probe)
    found = result["checks"].get("secret_findings", [])
    # Recorded as measured, not as a harness failure: the divergence from what
    # an operator would expect IS the finding, and belongs in the write-up.
    check(f"  {name} in a task description is NOT reported",
          "healthy=True  secrets=[]",
          f"healthy={result['healthy']}  secrets={[f['key'] for f in found]}")

# ---------------------------------------------------------------- D
print("\n########## D. the repair path doctor points at ##########")
print("  A truncated ledger with the projection left alone IS caught (issue #9).")
ws = build()
ws.claim(actor="claude", task_id="T1")
lines = ws.ledger.path.read_text(encoding="utf-8").splitlines()
dropped = json.loads(lines[-1])
ws.ledger.path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
print(f"  dropped event {dropped['sequence']} ({dropped['action']}), "
      f"projection untouched")
check("doctor reports it", "projection differs from ledger", verdict(ws))
attempt("  audit-projections raises", "projection differs from ledger",
        ws.audit_projections)

print("  the orchestrator now runs the documented remedy:")
result = ws.repair_projections(actor="antigravity")
check("  repair_projections reports success", "repaired: ['T1']",
      f"repaired: {result['repaired']}  mismatches: {result['mismatches']}")
check("  doctor afterwards", "healthy=True", verdict(ws))
state = json.loads((ws.tasks_dir / "T1.json").read_text(encoding="utf-8"))
check("  the task now reads back as the pre-claim state", "state=pending",
      f"state={state['state']}")
actions = [e["action"] for e in ws.ledger.read() if e.get("task_id") == "T1"]
check("  and the dropped event is still gone", "task.claimed present: False",
      f"task.claimed present: {'task.claimed' in actions} -> {actions}")
check("  does the repaired projection keep last_event_hash?",
      "last_event_hash present: False",
      f"last_event_hash present: {'last_event_hash' in state}")
attempt("  can the task still be read?", "accepted",
        lambda: ws.get_task("T1")["state"])

# ---------------------------------------------------------------- E
print("\n########## E. coverage map for the open findings ##########")
print("  Measured, not asserted as defects: README.md:381 lists `efo doctor`")
print("  under Recovery and audit without enumerating a scope.")
rows = []

ws = build()
ws.claim(actor="claude", task_id="T1", lease_seconds=315_360_000)
rows.append(("#7  a ten-year lease", verdict(ws)))

ws = build()
ws.claim(actor="claude", task_id="T1")
lines = ws.ledger.path.read_text(encoding="utf-8").splitlines()
prior = json.loads(lines[-2])
ws.ledger.path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
snapshot = dict(prior["payload"]["task"])
snapshot["last_event_hash"] = prior["event_hash"]
(ws.tasks_dir / "T1.json").write_text(json.dumps(snapshot, indent=2,
                                                 sort_keys=True),
                                      encoding="utf-8")
rows.append(("#9  truncation + projection rolled back", verdict(ws)))

ws = build()
bundle = ws.submissions_dir / "T1" / "attempt-001" / "worker-x" / "files"
bundle.mkdir(parents=True)
(bundle / "evidence.txt").write_text("tampered\n", encoding="utf-8")
rows.append(("#10 tampered submission bundle", verdict(ws)))

for label, line in rows:
    print(f"        {label:<42} {line}")

print("  the workspace ships an independence auditor; does doctor run it?")
ws = build()
keys = sorted(report(ws)["checks"].keys())
print(f"        audit_workspace checks: {keys}")
check("  audit_independence among them", "independence present: False",
      f"independence present: {'independence' in keys}")
print(f"        it exists as a separate call: "
      f"{'audit_independence' in dir(Workspace)}")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
