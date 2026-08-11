#!/usr/bin/env python3
"""Transport-attested progress on EFO main (5694ab45): does it go stale?

A lease has a freshness test (`lease_is_active`) and a claimed task drops out of
the portfolio's active count once the lease expires.  A transport-reported
external phase has no freshness test at all.  This measures both sides of that
asymmetry, with the lease case as the positive control.

    python3 probe_proxy_status_freshness.py
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.workspace import Workspace  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "collector", "/tmp/efo-prov/monitor/collector.py")
collector = importlib.util.module_from_spec(spec)
assert spec.loader is not None
# collector.py declares frozen dataclasses, and dataclasses resolves annotations
# through sys.modules[cls.__module__]; registering before exec is required.
sys.modules["collector"] = collector
spec.loader.exec_module(collector)

FAIL = 0


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def counts(tasks: list[dict]) -> dict[str, int]:
    """Re-derive the portfolio tally the collector computes (lines 893-912)."""
    verified = active = blocked = 0
    for task in tasks:
        state = str(task.get("canonical_state") or task.get("state") or "")
        phase = str(task.get("external_phase") or "")
        if state in collector.TERMINAL_STATES:
            verified += 1
        elif state == "pending" and phase in collector.PORTFOLIO_EXTERNAL_ACTIVE_PHASES:
            active += 1
        elif state in collector.PORTFOLIO_ACTIVE_STATES and (
            state == "submitted" or task.get("lease_active") is True
        ):
            active += 1
        elif (
            state in collector.BLOCKED_STATES
            or state in {"claimed", "running"}
            or (state == "pending" and phase == "blocked")
        ):
            blocked += 1
    return {"verified": verified, "active": active, "blocked": blocked}


root = Path(tempfile.mkdtemp(prefix="efo-proxy-"))
ws = Workspace.initialize(root / "ws", name="proxy-probe",
                          orchestrator="antigravity",
                          preset="antigravity-codex-claude")
ws.add_agent(actor="antigravity", agent_id="ext", role="worker", mode="manual",
             control_principal="openai", model_family="openai-codex")
# The transport actor needs its own signed identity; the first run of this probe
# omitted it and every call rejected with "Transport actor needs a signed
# identity attestation" - a different gate than the one under test.
ws.attest_agent_identity(actor="antigravity", agent_id="antigravity",
                         control_principal="antigravity",
                         model_family="antigravity-native")
ws.create_task(actor="antigravity", task_id="T1", title="external work",
               description="dispatched to an external worker", owner="ext")

print("########## A. the phase machine ##########")
for phase, expect in [("working", "first proxy status phase must be dispatched"),
                      ("dispatched", "accepted")]:
    try:
        ws.report_proxy_status(actor="antigravity", author="ext", task_id="T1",
                               phase=phase, reference="ext-run-1",
                               note="external dispatch")
        check(f"first phase = {phase}", expect, "accepted")
    except Exception as exc:
        check(f"first phase = {phase}", expect, f"rejected ({exc})")

try:
    ws.report_proxy_status(actor="antigravity", author="ext", task_id="T1",
                           phase="working", reference="OTHER-ref", note="n")
    check("reference swapped mid-dispatch", "reference cannot change", "accepted")
except Exception as exc:
    check("reference swapped mid-dispatch", "reference cannot change", f"rejected ({exc})")

# The machine is stricter than a naive reading: working -> ready is refused,
# `reviewing` is mandatory. The first run of this probe skipped it and hit
# "cannot regress 'working' -> 'ready'".
for step in ("working", "reviewing", "ready"):
    ws.report_proxy_status(actor="antigravity", author="ext", task_id="T1",
                           phase=step, reference="ext-run-1", note=step)
try:
    ws.report_proxy_status(actor="antigravity", author="ext", task_id="T1",
                           phase="ready", reference="ext-run-1", note="skip")
    check("working -> ready must pass through reviewing", "n/a", "n/a")
except Exception:
    pass
try:
    ws.report_proxy_status(actor="antigravity", author="ext", task_id="T1",
                           phase="working", reference="ext-run-1", note="back")
    check("phase regression ready -> working", "cannot regress", "accepted")
except Exception as exc:
    check("phase regression ready -> working", "cannot regress", f"rejected ({exc})")

task = ws.get_task("T1")
check("canonical state is untouched by the report", "pending",
      f"state={task['state']}")

print("\n########## B. how the monitor renders it ##########")
view = collector.task_to_view(task)
check("progress overridden by the transport report", "85",
      f"progress_percent={view['progress_percent']} "
      f"(canonical 'pending' would be {collector.TASK_PROGRESS['pending']})")
check("the override is labelled", "transport_assertion",
      f"status_source={view['status_source']} badge={view['status_badge']} "
      f"canonical_state={view['canonical_state']}")

print("\n########## C. freshness: the asymmetry ##########")
old = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

stale_lease = {"canonical_state": "running", "state": "running",
               "external_phase": "", "lease_active":
               collector.lease_is_active({"expires_at": old})}
check("POSITIVE CONTROL - a 30-day-old lease is not active", "False",
      f"lease_is_active={stale_lease['lease_active']}")
check("  and a task on that stale lease is not counted active",
      "'active': 0", str(counts([stale_lease])))

stale_view = dict(view)
stale_view["updated_at"] = old
check("a 30-day-old transport report is still counted active",
      "'active': 1", str(counts([stale_view])))
check("  and still renders at the same progress", "85",
      f"progress_percent={stale_view['progress_percent']}, "
      f"updated_at={stale_view['updated_at']}")

print("\n########## D. what clears the projection ##########")
# requeue refuses a pending task, and a proxy status only exists on a pending
# task, so the clearing path is reached only after the task is claimed. The
# first run of this probe called requeue directly and hit
# "Cannot requeue task T1 in state pending".
lease = ws.claim(actor="ext", task_id="T1")
claimed = ws.get_task("T1")
check("a claimed task keeps the stale external_status on disk", "ready",
      f"external_status.phase={claimed.get('external_status', {}).get('phase')}")
claimed_view = collector.task_to_view(claimed)
check("  but the monitor ignores it once the task leaves pending", "25",
      f"progress_percent={claimed_view['progress_percent']} "
      f"status_source={claimed_view['status_source']}")
# requeue accepts only blocked or rejected, so the full reachable path is
# claim -> start -> block -> requeue. A task left pending with a stale report
# has no clearing path at all.
ws.start(actor="ext", task_id="T1", lease_token=lease["lease_token"])
ws.block(actor="ext", task_id="T1", lease_token=lease["lease_token"],
         reason="external dispatch abandoned")
ws.requeue(actor="antigravity", task_id="T1", reason="dispatch abandoned")
after = ws.get_task("T1")
check("requeue drops external_status", "None",
      f"external_status={after.get('external_status')}")
after_view = collector.task_to_view(after)
check("  and the task falls back to canonical progress", "10",
      f"progress_percent={after_view['progress_percent']}")

shutil.rmtree(root, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
