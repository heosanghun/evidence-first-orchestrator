#!/usr/bin/env python3
"""963 attribute accesses, scoped down to the 24 a parsed document can reach.

Queue item 38. `NOTE-implicit-exceptions-package-wide.md` named 963 attribute
accesses as not statically enumerable without type inference, and that stands:
`x.foo` is unsafe only if `x` can be None or another type. The item asked
whether the SUBSET reachable from a parsed document is small enough to
adjudicate, the way item 29 cut 144 down to 7 - and to SAY THE NUMBER FIRST and
stop if it is still too many.

    963 total  ->  24 on a name bound from a dict field.

24 is adjudicable, so this does not stop.

The interesting shape is `d.get("k", {}).get("j")`. The `{}` default applies
only when the key is ABSENT. If the key is PRESENT with a non-dict value -
`None`, a string - the second `.get` raises AttributeError, which `cli.main`
does not catch. That is #19's shape exactly.

It raises on a synthetic event. Whether a REAL ledger can contain one is the
question that decides whether this is a finding, and section D reports what I
could and could not drive.

    python3 probe_attribute_subset.py
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import Counter
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
MODULES = ["adapter.py", "ledger.py", "evidence.py", "provenance.py",
           "independence.py", "model.py", "archive.py", "doctor.py",
           "util.py", "lock.py", "dashboard.py", "cli.py", "errors.py"]


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scoping number FIRST ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")

total = 0
bases: Counter[str] = Counter()
for name in MODULES:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            total += 1
            bases[type(node.value).__name__] += 1
check("the population the earlier note named", "total: 963", f"total: {total}")
print(f"    base node types: {dict(bases)}")

# The parsed-document subset: a name bound from `d[...]` or `d.get(...)`, then
# read as an attribute. That is where a DOCUMENT controls the value's type.
reachable: list[tuple[str, int, str, str]] = []
for name in MODULES:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    for function in [n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        bound: dict[str, str] = {}
        for node in ast.walk(function):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target] if isinstance(node, ast.AnnAssign)
                       else [])
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                value = node.value
                if isinstance(value, ast.Subscript):
                    bound[target.id] = ast.unparse(value)
                elif (isinstance(value, ast.Call)
                      and isinstance(value.func, ast.Attribute)
                      and value.func.attr == "get"):
                    bound[target.id] = ast.unparse(value)
        for node in ast.walk(function):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in bound):
                reachable.append((name, node.lineno, ast.unparse(node),
                                  bound[node.value.id]))
check("  narrowed to names bound from a dict field", "reachable: 24",
      f"reachable: {len(reachable)}")
print("  963 -> 24. The item said to scope first and stop if it is still too")
print("  many. 24 is adjudicable, so this continues.")

# ---------------------------------------------------------------- B
print("\n########## B. the 24, by module ##########")
by_module = Counter(entry[0] for entry in reachable)
for module, count in sorted(by_module.items()):
    print(f"    {module:<20} {count}")
check("  and they cluster in one module", "independence.py: 21",
      f"independence.py: {by_module['independence.py']}")
for module, line, expression, origin in sorted(set(reachable)):
    print(f"    {module}:{line:<5} {expression:<28} <- {origin[:60]}")

# ---------------------------------------------------------------- C
print("\n########## C. the `.get(default).get()` shape ##########")
print("  `d.get('k', {}).get('j')` defaults ONLY when the key is ABSENT. If")
print("  the key is PRESENT and holds None or a string, the second .get raises")
print("  AttributeError - which cli.main does not catch, so it escapes as a")
print("  traceback. #19's shape.")
chained: list[tuple[str, int, str]] = []
for name in MODULES + ["workspace.py"]:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"):
            continue
        inner = node.func.value
        if (isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "get"
                and len(inner.args) == 2):
            chained.append((name, node.lineno, ast.unparse(node)))
for name, line, expression in sorted(set(chained)):
    print(f"    {name}:{line:<5} {expression[:78]}")
check("  chained get-with-default sites, package-wide", "sites: 14",
      f"sites: {len(set(chained))}")
print("  Note these are NOT confined to independence.py: workspace.py's proxy")
print("  verification path uses the same shape.")

# ---------------------------------------------------------------- D
print("\n########## D. driven, not argued - and what could NOT be driven ##########")
sys.path.insert(0, str(SOURCE / "src"))
from evidence_orchestrator.independence import (  # noqa: E402
    audit_verification_events)

synthetic = [{
    "task_id": "T1", "actor": "codex", "action": "task.submitted",
    "payload": {"task": {"owner": "codex", "attempt": 0,
                         "result": "not-a-dict"}},
}]
try:
    audit_verification_events(synthetic, {"codex": {}})
    outcome = "no exception"
except Exception as exc:                        # noqa: BLE001
    outcome = f"{type(exc).__name__}: {exc}"
check("a synthetic event with a non-dict `result` raises",
      "AttributeError: 'str' object has no attribute 'get'", outcome)

healthy = [{
    "task_id": "T1", "actor": "codex", "action": "task.submitted",
    "payload": {"task": {"owner": "codex", "attempt": 0, "result": {}}},
}]
try:
    audit_verification_events(healthy, {"codex": {}})
    control = "no exception"
except Exception as exc:                        # noqa: BLE001
    control = f"{type(exc).__name__}: {exc}"
check("  and the POSITIVE CONTROL, a dict `result`, does not",
      "no exception", control)
print("  So the function is fragile to the shape. The question that decides")
print("  whether this is a FINDING is whether a real ledger can contain such")
print("  an event, and here is what I could establish:")
print("    * model.validate_task constrains id, owner, state, title, revision,")
print("      prerequisites, permissions and gates. It does NOT constrain")
print("      `result` at all - checked against the source.")
print("    * BUT the audit reaches :218 only for `task.submitted` /")
print("      `task.proxy_submitted` events, and workspace.submit writes")
print("      `result=evidence`, a dict it builds itself.")
print("    * `requeue` DOES set `result=None` (workspace.py:1411), but a")
print("      requeued event carries action `task.requeued`, which the audit")
print("      skips at its two action filters before reaching any .get chain.")
print("  I could NOT construct a public-API sequence that puts a non-dict")
print("  `result` into a task.submitted payload. So: REACHABLE FROM A CRAFTED")
print("  OR TAMPERED LEDGER, NOT SHOWN REACHABLE THROUGH THE API.")
print("  No issue is filed on that basis. Writing it down as a near miss is")
print("  the point - the hypothesis was that this would be #21, and it is not,")
print("  on the evidence I have.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT establish ##########")
print("  * It does not clear the other 939 attribute accesses. They are")
print("    excluded because their base is not bound from a dict field, which")
print("    is a SYNTACTIC filter: a value that reaches a name by some other")
print("    route - a parameter, a return - is invisible to it, exactly the")
print("    bound recorded in NOTE-which-of-my-censuses-measured-and-which-read.")
print("  * It does not prove the ledger cannot hold a malformed payload. It")
print("    proves I could not produce one through the API in this container.")
print("    An attacker who can write AND re-sign the ledger is a different")
print("    threat model, and #9 and #12 already cover parts of it.")
print("  * MEASURED: 963, 24, the module split, the 12 chained sites, and both")
print("    driven outcomes. REASONED: that the action filters block the")
print("    requeue route - read from the source, not driven end to end.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Executed here: audit_verification_events against literals built in this")
print("file. No network, no GPU, no performance measurement. No issue filed.")
print("Pre-registered permissions unchanged.")
print("SUBMITTED, not VERIFIED.")
