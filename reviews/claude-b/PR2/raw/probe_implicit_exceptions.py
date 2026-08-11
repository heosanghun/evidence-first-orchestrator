#!/usr/bin/env python3
"""EFO `workspace.py` at main (5694ab45): is issue #19 the only one?

#19 is a `KeyError` from `task_for_validation["last_event_hash"]` that escapes
`cli.main` as a traceback, because `repair_projections` silently drops that
key. `NOTE-dashboard-and-errors-hold.md` had reported `escapes: []` from a
census of `raise` STATEMENTS, which structurally cannot see an exception
arriving from a dict index. This generalises the question.

Two things are measured, not argued:

  1. WHICH keys `repair_projections` drops, by diffing a real repaired
     projection against a real normal one. If `last_event_hash` is the only
     one, #19 is the sole instance of its class - a negative result worth
     having.
  2. EVERY string-key read in workspace.py, enumerated by AST rather than by
     grep, adjudicated, with the run FAILING on anything uncovered.

The first census in this round used a hand-written list of variable names and
MISSED `task_for_validation` - the very variable #19 lives on. That is the same
trap again, so section C walks the AST for every `X["literal"]` read with no
name filter at all.

    python3 probe_implicit_exceptions.py
"""

from __future__ import annotations

import ast
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-implicit-")).resolve()
SOURCE = Path("/tmp/efo-prov/src/evidence_orchestrator/workspace.py")
CLI = Path("/tmp/efo-prov/src/evidence_orchestrator/cli.py")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def build() -> Workspace:
    workspace = Workspace.initialize(ROOT / "ws", name="implicit",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    workspace.attest_agent_identity(actor="antigravity",
                                    agent_id="antigravity",
                                    control_principal="google",
                                    model_family="google-antigravity")
    workspace.attest_agent_identity(actor="antigravity", agent_id="claude",
                                    control_principal="openai",
                                    model_family="openai-codex")
    return workspace


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - none of these is a caught family ##########")
caught = "(EFOError, OSError, ValueError, json.JSONDecodeError)"
check("cli.main's catch tuple is unchanged since the earlier census", caught,
      next(line.strip() for line in CLI.read_text(encoding="utf-8").splitlines()
           if "except (" in line and "as exc" in line))
implicit = {"KeyError": KeyError, "IndexError": IndexError,
            "AttributeError": AttributeError, "TypeError": TypeError,
            "ZeroDivisionError": ZeroDivisionError,
            "StopIteration": StopIteration}
uncaught = sorted(name for name, kind in implicit.items()
                  if not issubclass(kind, (OSError, ValueError)))
check("  every implicit exception type would escape it",
      "['AttributeError', 'IndexError', 'KeyError', 'StopIteration', "
      "'TypeError', 'ZeroDivisionError']", str(uncaught))
print("  ValueError IS caught, so a UnicodeDecodeError (a ValueError) would")
print("  not escape. The six above would. That is the shape of the gap.")

# ---------------------------------------------------------------- B
print("\n########## B. exactly which keys does repair drop? ##########")
ws = build()
ws.create_task(actor="antigravity", task_id="T1", title="T1",
               description="work", owner="claude")
present: set[str] = set(ws.get_task("T1"))
token = ws.claim(actor="claude", task_id="T1")["lease_token"]
present |= set(ws.get_task("T1"))
ws.start(actor="claude", task_id="T1", lease_token=token)
present |= set(ws.get_task("T1"))
ws.block(actor="claude", task_id="T1", lease_token=token, reason="r")
present |= set(ws.get_task("T1"))
check("a task carries this many distinct keys across its lifecycle",
      "keys: 21", f"keys: {len(present)}")

projection = ws.root / "tasks" / "T1.json"
normal = set(json.loads(projection.read_text(encoding="utf-8")))
projection.unlink()
Workspace(ws.root).repair_projections(actor="antigravity")
repaired = set(json.loads(projection.read_text(encoding="utf-8")))
check("  repair drops exactly one key", "dropped: ['last_event_hash']",
      f"dropped: {sorted(normal - repaired)}")
check("  and invents none", "added: []", f"added: {sorted(repaired - normal)}")
print("  So #19 is the SOLE instance of its class, not the first of many.")
print("  That is a negative result and it is the useful half of this probe:")
print("  a reviewer does not need to re-walk the repair path looking for more.")

# ---------------------------------------------------------------- C
print("\n########## C. every string-key READ in workspace.py, by AST ##########")
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
stores: set[tuple[int, str]] = set()
for node in ast.walk(tree):
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AugAssign):
        targets = [node.target]
    for target in targets:
        for inner in ast.walk(target):
            if isinstance(inner, ast.Subscript) and isinstance(
                    inner.slice, ast.Constant):
                stores.add((inner.lineno, ast.unparse(inner)))

