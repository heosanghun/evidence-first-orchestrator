#!/usr/bin/env python3
"""EFO `independence.py` at main (5694ab45): does issue #3 still reproduce?

Issue #3 was measured at `f35d5176`. `main` is now `5694ab45`, and #3's own
"Scope and boundary" says the `alias_of` / `alias_chain` / `shared_alias_lineage`
machinery was new and unexamined at the time. This re-runs #3's attack against
the current tree, re-tests its secondary claim about the audit policy, and then
probes the alias machinery it left open.

Section A is the positive control: an honest independent verification must be
accepted, and the audit must report it independent, before any of the rest
means anything. Every rejection is asserted on its MESSAGE, by substring.

    python3 probe_independence_audit.py
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
from evidence_orchestrator.independence import (  # noqa: E402
    audit_verification_events,
    resolve_identity_registry,
)
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-indep-"))

REPORT_BODY = "\n".join([
    "# report", "",
    "## 1. Scope", "independence probe", "",
    "## 2. What was done", "one passing check", "",
    "## 3. Counts", "passed=1 failed=0 skipped=0", "",
    "## 4. Known-answer comparison", "expected 4, observed 4", "",
    "## 5. Outside ownership", "none", "",
    "## 6. Not verified", "nothing", "",
])


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


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_for(ws: Workspace, actor: str, stem: str) -> Path:
    home = ws.reports_dir / actor
    home.mkdir(parents=True, exist_ok=True)
    art = home / f"{stem}.artifact.txt"
    art.write_text(f"{stem} artifact\n", encoding="utf-8")
    path = home / f"{stem}.manifest.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{"path": str(art), "sha256": sha_of(art)}],
        "validations": [{"command": "pytest -q", "exit_code": 0, "passed": 1,
                         "failed": 0, "skipped": 0, "skip_reasons": []}],
        "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                 "observed": 4, "passed": True}],
        "claims": [{"name": "functional behavior", "kind": "functional",
                    "measured": True, "value": "pass",
                    "evidence": [str(art)]}],
    }, indent=2), encoding="utf-8")
    return path


def build(*, verifier_principal: str, verifier_family: str) -> Workspace:
    """Worker `claude` is claude/anthropic-claude (from the preset)."""
    root = Path(tempfile.mkdtemp(prefix="ws-", dir=ROOT))
    ws = Workspace.initialize(root / "ws", name="independence-probe",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                             control_principal="claude",
                             model_family="anthropic-claude")
    ws.add_agent(actor="antigravity", agent_id="claude-verifier",
                 role="verifier", mode="manual",
                 control_principal=verifier_principal,
                 model_family=verifier_family)
    ws.create_task(actor="antigravity", task_id="T1", title="T1",
                   description="work", owner="claude")
    return ws


def submit(ws: Workspace) -> None:
    home = ws.reports_dir / "claude"
    home.mkdir(parents=True, exist_ok=True)
    report = home / "T1.md"
    report.write_text(REPORT_BODY, encoding="utf-8")
    manifest = manifest_for(ws, "claude", "T1")
    claim = ws.claim(actor="claude", task_id="T1")
    token = claim["lease_token"]
    ws.start(actor="claude", task_id="T1", lease_token=token)
    ws.submit(actor="claude", task_id="T1", lease_token=token,
              report_path=report, manifest_path=manifest)


def verify(ws: Workspace) -> str:
    return ws.verify(
        actor="claude-verifier", task_id="T1", decision="accept",
        note="reproduced independently",
        verification_manifest=manifest_for(ws, "claude-verifier", "V1"),
    )["state"]


def audit(ws: Workspace, **kwargs: Any) -> dict[str, Any]:
    return ws.audit_independence(**kwargs)


def summary(result: dict[str, Any]) -> str:
    return (f"checked={result['checked']} independent={result['independent']} "
            f"non_independent={result['non_independent']}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - an honestly independent verification ##########")
ws = build(verifier_principal="openai", verifier_family="openai-codex")
submit(ws)
attempt("a genuinely different verifier is accepted", "accepted (verified)",
        lambda: verify(ws))
result = audit(ws)
check("  and the audit reports it independent",
      "checked=1 independent=1 non_independent=0", summary(result))
finding = result["findings"][0]
check("  sourcing both sides from the recorded snapshots",
      "worker=submission_snapshot verifier=verification_snapshot",
      f"worker={finding['worker_identity_source']} "
      f"verifier={finding['verifier_identity_source']}")

# ---------------------------------------------------------------- B
print("\n########## B. issue #3, re-run verbatim at 5694ab45 ##########")
ws = build(verifier_principal="claude", verifier_family="anthropic-claude")
submit(ws)
attempt("a verifier declared identical to the worker",
        "Independent verification could not be established: "
        "same_control_principal, same_model_family",
        lambda: verify(ws))

ws.attest_agent_identity(actor="antigravity", agent_id="claude-verifier",
                         control_principal="openai",
                         model_family="openai-codex")
print("  the verifier is re-attested to openai / openai-codex")
attempt("  the byte-identical verification, replayed", "accepted (verified)",
        lambda: verify(ws))

result = audit(ws)
check("  what does audit-independence say now?",
      "checked=1 independent=1 non_independent=0", summary(result))
finding = result["findings"][0]
check("    and where did it source the verifier?", "verification_snapshot",
      finding["verifier_identity_source"])

actions = [(event["sequence"], event["action"], event.get("actor"))
           for event in ws.ledger.read()
           if event["action"] in {"task.submitted", "agent.identity_attested",
                                  "task.verified"}]
print("  the mutating event sits inside the task's own lifetime:")
for sequence, action, actor in actions:
    print(f"        {sequence:>3}  {action:<26} {actor}")
attested = [s for s, a, _ in actions if a == "agent.identity_attested"]
submitted = [s for s, a, _ in actions if a == "task.submitted"]
verified = [s for s, a, _ in actions if a == "task.verified"]
check("  submitted < attested < verified", "in-lifetime: True",
      f"in-lifetime: {bool(submitted and attested and verified) and submitted[0] < attested[-1] < verified[0]}")

print("  does the audit consider agent.identity_attested at all?")
source = Path("/tmp/efo-prov/src/evidence_orchestrator/independence.py")
text = source.read_text(encoding="utf-8")
check("  the string appears in independence.py",
      "identity_attested present: False",
      f"identity_attested present: {'identity_attested' in text}")
actions_read = sorted({
    line.strip() for line in text.splitlines()
    if 'event.get("action")' in line or '"task.' in line
})
print("  every event action independence.py mentions:")
for line in actions_read:
    print(f"        {line}")

# ---------------------------------------------------------------- C
print("\n########## C. issue #3's secondary claim: is a policy a mitigation? ##########")
print("  #3 says resolve_identity_registry consults the policy only as a")
print("  fallback for agents with NO identity, so it cannot pin one that has.")
agents = {agent["id"]: agent for agent in ws.list_agents()}
pinned = resolve_identity_registry(
    agents,
    policy={"agents": {"claude-verifier": {
        "schema_version": 1, "control_principal": "claude",
        "model_family": "anthropic-claude", "alias_of": None,
        "alias_chain": []}}},
)
check("a policy naming an agent that already has an identity",
      "control_principal=openai",
      f"control_principal={pinned['claude-verifier']['control_principal']}")
result = audit(ws, identity_policy={"agents": {"claude-verifier": {
    "schema_version": 1, "control_principal": "claude",
    "model_family": "anthropic-claude", "alias_of": None, "alias_chain": []}}})
check("  and the audit with that policy applied",
      "checked=1 independent=1 non_independent=0", summary(result))

no_identity = {"stranger": {"id": "stranger", "role": "worker"}}
filled = resolve_identity_registry(no_identity, policy={"agents": {"stranger": {
    "schema_version": 1, "control_principal": "mistral",
    "model_family": "mistral-large", "alias_of": None, "alias_chain": []}}})
check("  a policy DOES fill an agent that has none", "control_principal=mistral",
      f"control_principal={filled['stranger']['control_principal']}")

# ---------------------------------------------------------------- D
print("\n########## D. the alias machinery #3 left unexamined ##########")
ws2 = build(verifier_principal="openai", verifier_family="openai-codex")
ws2.add_agent(actor="antigravity", agent_id="verifier-alias", role="verifier",
              mode="manual", alias_of="claude")
submit(ws2)
attempt("a verifier aliased to the worker",
        "Independent verification could not be established",
        lambda: ws2.verify(actor="verifier-alias", task_id="T1",
                           decision="accept", note="n",
                           verification_manifest=manifest_for(
                               ws2, "verifier-alias", "V1")))

registry = resolve_identity_registry({
    "root": {"identity": {"schema_version": 1, "control_principal": "openai",
                          "model_family": "openai-codex", "alias_of": None,
                          "alias_chain": []}},
    "mid": {"identity": {"schema_version": 1, "control_principal": "x",
                         "model_family": "y", "alias_of": "root",
                         "alias_chain": []}},
    "leaf": {"identity": {"schema_version": 1, "control_principal": "x",
                          "model_family": "y", "alias_of": "mid",
                          "alias_chain": []}},
})
check("a three-deep alias chain resolves to the root's principal",
      "control_principal=openai chain=['mid', 'root']",
      f"control_principal={registry['leaf']['control_principal']} "
      f"chain={registry['leaf']['alias_chain']}")

attempt("an alias cycle", "Identity policy alias cycle",
        lambda: resolve_identity_registry({
            "a": {"identity": {"schema_version": 1, "control_principal": "x",
                               "model_family": "y", "alias_of": "b",
                               "alias_chain": []}},
            "b": {"identity": {"schema_version": 1, "control_principal": "x",
                               "model_family": "y", "alias_of": "a",
                               "alias_chain": []}},
        }))

attempt("an alias to an agent that has no identity", "accepted",
        lambda: resolve_identity_registry({
            "orphan": {"identity": {"schema_version": 1,
                                    "control_principal": "x",
                                    "model_family": "y", "alias_of": "ghost",
                                    "alias_chain": []}},
        })["orphan"])

# ---------------------------------------------------------------- E
print("\n########## E. a verification with no matching submission ##########")
ws3 = build(verifier_principal="openai", verifier_family="openai-codex")
submit(ws3)
verify(ws3)
events = ws3.ledger.read()
trimmed = [event for event in events if event["action"] != "task.submitted"]
agents3 = {agent["id"]: agent for agent in ws3.list_agents()}
orphan = audit_verification_events(trimmed, agents3)
check("the audit falls back to the task owner's CURRENT identity",
      "worker=signed_agent_identity",
      f"worker={orphan['findings'][0]['worker_identity_source']}")
check("  and says so in the finding", "checked=1",
      summary(orphan))
print("  -> the fallback is disclosed, not silent. That is the right shape.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
