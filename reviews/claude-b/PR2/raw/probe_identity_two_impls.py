#!/usr/bin/env python3
"""EFO at main (5694ab45): two independent implementations of agent identity.

`src/evidence_orchestrator/independence.py::resolve_identity_registry` decides
who is independent of whom for the verification gate.
`monitor/collector.py::_resolve_signed_identity_registry` decides the same
thing again, separately, for the dashboard.

Two implementations of one security-relevant idea is the shape that goes wrong
quietly, so this runs both over one corpus of identity declarations and reports
where they agree and where they do not.

Section A is the positive control: on a real workspace both must resolve the
same identities, or every disagreement below is meaningless.

    python3 probe_identity_two_impls.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
sys.path.insert(0, "/tmp/efo-prov")
from evidence_orchestrator.independence import (  # noqa: E402
    resolve_identity_registry,
)
from evidence_orchestrator.workspace import Workspace  # noqa: E402
from monitor.collector import (  # noqa: E402
    _resolve_signed_identity_registry,
    resolve_signed_identity_groups,
    task_actor_ids,
)

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-ident2-"))


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def identity(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": 1,
        "control_principal": "openai",
        "model_family": "openai-codex",
        "alias_of": None,
        "alias_chain": [],
    }
    base.update(over)
    return base


def core_verdict(agents: dict[str, dict[str, Any]], agent_id: str) -> str:
    """independence.py's answer for one agent."""
    try:
        registry = resolve_identity_registry(agents)
    except Exception as exc:
        return f"RAISED {type(exc).__name__}"
    value = registry.get(agent_id)
    if value is None:
        return "none"
    return (f"{value['control_principal']}/{value['model_family']}"
            f" chain={value['alias_chain']}")


def collector_verdict(agents: dict[str, dict[str, Any]], agent_id: str) -> str:
    """collector.py's answer for the same agent."""
    try:
        registry, _roots = _resolve_signed_identity_registry(
            [{"id": key, **record} for key, record in agents.items()],
            ledger_valid=True,
        )
    except Exception as exc:
        return f"RAISED {type(exc).__name__}"
    value = registry.get(agent_id)
    if value is None:
        return "rejected"
    return (f"{value['control_principal']}/{value['model_family']}"
            f" chain={value['alias_chain']}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - a real workspace ##########")
ws = Workspace.initialize(ROOT / "ws", name="identity-probe",
                          orchestrator="antigravity",
                          preset="antigravity-codex-claude")
ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                         control_principal="anthropic",
                         model_family="anthropic-claude")
ws.add_agent(actor="antigravity", agent_id="claude-alias", role="verifier",
             mode="manual", alias_of="claude")
registered = ws.list_agents()
agents = {agent["id"]: agent for agent in registered}

core = resolve_identity_registry(agents)
collector, roots = _resolve_signed_identity_registry(registered,
                                                     ledger_valid=True)
for agent_id in ("claude", "claude-alias"):
    check(f"both resolve {agent_id} identically",
          f"agree: True",
          f"agree: {core[agent_id] == collector[agent_id]}  "
          f"{core[agent_id]['control_principal']}/"
          f"{core[agent_id]['model_family']} "
          f"chain={core[agent_id]['alias_chain']}")
groups = resolve_signed_identity_groups(registered, ledger_valid=True)
check("  and the collector groups the alias with its root",
      "['claude', 'claude-alias']",
      str(sorted(groups["claude-alias"])))

