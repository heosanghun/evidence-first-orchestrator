#!/usr/bin/env python3
"""EFO ledger hash chain and HMAC signing at main (5694ab45).

`docs/ARCHITECTURE.md:160` claims "Ledger line is edited -> Hash or HMAC
verification fails" and "Task JSON is lost -> Ledger retains complete snapshot".
This tests those claims, then the shapes the documentation does not mention:
tail truncation, and truncation with the projections rolled back to match.

The local-key limitation is NOT probed as a defect: README.md:422 and
SECURITY.md:38 already state that the key only protects against parties who
cannot read it.

Section A is the positive control.  Every rejection is asserted on its MESSAGE.

    python3 probe_ledger_chain.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.doctor import audit_workspace as diagnose  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def healthy(ws) -> str:
    """doctor's entry point is audit_workspace(root), not audit_workspace(ws)."""
    return str(diagnose(ws.root)["healthy"])


def attempt(name: str, expected: str, fn) -> None:
    try:
        value = fn()
        check(name, expected, f"accepted ({value})")
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


def build() -> tuple[Workspace, Path]:
    root = Path(tempfile.mkdtemp(prefix="efo-ledger-"))
    ws = Workspace.initialize(root / "ws", name="ledger-probe",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    ws.add_agent(actor="antigravity", agent_id="w", role="worker", mode="manual",
                 control_principal="openai", model_family="openai-codex")
    for tid in ("T1", "T2"):
        ws.create_task(actor="antigravity", task_id=tid, title=tid,
                       description="work", owner="w")
    ws.claim(actor="w", task_id="T1")
    return ws, root


def lines(ws: Workspace) -> list[str]:
    return ws.ledger.path.read_text(encoding="utf-8").splitlines()


def rewrite(ws: Workspace, new_lines: list[str]) -> None:
    ws.ledger.path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


print("########## A. POSITIVE CONTROL ##########")
ws, root = build()
status = ws.ledger.verify()
check("an untouched ledger verifies", "'valid': True", str(status))
check("  and doctor reports healthy", "healthy=True",
      "healthy=" + healthy(ws))

print("\n########## B. the documented claims ##########")
ws, root = build()
raw = lines(ws)
event = json.loads(raw[2])
event["actor"] = "someone-else"
raw[2] = json.dumps(event, ensure_ascii=False, sort_keys=True)
rewrite(ws, raw)
attempt("an edited line (docs: hash or HMAC verification fails)",
        "event hash mismatch at event 3", ws.ledger.verify)

ws, root = build()
raw = lines(ws)
event = json.loads(raw[2])
event["signature"] = "0" * 64
raw[2] = json.dumps(event, ensure_ascii=False, sort_keys=True)
rewrite(ws, raw)
attempt("a forged signature with an intact hash",
        "signature mismatch at event 3", ws.ledger.verify)

ws, root = build()
raw = lines(ws)
rewrite(ws, raw[:2] + [raw[3], raw[2]] + raw[4:])
attempt("two events reordered", "sequence mismatch", ws.ledger.verify)

ws, root = build()
raw = lines(ws)
rewrite(ws, raw[:2] + [raw[2], raw[2]] + raw[3:])
attempt("an event duplicated in place", "sequence mismatch", ws.ledger.verify)

ws, root = build()
task_file = ws.tasks_dir / "T1.json"
task_file.unlink()
attempt("a deleted task projection (docs: ledger retains the snapshot)",
        "projection missing",
        lambda: ws._audit_projections(repair=False)["mismatches"])

print("\n########## C. tail truncation - not mentioned in the docs ##########")
ws, root = build()
raw = lines(ws)
print(f"  ledger has {len(raw)} events; dropping the last one (the claim)")
rewrite(ws, raw[:-1])
attempt("does the chain itself notice a dropped tail?", "rejected",
        ws.ledger.verify)
attempt("  does reading the task notice?",
        "projection differs from the signed ledger",
        lambda: ws.get_task("T1")["state"])
check("  and doctor?", "healthy=False", "healthy=" + healthy(ws))

print("\n########## D. truncation with the projection rolled back to match ##########")
ws, root = build()
raw = lines(ws)
pending_snapshot = None
for line in raw:
    event = json.loads(line)
    if event.get("action") == "task.created" and event.get("task_id") == "T1":
        pending_snapshot = event["payload"]["task"]
rewrite(ws, raw[:-1])
(ws.tasks_dir / "T1.json").write_text(
    json.dumps({**pending_snapshot,
                "last_event_hash": json.loads(raw[-2])["event_hash"]},
               indent=2, sort_keys=True), encoding="utf-8")
attempt("the chain verifies", "accepted", ws.ledger.verify)
attempt("  and the task reads back as pending", "accepted",
        lambda: ws.get_task("T1")["state"])
check("  and doctor?", "healthy=", "healthy=" + healthy(ws))
print("  -> the claim event is gone from history and nothing reports it.")

shutil.rmtree(root, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