reads: list[tuple[int, str, str]] = []
for node in ast.walk(tree):
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) \
            and isinstance(node.slice.value, str):
        expression = ast.unparse(node)
        if (node.lineno, expression) not in stores:
            reads.append((node.lineno, expression, node.slice.value))

by_base: Counter[str] = Counter()
for _, expression, _ in reads:
    by_base[expression.split("[")[0]] += 1

# base expression -> why a missing key is impossible, or where it is handled
ADJUDICATED = {
    "task": "task-projection key; section D proves every one is guaranteed",
    "task_for_validation": "same projection - and last_event_hash is #19",
    "candidate": "a task projection from list_tasks()",
    "existing": "task.get('proxy_grant'), guarded by isinstance(dict) and "
                "a consumed_at check before the index",
    "self.config": "workspace config, ledger-bound; section E",
    "defaults": "self.config['defaults'], written by initialize()",
    "agent": "agent record written by add_agent(); id/role always set",
    "worker": "an agent record from list_agents()",
    "record": "an agent record from list_agents()",
    "target_identity": "guarded by an isinstance(dict) check before use",
    "event": "a ledger event this method just appended",
    "grant": "built by authorize_proxy_submission in this process",
    "provenance": "the dict validate_git_provenance RETURNS, not user input",
    "evidence": "the dict validate_submission RETURNS, not user input",
    "verification": "a local dict built in verify() before any read",
    "independence": "the dict evaluate_independence RETURNS",
    "transport_independence": "the dict evaluate_independence RETURNS",
    "renewed": "the dict this method just built",
    "self.get_task(task_id)": "get_task raises EFOError for a missing task",
}
uncovered = sorted(base for base in by_base if base not in ADJUDICATED)
stale = sorted(base for base in ADJUDICATED if base not in by_base)
print(f"  {len(reads)} read sites across {len(set(e for _, e, _ in reads))} "
      f"distinct expressions, on {len(by_base)} base objects:")
for base, count in sorted(by_base.items(), key=lambda kv: (-kv[1], kv[0])):
    marker = "!!" if base in uncovered else "  "
    print(f"  {marker}{count:3}x  {base:<24} {ADJUDICATED.get(base, '?')}")
check("every base object is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")
check("  and the map has no stale entries", "stale: []", f"stale: {stale}")
print("  The FIRST census this round filtered by a hand-written list of")
print("  variable names and missed `task_for_validation` - the variable #19")
print("  lives on. This one filters by nothing.")

# ---------------------------------------------------------------- D
print("\n########## D. is every task key that code reads actually guaranteed? ##########")
TASK_BASES = {"task", "task_for_validation", "candidate"}
task_keys = sorted({key for _, expression, key in reads
                    if expression.split("[")[0] in TASK_BASES
                    and expression.count("[") == 1})
print("  `existing` is EXCLUDED here and that is a correction: my first draft")
print("  called it a task projection. workspace.py:750 assigns it")
print("  `task.get('proxy_grant')` - it is a GRANT, guarded by an isinstance")
print("  check, and its `expires_at` is not a task key at all. Lumping it in")
print("  produced a false 'absent' that I would have had to explain away.")
print(f"  keys read off a task projection: {task_keys}")
absent_normal = [key for key in task_keys if key not in normal]
absent_repaired = [key for key in task_keys if key not in repaired]
check("every key read is present on a NORMAL projection", "absent: []",
      f"absent: {absent_normal}")
check("  on a REPAIRED projection, exactly one is not",
      "absent: ['last_event_hash']", f"absent: {absent_repaired}")
print("  This is the whole of #19 stated as a set difference, and it confirms")
print("  there is no second key in the same position.")

# ---------------------------------------------------------------- E
print("\n########## E. the config reads ##########")
config_keys = sorted({key for _, expression, key in reads
                      if expression.startswith("self.config[")
                      and expression.count("[") == 1})
print("  Only TOP-LEVEL config keys: `self.config['defaults']['lease_seconds']`")
print("  is one read of `defaults`, not a read of a config key named")
print("  `lease_seconds`. Taking the innermost literal was my second")
print("  misclassification this round, and it invented a missing key.")
live = set(ws.config)
check("every config key read exists in a real workspace config", "missing: []",
      "missing: " + str([key for key in config_keys if key not in live]))
print(f"  keys read: {config_keys}")
print("  A workspace config is bound to the signed ledger - editing it is")
print("  refused with `Workspace configuration differs from the signed")
print("  ledger` (measured previously in probe_doctor_coverage.py), so a")
print("  hand-removed key cannot reach these reads. Nested reads use")
print("  `.get(...)` with a default at workspace.py:736 and :1147.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Adjudication basis, stated plainly: sections B, D and E are MEASURED")
print("against a live workspace. Section C's per-base reasons are read from")
print("the source - each says why a missing key is impossible or where it is")
print("handled - and are NOT individually executed. Only #19's row was driven")
print("to an actual traceback, in probe_architecture_claims.py.")
print("SUBMITTED, not VERIFIED.")
