#!/usr/bin/env python3
"""Does the alias machinery on main (5694ab45) hold?

evaluate_independence builds lineage from `alias_chain` and the actor id, but
never reads `alias_of`.  This asks whether that asymmetry is reachable, and
whether the documented alias guards actually fire.

Each probe is stated as expected/observed so a pass cannot be confused with a
gate that never ran.

    python3 probe_alias_lineage.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.errors import ConfigurationError  # noqa: E402
from evidence_orchestrator.independence import (  # noqa: E402
    build_identity,
    evaluate_independence,
    identity_snapshot,
)
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0


def check(name: str, expected: str, observed: str) -> None:
    """`expected` is matched as a substring of `observed`, so a guard that
    rejects with an explanatory message still counts as the expected rejection.
    An exact-equality comparison here produced six false 'UNEXPECTED' results on
    the first run; that was the harness, not the code under test."""

    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


root = Path(tempfile.mkdtemp(prefix="efo-alias-"))
ws = Workspace.initialize(root / "ws", name="alias-probe",
                          orchestrator="antigravity", preset="antigravity-codex-claude")

print("########## A. the documented alias guards ##########")
ws.add_agent(actor="antigravity", agent_id="t", role="worker", mode="manual",
             control_principal="openai", model_family="openai-codex")

try:
    ws.attest_agent_identity(actor="antigravity", agent_id="t", alias_of="t")
    check("self-alias", "rejected", "ACCEPTED")
except ConfigurationError as exc:
    check("self-alias", "rejected", f"rejected ({exc})")

ws.add_agent(actor="antigravity", agent_id="x", role="verifier", mode="manual",
             control_principal="claude", model_family="anthropic-claude")
try:
    ws.attest_agent_identity(actor="antigravity", agent_id="x", alias_of="t",
                             control_principal="other", model_family="other")
    check("alias plus explicit identity", "rejected", "ACCEPTED")
except ConfigurationError as exc:
    check("alias plus explicit identity", "rejected", f"rejected ({exc})")

ws.attest_agent_identity(actor="antigravity", agent_id="x", alias_of="t")
xi = ws.get_agent("x")["identity"]
check("alias inherits the target's identity",
      "control_principal=openai model_family=openai-codex alias_chain=['t']",
      f"control_principal={xi['control_principal']} "
      f"model_family={xi['model_family']} alias_chain={xi['alias_chain']}")

try:
    ws.attest_agent_identity(actor="antigravity", agent_id="t", alias_of="x")
    check("cycle t->x while x->t", "rejected", "ACCEPTED")
except ConfigurationError as exc:
    check("cycle t->x while x->t", "rejected", f"rejected ({exc})")

try:
    ws.attest_agent_identity(actor="antigravity", agent_id="x",
                             control_principal="openai", model_family="gpt")
    check("reparenting an attested alias away", "rejected", "ACCEPTED")
except ConfigurationError as exc:
    check("reparenting an attested alias away", "rejected", f"rejected ({exc})")

print("\n########## B. does the lineage check actually fire? ##########")
w = identity_snapshot("t", ws.get_agent("t")["identity"])
v = identity_snapshot("x", ws.get_agent("x")["identity"])
r = evaluate_independence(w, v)
check("target vs its own alias", "independent=False", 
      f"independent={r['independent']}, reasons={r['reasons']}")
check("  and the reason is named", "shared_alias_lineage", str(r["reasons"]))

ws.add_agent(actor="antigravity", agent_id="y", role="verifier", mode="manual",
             control_principal="claude", model_family="anthropic-claude")
ws.attest_agent_identity(actor="antigravity", agent_id="y", alias_of="t")
r2 = evaluate_independence(identity_snapshot("x", ws.get_agent("x")["identity"]),
                           identity_snapshot("y", ws.get_agent("y")["identity"]))
check("two aliases of the same target", "independent=False",
      f"independent={r2['independent']}, reasons={r2['reasons']}")
check("  and the reason is named", "shared_alias_lineage", str(r2["reasons"]))

print("\n########## C. the asymmetry: alias_of is never read ##########")
print("  evaluate_independence unions alias_chain with the actor id and ignores")
print("  alias_of.  Construct the inconsistent pair directly and see what happens.")
a = build_identity(control_principal="openai", model_family="openai-codex",
                   alias_of="t", alias_chain=[])
b = build_identity(control_principal="claude", model_family="anthropic-claude",
                   alias_of="t", alias_chain=[])
a = {"actor": "p", **a}
b = {"actor": "q", **b}
r3 = evaluate_independence(a, b)
check("both alias 't' but with empty chains",
      "independent=False",
      f"independent={r3['independent']}, reasons={r3['reasons']}")

print("\n  reachability: can a stored agent record hold alias_of with an empty chain?")
reached = "no supported path found"
try:
    ws.add_agent(actor="antigravity", agent_id="z", role="worker", mode="manual",
                 alias_of="t")
    zi = ws.get_agent("z")["identity"]
    if zi.get("alias_of") and not zi.get("alias_chain"):
        reached = f"YES via add_agent: {zi}"
    else:
        reached = f"no - add_agent produced alias_chain={zi.get('alias_chain')}"
except Exception as exc:
    reached = f"add_agent(alias_of=...) -> {type(exc).__name__}: {exc}"
check("reachable through a supported write path", "YES", reached)

shutil.rmtree(root, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
