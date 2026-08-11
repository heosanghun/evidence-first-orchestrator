#!/usr/bin/env python3
"""EFO task lifecycle gates at main (5694ab45).

Claim / lease / start / submit ordering, lease theft, double claim, heartbeat on
an expired lease, and whether the lease duration a worker asks for is bounded.

Every rejection is asserted on its MESSAGE, so a different gate firing cannot be
mistaken for the one under test.  Section A is the positive control: the honest
flow must succeed before any refusal below means anything.

    python3 probe_lifecycle_gates.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.model import lease_expired  # noqa: E402
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


def attempt(name: str, expected: str, fn) -> None:
    try:
        fn()
        check(name, expected, "accepted")
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


SIX_SECTIONS = "\n".join([
    "# report", "", "## 1. Files changed", "none", "",
    "## 2. Validation and raw output", "recorded", "",
    "## 3. Pass, fail, and skip counts", "recorded", "",
    "## 4. Known-answer comparison", "recorded", "",
    "## 5. Proposed changes outside ownership", "None.", "",
    "## 6. Unmeasured items", "[FILL]", ""])


def bundle(directory: Path, stem: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    art = directory / f"{stem}.artifact.txt"
    art.write_text(f"{stem}\n", encoding="utf-8")
    digest = hashlib.sha256(art.read_bytes()).hexdigest()
    report = directory / f"{stem}.md"
    report.write_text(SIX_SECTIONS, encoding="utf-8")
    manifest = directory / f"{stem}.evidence.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{"path": art.name, "sha256": digest}],
        "validations": [{"command": "known-test", "exit_code": 0, "passed": 1,
                         "failed": 0, "skipped": 0, "skip_reasons": []}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "functional behavior", "kind": "functional",
                    "measured": True, "value": "pass", "evidence": [art.name]}],
    }, indent=2), encoding="utf-8")
    return report, manifest


root = Path(tempfile.mkdtemp(prefix="efo-life-"))
ws = Workspace.initialize(root / "ws", name="lifecycle-probe",
                          orchestrator="antigravity",
                          preset="antigravity-codex-claude")
for aid, principal, family in [("w", "openai", "openai-codex"),
                               ("thief", "google", "gemini")]:
    ws.add_agent(actor="antigravity", agent_id=aid, role="worker", mode="manual",
                 control_principal=principal, model_family=family)
reports = ws.reports_dir

print("########## A. POSITIVE CONTROL - the honest flow ##########")
ws.create_task(actor="antigravity", task_id="OK", title="t",
               description="honest flow", owner="w")
lease_ok = ws.claim(actor="w", task_id="OK")
ws.start(actor="w", task_id="OK", lease_token=lease_ok["lease_token"])
rep, man = bundle(reports / "w", "OK")
ws.submit(actor="w", task_id="OK", lease_token=lease_ok["lease_token"],
          report_path=rep, manifest_path=man)
check("claim -> start -> submit succeeds", "submitted",
      f"state={ws.get_task('OK')['state']}")

print("\n########## B. ordering ##########")
ws.create_task(actor="antigravity", task_id="ORD", title="t",
               description="ordering", owner="w")
rep2, man2 = bundle(reports / "w", "ORD")
attempt("start before claim", "has no active lease",
        lambda: ws.start(actor="w", task_id="ORD", lease_token="nope"))
# Rejected by an earlier gate than the lease check; the first run of this probe
# expected "has no active lease" and mis-flagged a correct refusal.
attempt("submit before claim", "must be running before submission",
        lambda: ws.submit(actor="w", task_id="ORD", lease_token="nope",
                          report_path=rep2, manifest_path=man2))
attempt("heartbeat before claim", "Cannot heartbeat",
        lambda: ws.heartbeat(actor="w", task_id="ORD", lease_token="nope"))

print("\n########## C. lease ownership and tokens ##########")
lease_ord = ws.claim(actor="w", task_id="ORD")
token = lease_ord["lease_token"]
attempt("second claim of the same task", "not pending",
        lambda: ws.claim(actor="w", task_id="ORD"))
attempt("another agent presents the real token", "belongs to another worker",
        lambda: ws.start(actor="thief", task_id="ORD", lease_token=token))
attempt("the owner presents a wrong token", "lease token is invalid",
        lambda: ws.start(actor="w", task_id="ORD", lease_token="wrong-token"))
attempt("submit skipping start (claimed -> submitted)",
        "must be running before submission",
        lambda: ws.submit(actor="w", task_id="ORD", lease_token=token,
                          report_path=rep2, manifest_path=man2))

print("\n########## D. expiry ##########")
ws.create_task(actor="antigravity", task_id="EXP", title="t",
               description="expiry", owner="w")
short = ws.claim(actor="w", task_id="EXP", lease_seconds=10)
print("  waiting 11s for a 10s lease to lapse...")
time.sleep(11)
check("the lease is expired", "True", f"lease_expired={lease_expired(ws.get_task('EXP'))}")
attempt("start on an expired lease", "lease has expired",
        lambda: ws.start(actor="w", task_id="EXP",
                         lease_token=short["lease_token"]))
attempt("heartbeat cannot revive an expired lease", "lease has expired",
        lambda: ws.heartbeat(actor="w", task_id="EXP",
                             lease_token=short["lease_token"]))
recovered = ws.recover_expired(actor="antigravity")
check("recover_expired moves it to blocked", "blocked",
      f"recovered={[t['id'] + ':' + t['state'] for t in recovered]}")

print("\n########## E. is the lease duration the worker asks for bounded? ##########")
ws.create_task(actor="antigravity", task_id="LONG", title="t",
               description="long lease", owner="w")
attempt("lease_seconds below the documented floor of 10", "at least 10 seconds",
        lambda: ws.claim(actor="w", task_id="LONG", lease_seconds=9))
ten_years = 10 * 365 * 24 * 3600
ws.claim(actor="w", task_id="LONG", lease_seconds=ten_years)
task = ws.get_task("LONG")
check("a ten-year lease is refused", "rejected",
      f"accepted: expires_at={task['lease']['expires_at']} "
      f"duration_seconds={task['lease']['duration_seconds']}")
check("  and recover_expired can still reclaim it", "LONG",
      f"recovered={[t['id'] for t in ws.recover_expired(actor='antigravity')]}")
attempt("the orchestrator can requeue the stranded task", "accepted",
        lambda: ws.requeue(actor="antigravity", task_id="LONG",
                           reason="lease is a decade long"))
print("  every public Workspace method whose name suggests lease recovery:")
import inspect
from evidence_orchestrator.workspace import Workspace as _W
names = [n for n, _ in inspect.getmembers(_W, inspect.isfunction)
         if not n.startswith("_")
         and any(k in n for k in ("lease", "recover", "release", "revoke",
                                  "cancel", "requeue", "expire"))]
print(f"        {names}")

shutil.rmtree(root, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
