#!/usr/bin/env python3
"""91 -> 22 -> 16 -> one raising function, and the API path is guarded.

Queue item 45. `NOTE-487-is-too-many-and-the-two-that-survive-are-guarded.md`
named its own gap: 91 dict-field arguments go to a callee defined in ANOTHER
module and were not propagated. The item asked whether following imports for
those 91 is a bounded job, and said to SAY THE NUMBER FIRST.

    91  dict-field args to a non-local callee
    22  whose callee RESOLVES to a sibling module (13 call sites, 7 callees)
    69  that do not resolve - stdlib, a method on an object, a builtin
    16  attribute accesses on a parameter tainted across that hop
     1  function that RAISES when driven with a malformed value and is not
        already covered by an open issue

22 is bounded, so this does not stop. Every one of the 16 is adjudicated below,
and the raising one is DRIVEN rather than reasoned about - the EFO package
imports and runs under plain python3 in this container.

THE RESULT IS A NEAR MISS, NOT A FINDING. `model.lease_expired` raises
AttributeError on a malformed `lease.expires_at`, and `validate_task` never
constrains the lease. But both call paths - `Workspace.get_task` and
`Workspace.list_tasks` - compare the whole task against the signed ledger
projection first, so a tampered lease raises IntegrityError before
`lease_expired` is reached. Recorded and NOT filed, the same standard item 38
applied to its `.get` chain.

A harness bug of mine, caught by a positive control: the first driver called
`lease_expired(lease, ...)` instead of `lease_expired(task, ...)`, so
`task.get("lease")` was None and EVERY case returned False - including the
control that should have returned True. The control failing is what said the
driver was wrong rather than the code.

    python3 probe_cross_module_hop.py
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
NOW = "2026-08-03T00:00:00Z"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def is_dict_field(node: ast.AST) -> bool:
    if isinstance(node, ast.Subscript):
        return True
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scoping number FIRST ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")

modules = sorted(p.name for p in PACKAGE.glob("*.py") if p.name != "__init__.py")
trees = {m: ast.parse((PACKAGE / m).read_text(encoding="utf-8")) for m in modules}
imports: dict[tuple[str, str], str] = {}
for module in modules:
    for node in ast.walk(trees[module]):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                imports[(module, alias.asname or alias.name)] = f"{node.module}.py"
functions = {(m, n.name): n for m in modules for n in ast.walk(trees[m])
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

resolved = unresolved = 0
sites = 0
for module in modules:
    local = {n.name for n in ast.walk(trees[module])
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in ast.walk(trees[module]):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.id if isinstance(node.func, ast.Name)
                else node.func.attr if isinstance(node.func, ast.Attribute)
                else None)
        if not name or name in local:
            continue
        count = (sum(1 for a in node.args if is_dict_field(a))
                 + sum(1 for k in node.keywords
                       if k.arg and is_dict_field(k.value)))
        if not count:
            continue
        sites += 1
        if imports.get((module, name)):
            resolved += count
        else:
            unresolved += count
check("item 45's population, said before any adjudication",
      "cross-module args: 91", f"cross-module args: {resolved + unresolved}")
check("  of which the callee resolves to a sibling module",
      "resolved: 22", f"resolved: {resolved}")
check("    the rest do not - stdlib, a method, a builtin",
      "unresolved: 69", f"unresolved: {unresolved}")
check("      and 22 is bounded, so this does not stop", "bounded: True",
      f"bounded: {resolved <= 50}")
print("  The 69 are NOT cleared. They are excluded because this analysis")
print("  cannot resolve their callee, which is a statement about the analysis.")

# ---------------------------------------------------------------- B
print("\n########## B. following the hop: 16 attribute accesses ##########")
tainted: set[tuple[str, str, str]] = set()
for module in modules:
    local = {n.name for n in ast.walk(trees[module])
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in ast.walk(trees[module]):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.id if isinstance(node.func, ast.Name)
                else node.func.attr if isinstance(node.func, ast.Attribute)
                else None)
        if not name or name in local:
            continue
        target = imports.get((module, name))
        fn = functions.get((target, name)) if target else None
        if fn is None:
            continue
        positional = [a.arg for a in (fn.args.posonlyargs + fn.args.args)]
        for index, arg in enumerate(node.args):
            if is_dict_field(arg) and index < len(positional):
                tainted.add((target, name, positional[index]))
        for keyword in node.keywords:
            if keyword.arg and is_dict_field(keyword.value):
                tainted.add((target, name, keyword.arg))
accesses: list[tuple[str, int, str, str]] = []
for target, name, param in sorted(tainted):
    for node in ast.walk(functions[(target, name)]):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id == param):
            accesses.append((target, node.lineno,
                             f"{param}.{node.attr}", name))
printed = 0
for target, line, expression, owner in sorted(accesses):
    print(f"    {target:<18}:{line:<5} {expression:<24} in {owner}()")
    printed += 1
check("tainted (module, function, parameter) triples", "triples: 12",
      f"triples: {len(tainted)}")
check("  attribute accesses on them", "accesses: 16",
      f"accesses: {len(accesses)}")
check("    every one listed, none summarised away", f"listed: {len(accesses)}",
      f"listed: {printed}")
already = [a for a in accesses if a[0] == "evidence.py"]
check("  of which already covered by an open issue (#15, gates/permissions)",
      "covered by #15: 4", f"covered by #15: {len(already)}")
print("  evidence.py's gates.get / permissions.get ARE #15 - `permissions` and")
print("  `gates` are never type-checked - so they are not a new result, they")
print("  are #15 reached from a second direction.")

# ---------------------------------------------------------------- C
print("\n########## C. EXECUTED, not reasoned - the package runs here ##########")
sys.path.insert(0, str(PACKAGE.parent))
from evidence_orchestrator import model  # noqa: E402


def drive(fn) -> str:
    try:
        return f"returned {fn()!r}"
    except Exception as error:                                  # noqa: BLE001
        return f"{type(error).__name__}: {str(error)[:44]}"


print("  POSITIVE CONTROLS FIRST. The first version of this driver passed the")
print("  LEASE where a TASK belongs, so task.get('lease') was None and every")
print("  case returned False - including the control that should be True.")
print("  The control failing is what said the driver was wrong, not the code.")
check("a lease in the past is expired", "returned True",
      drive(lambda: model.lease_expired(
          {"lease": {"expires_at": "2026-01-01T00:00:00Z"}}, now=NOW)))
check("  a lease in the future is not", "returned False",
      drive(lambda: model.lease_expired(
          {"lease": {"expires_at": "2026-12-01T00:00:00Z"}}, now=NOW)))
check("  and no lease at all is not", "returned False",
      drive(lambda: model.lease_expired({}, now=NOW)))
print("  Now the malformed values:")
raised = 0
for bad in (None, 123, {"a": 1}, [], "not-a-timestamp", True):
    outcome = drive(lambda b=bad: model.lease_expired(
        {"lease": {"expires_at": b}}, now=NOW))
    raised += "Error" in outcome
    print(f"    expires_at = {bad!r:<18} {outcome}")
missing = drive(lambda: model.lease_expired({"lease": {"token": "x"}}, now=NOW))
print(f"    lease without expires_at   {missing}")
check("every malformed lease raises rather than returning a bool",
      "raised: 6", f"raised: {raised}")
check("  and a lease missing the key raises too", "KeyError", missing)
import inspect  # noqa: E402
import re  # noqa: E402
validate_source = inspect.getsource(model.validate_task)
LEASE = re.compile(r"\blease\b")
# BOTH DIRECTIONS. An escaping slip left this as `.lease.b` - which returns 0
# for the right reason by accident. The filter is now checked against a known
# answer that MUST match before its zero on validate_task means anything.
check("  the lease filter matches when a lease IS mentioned",
      "control hits: 2", f"control hits: {len(LEASE.findall('lease and lease'))}")
check("  and validate_task never constrains the lease", "lease mentions: 0",
      f"lease mentions: {len(LEASE.findall(validate_source))}")
check("    while lease_expired obviously does", "lease_expired hits: 5",
      f"lease_expired hits: {len(LEASE.findall(inspect.getsource(model.lease_expired)))}")
print(f"    it names only: "
      f"{sorted(set(re.findall(chr(34) + '([a-z_]+)' + chr(34), validate_source)))}")

# ---------------------------------------------------------------- D
print("\n########## D. and the API path is GUARDED - a near miss, not a finding ##########")
workspace_source = (PACKAGE / "workspace.py").read_text(encoding="utf-8")
callers = [line.strip() for line in workspace_source.splitlines()
           if "lease_expired(" in line and "def " not in line]
for caller in callers:
    print(f"    workspace.py  {caller[:66]}")
guard = "projection differs from the signed ledger"
check("both readers compare the task against the signed ledger",
      "guard sites: 2", f"guard sites: {workspace_source.count(guard)}")
check("  get_task validates and compares before returning",
      "validate_task(task)", workspace_source.splitlines()[465].strip())
check("  list_tasks does the same",
      "validate_task(task)", workspace_source.splitlines()[492].strip())
print("  The comparison is over the WHOLE task minus last_event_hash, so a")
print("  tampered `lease` raises IntegrityError before lease_expired is ever")
print("  called. doctor.py:192 reaches it through list_tasks, so it is behind")
print("  the same gate.")
print("  I could not reach the raise through the API. It is therefore a NEAR")
print("  MISS, written up and NOT filed - the standard item 38 set for its")
print("  own .get chain. A finding asserted here would be a finding I could")
print("  not demonstrate.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT do ##########")
print("  * It does not clear the 69 unresolved arguments. Their callee is a")
print("    stdlib function, a method on an object, or a builtin, and this")
print("    analysis does not resolve those.")
print("  * It does not follow hop THREE. A parameter receiving a bare name")
print("    that is itself a tainted parameter is not traced.")
print("  * It does not file an issue, and does not re-confirm or retract #15.")
print("  * It did NOT write to any workspace. Section C calls two pure")
print("    functions with literal dicts; nothing touched a filesystem.")
print("  * MEASURED: every count, every listed access, every driven outcome,")
print("    the guard lines. REASONED: nothing - the guard was read and the")
print("    raise was executed.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static AST reads plus two pure-function drives of the package at main")
print("5694ab45. No workspace was created, no issue filed. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
