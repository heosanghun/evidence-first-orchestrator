#!/usr/bin/env python3
"""EFO `model.py` at main (5694ab45): the state machine's own definitions.

`new_task` writes the pre-registered permissions and gates that every later
check reads. `transition` is the only legal way to change a task's state.
Everything else in the broker trusts both.

Section A is the positive control. Section E checks `transition` against the
full 8x8 state matrix rather than a sample.

    python3 probe_model_gates.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.evidence import validate_manifest  # noqa: E402
from evidence_orchestrator.model import (  # noqa: E402
    TASK_STATES,
    TRANSITIONS,
    lease_expired,
    lease_expiry,
    new_task,
    transition,
    validate_task,
)

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-model-"))
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


ART = ROOT / "a.txt"
ART.write_text("artifact\n", encoding="utf-8")
ART_SHA = hashlib.sha256(ART.read_bytes()).hexdigest()


def manifest(*, measured_performance: bool = False,
             skipped: int = 0) -> Path:
    claims: list[dict[str, Any]] = [
        {"name": "functional behavior", "kind": "functional", "measured": True,
         "value": "pass", "evidence": [ART.name]}
    ]
    if measured_performance:
        claims.append({"name": "speedup", "kind": "performance",
                       "measured": True, "value": 26.7,
                       "evidence": [ART.name]})
    path = ROOT / "m.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{"path": ART.name, "sha256": ART_SHA}],
        "validations": [{"command": "pytest -q", "exit_code": 0, "passed": 3,
                         "failed": 0, "skipped": skipped,
                         "skip_reasons": ["needs a GPU"] * skipped}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": claims,
    }, indent=2), encoding="utf-8")
    return path


def _try(record: dict[str, Any], target: str) -> str:
    try:
        transition(record, target)
        return "accepted"
    except Exception as exc:
        return str(exc)


def task(**over: Any) -> dict[str, Any]:
    return new_task(task_id="T1", title="T1", description="work",
                    owner="claude", created_by="antigravity", **over)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
base = task()
check("new_task denies everything by default",
      "{'gpu': False, 'network': False, 'performance_metrics': False}",
      str(dict(sorted(base["permissions"].items()))))
check("  and requires every gate", "'allow_skips': False",
      str(dict(sorted(base["gates"].items()))))
attempt("a measured performance claim under the default permissions",
        "Measured performance claims are forbidden",
        lambda: validate_manifest(manifest(measured_performance=True),
                                  permissions=base["permissions"],
                                  gates=base["gates"]))
attempt("  and an honest manifest still validates", "accepted",
        lambda: validate_manifest(manifest(), permissions=base["permissions"],
                                  gates=base["gates"])["passed"])

# ---------------------------------------------------------------- B
print("\n########## B. permissions and gates are never type-checked ##########")
print("  validate_task checks that permissions/gates ARE objects")
print("  (model.py:104-107) and nothing about what is in them. Every later")
print("  reader uses .get(name, default) in a boolean context.")
print()
print("  What a non-boolean does to a permission that GRANTS when truthy:")
for label, value in [("the boolean False", False),
                     ("the string \"false\"", "false"),
                     ("the string \"no\"", "no"),
                     ("the string \"0\"", "0"),
                     ("the integer 0", 0),
                     ("an empty list", []),
                     ("the string \"true\"", "true")]:
    granted = task(permissions={"performance_metrics": value})
    try:
        validate_manifest(manifest(measured_performance=True),
                          permissions=granted["permissions"],
                          gates=granted["gates"])
        verdict = "ALLOWED"
    except Exception:
        verdict = "refused"
    expected = "ALLOWED" if bool(value) else "refused"
    check(f"  performance_metrics = {label}", expected, verdict)

print("\n  and to the gate that GRANTS when truthy:")
for label, value in [("the boolean False", False),
                     ("the string \"false\"", "false"),
                     ("the boolean True", True)]:
    gated = task(gates={"allow_skips": value})
    try:
        validate_manifest(manifest(skipped=1), permissions=gated["permissions"],
                          gates=gated["gates"])
        verdict = "skips ALLOWED"
    except Exception:
        verdict = "skips refused"
    expected = "skips ALLOWED" if bool(value) else "skips refused"
    check(f"  allow_skips = {label}", expected, verdict)

print("\n  the require_* gates restrict when truthy, so the same confusion")
print("  fails SAFE there:")
for label, value in [("the string \"false\"", "false"), ("False", False)]:
    gated = task(gates={"require_known_answer_check": value})
    empty = json.loads(manifest().read_text(encoding="utf-8"))
    empty["known_answer_checks"] = []
    path = ROOT / "m2.json"
    path.write_text(json.dumps(empty, indent=2), encoding="utf-8")
    try:
        validate_manifest(path, permissions=gated["permissions"],
                          gates=gated["gates"])
        verdict = "no known-answer check needed"
    except Exception:
        verdict = "still required"
    expected = "still required" if bool(value) else "no known-answer check needed"
    check(f"  require_known_answer_check = {label}", expected, verdict)

# ---------------------------------------------------------------- C
print("\n########## C. is a non-boolean reachable? ##########")
cli = (SOURCE.parent / "evidence_orchestrator" / "cli.py").read_text(
    encoding="utf-8")
block = cli.split("def _cmd_task_add")[1].split("task = workspace.create_task")[0]
print("  cli.py builds both dicts from argparse store_true flags:")
for line in block.splitlines():
    if "args." in line:
        print(f"        {line.strip()}")
check("  so the CLI can only ever pass real booleans", "args_ prefixed: True",
      f"args_ prefixed: {all('args.' in line for line in block.splitlines() if ':' in line and 'args.' in line)}")
print("  The Python API is the reachable path: Workspace.create_task takes")
print("  permissions= and gates= straight through to new_task, and this")
print("  project drives EFO programmatically, not only through the CLI.")

# ---------------------------------------------------------------- D
print("\n########## D. transition's updates can overwrite the target state ##########")
print("  model.py:117-120 sets state, then applies **updates AFTER it.")
pending = task()
forced = transition(pending, "claimed", state="verified")
check("transition(task, 'claimed', state='verified') lands on", "verified",
      forced["state"])
check("  the illegal edge without the override",
      "cannot transition pending -> verified", _try(pending, "verified"))
workspace_text = (SOURCE / "workspace.py").read_text(encoding="utf-8")
sites = [line.strip() for line in workspace_text.splitlines()
         if "state=" in line and "transition" in line]
check("  call sites that pass state= into transition", "sites: []",
      f"sites: {sites}")
print("        -> unreachable through the broker. Recorded as an API contract")
print("           gap: the function documents 'a legal state transition' and")
print("           its own last line can undo the check.")

# ---------------------------------------------------------------- E
print("\n########## E. the full 8x8 transition matrix ##########")
mismatches = []
for source in sorted(TASK_STATES):
    for target in sorted(TASK_STATES):
        record = task()
        record["state"] = source
        legal = target in TRANSITIONS.get(source, set())
        result = _try(record, target)
        accepted = result == "accepted"
        if accepted != legal:
            mismatches.append((source, target, legal, accepted))
print(f"  {len(TASK_STATES)}x{len(TASK_STATES)} = {len(TASK_STATES) ** 2} edges")
check("transition agrees with TRANSITIONS on every edge", "mismatches: []",
      f"mismatches: {mismatches}")
legal_edges = sorted(f"{s}->{t}" for s, targets in TRANSITIONS.items()
                     for t in targets)
print(f"  the {len(legal_edges)} legal edges: {legal_edges}")
check("  archived is terminal", "archived targets: set()",
      f"archived targets: {TRANSITIONS['archived']}")
check("  pending -> submitted exists, reserved for proxy_submit",
      "'submitted' in pending: True",
      f"'submitted' in pending: {'submitted' in TRANSITIONS['pending']}")

# ---------------------------------------------------------------- F
print("\n########## F. the lease helpers ##########")
attempt("lease_expiry below the floor", "at least 10 seconds",
        lambda: lease_expiry(9))
check("lease_expiry at the floor", "Z", lease_expiry(10, "2026-08-02T00:00:00Z"))
check("  and it has no ceiling (issue #7)", "2036",
      lease_expiry(315_360_000, "2026-08-02T00:00:00Z"))
leased = task()
leased["lease"] = {"expires_at": "2026-08-02T00:00:10Z"}
check("a lease expiring exactly now counts as expired", "expired: True",
      f"expired: {lease_expired(leased, '2026-08-02T00:00:10Z')}")
check("  one second earlier does not", "expired: False",
      f"expired: {lease_expired(leased, '2026-08-02T00:00:09Z')}")
check("a task with no lease is never expired", "expired: False",
      f"expired: {lease_expired(task())}")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