# ---------------------------------------------------------------- B
print("\n########## B. head to head over one corpus ##########")
print(f"  {'shape':<46}{'independence.py':<38}collector.py")
CORPUS: list[tuple[str, dict[str, dict[str, Any]], str]] = [
    ("an honest non-alias",
     {"a": {"identity": identity()}}, "a"),
    ("an honest alias",
     {"root": {"identity": identity()},
      "a": {"identity": identity(control_principal="openai",
                                 model_family="openai-codex",
                                 alias_of="root", alias_chain=["root"])}}, "a"),
    ("an alias whose declared chain is WRONG",
     {"root": {"identity": identity()},
      "mid": {"identity": identity(alias_of="root", alias_chain=["root"])},
      "a": {"identity": identity(alias_of="mid", alias_chain=["mid"])}}, "a"),
    ("an alias declaring a DIFFERENT principal from its target",
     {"root": {"identity": identity()},
      "a": {"identity": identity(control_principal="anthropic",
                                 model_family="anthropic-claude",
                                 alias_of="root", alias_chain=["root"])}}, "a"),
    ("a NON-alias carrying a non-empty alias_chain",
     {"a": {"identity": identity(alias_chain=["ghost"])}}, "a"),
    ("an identity with an EXTRA key",
     {"a": {"identity": {**identity(), "note": "x"}}}, "a"),
    ("schema_version 2",
     {"a": {"identity": identity(schema_version=2)}}, "a"),
    ("an alias cycle",
     {"a": {"identity": identity(alias_of="b", alias_chain=["b"])},
      "b": {"identity": identity(alias_of="a", alias_chain=["a"])}}, "a"),
    ("a self-alias",
     {"a": {"identity": identity(alias_of="a", alias_chain=["a"])}}, "a"),
    ("an alias to an agent that does not exist",
     {"a": {"identity": identity(alias_of="ghost", alias_chain=["ghost"])}},
     "a"),
    ("an agent_id inside its own alias_chain",
     {"root": {"identity": identity()},
      "a": {"identity": identity(alias_of="root", alias_chain=["root", "a"])}},
     "a"),
    ("no identity at all",
     {"a": {"id": "a"}}, "a"),
]
disagreements = []
for label, agents_case, target in CORPUS:
    left = core_verdict(agents_case, target)
    right = collector_verdict(agents_case, target)
    agree = (left == "none") == (right == "rejected") and (
        left == "none" or left == right)
    if not agree:
        disagreements.append((label, left, right))
    marker = "  " if agree else "!!"
    print(f"  {marker}{label:<44}{left:<38}{right}")

print(f"\n  disagreements: {len(disagreements)}")
for label, left, right in disagreements:
    print(f"        {label}")
    print(f"            independence.py -> {left}")
    print(f"            collector.py    -> {right}")

# ---------------------------------------------------------------- C
print("\n########## C. the ledger gate the collector has and the core does not ##########")
registry, _roots = _resolve_signed_identity_registry(registered,
                                                     ledger_valid=False)
check("collector: an invalid ledger empties the registry", "{}", str(registry))
core_still = resolve_identity_registry(agents)
check("independence.py has no such parameter", "resolves anyway: True",
      f"resolves anyway: {'claude' in core_still}")
print("  Not a defect: audit_independence calls self.ledger.verify() before")
print("  resolve_identity_registry (workspace.py:1488). The collector cannot")
print("  rely on a caller, because it reads the ledger through the CLI.")

# ---------------------------------------------------------------- D
print("\n########## D. task_actor_ids: attribution by exact snapshot equality ##########")
snapshot = collector["claude"]
task = {"owner": "claude", "verification": {"actor": "claude",
                                            "identity": snapshot}}
check("a verification whose snapshot matches the current registry",
      "{'claude'}",
      str(set(task_actor_ids(task, collector, {"claude"}))))
stale = {**snapshot, "control_principal": "openai"}
task_stale = {"owner": "codex", "verification": {"actor": "claude",
                                                 "identity": stale}}
check("  one whose snapshot no longer matches", "claude present: False",
      f"claude present: "
      f"{'claude' in task_actor_ids(task_stale, collector, {'claude', 'codex'})}")
print("  So the dashboard drops an actor whose identity has been re-attested")
print("  since the verification it is being credited for. That is stricter")
print("  than audit_verification_events, which trusts the frozen snapshot")
print("  (issue #3). Recorded as a divergence, not a defect - for attribution")
print("  the strict reading is the safe one.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
