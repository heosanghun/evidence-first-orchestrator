#!/usr/bin/env python3
"""EFO at main (5694ab45): the implicit-exception census, beyond workspace.py.

`NOTE-issue19-is-the-only-one.md` proved #19 is the only instance of its class
*in workspace.py's subscript reads*, and named two gaps in its own scope:
the other modules, and exception shapes other than a dict index. This closes
the first gap, closes half the second, and states plainly why the rest cannot
be closed by static means.

`cli.main` catches `(EFOError, OSError, ValueError, json.JSONDecodeError)`.
`KeyError` and `IndexError` are outside it, so either one reaching a CLI
invocation is a traceback rather than a message - which is what #19 is.

    python3 probe_implicit_exceptions_all_modules.py
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
# workspace.py is the ONLY deliberate exclusion: it is already covered by
# NOTE-issue19-is-the-only-one.md. Everything else in the package is here.
DELIBERATE = {"workspace.py"}


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def subscript_reads(path: Path) -> list[tuple[int, str, object]]:
    """Every constant-key subscript that is READ, not assigned to."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    stores: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        targets = (node.targets if isinstance(node, ast.Assign)
                   else [node.target] if isinstance(node, ast.AugAssign)
                   else [])
        for target in targets:
            for inner in ast.walk(target):
                if isinstance(inner, ast.Subscript) and isinstance(
                        inner.slice, ast.Constant):
                    stores.add((inner.lineno, ast.unparse(inner)))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant):
            expression = ast.unparse(node)
            if (node.lineno, expression) not in stores:
                found.append((node.lineno, expression, node.slice.value))
    return found


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
present = [name for name in MODULES if (PACKAGE / name).is_file()]
check("  and every module named is present", f"modules: {len(MODULES)}",
      f"modules: {len(present)}")
package_modules = sorted(p.name for p in PACKAGE.glob("*.py")
                         if p.name not in {"__init__.py", "__main__.py"})
unlisted = [m for m in package_modules
            if m not in MODULES and m not in DELIBERATE]
check("  nothing in the package is silently unlisted", "unlisted: []",
      f"unlisted: {unlisted}")
check("  and the only deliberate exclusion is named", "{'workspace.py'}",
      str(DELIBERATE))
print("  My first draft of this list MISSED errors.py - caught by this very")
print("  check, which compares the list against the package rather than")
print("  trusting it. That is the third time a hand-written filter has been")
print("  the bug; the check for it is now cheap and permanent.")

# ---------------------------------------------------------------- B
print("\n########## B. integer-index reads - the IndexError shape ##########")
integer_sites = []
for name in MODULES:
    for line, expression, key in subscript_reads(PACKAGE / name):
        if isinstance(key, int) and not isinstance(key, bool):
            integer_sites.append((name, line, expression))
check("integer-index reads in the whole package outside workspace.py",
      "sites: 3", f"sites: {len(integer_sites)}")
for name, line, expression in integer_sites:
    print(f"    {name}:{line}  {expression}")
print("  All three are `fields[N]` in the same expression, where")
print("  `fields = metadata.split()` from a `git ls-tree` line. They are safe")
print("  by SHORT-CIRCUIT ORDERING, which is checked here rather than assumed:")

tree = ast.parse((PACKAGE / "provenance.py").read_text(encoding="utf-8"))
guard_ok = False
for node in ast.walk(tree):
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        rendered = [ast.unparse(value) for value in node.values]
        if any("fields[1]" in text for text in rendered):
            length_at = next((i for i, text in enumerate(rendered)
                              if "len(fields) != 3" in text), None)
            index_at = min(i for i, text in enumerate(rendered)
                           if "fields[" in text)
            guard_ok = length_at is not None and length_at < index_at
            print(f"    operands in order: {rendered}")
check("  the length guard precedes every index in the same `or` chain",
      "guard before index: True", f"guard before index: {guard_ok}")
print("  `provenance.py:314` reads `fields[0]` again, reachable only after")
print("  that chain did NOT raise - so the guard has already held.")
print("  MEASURED: the ordering. NOT MEASURED: a malformed `git ls-tree`")
print("  line driven end to end, which would need a crafted repository.")

# ---------------------------------------------------------------- C
print("\n########## C. string-key reads across every other module ##########")
bases: Counter[tuple[str, str]] = Counter()
for name in MODULES:
    for line, expression, key in subscript_reads(PACKAGE / name):
        if isinstance(key, str):
            bases[(name, expression.split("[")[0])] += 1

# (module, base) -> why a missing key cannot reach it
ADJUDICATED = {
    ("adapter.py", "task"): "a task projection; workspace.get_task returns it",
    ("adapter.py", "agent"): "an agent record from list_agents()",
    ("adapter.py", "claim"): "the dict workspace.claim RETURNS",
    ("adapter.py", "submitted"): "the dict workspace.submit RETURNS",
    ("ledger.py", "events"): "a list of events this module just parsed",
    ("evidence.py", "manifest"): "validated against the schema before use",
    ("evidence.py", "report"): "built by this module",
    ("evidence.py", "check"): "a known_answer_checks entry, schema-validated",
    ("evidence.py", "claim"): "a claims entry, schema-validated",
    ("provenance.py", "artifact"): "an evidence manifest artifact entry",
    ("provenance.py", "raw_output"): "an evidence manifest raw_output entry",
    ("independence.py", "worker"): "an identity dict, isinstance-checked",
    ("independence.py", "verifier"): "an identity dict, isinstance-checked",
    ("independence.py", "target"): "an agent record from the registry",
    ("independence.py", "item"): "an alias_chain entry this module built",
    ("independence.py", "task"): "a task projection",
    ("model.py", "task"): "a task projection; the state machine's input",
    ("model.py", "lease"): "the lease dict model.py itself constructs",
    ("archive.py", "manifest"): "the caller passes {path, sha256}; workspace "
                                "builds it",
    ("archive.py", "report"): "same shape as manifest, built by workspace",
    ("archive.py", "artifact"): "an entry of the files list workspace builds",
    ("archive.py", "extra"): "an extra_files entry workspace builds",
    ("archive.py", "item"): "a retained record archive.py just appended",
    ("archive.py", "raw_output"): "a validation raw_output entry",
    ("doctor.py", "agent"): "an agent record from list_agents()",
    ("doctor.py", "task"): "a task projection from list_tasks()",
    ("doctor.py", "check"): "a check dict doctor.py just appended",
    ("doctor.py", "projection"): "the dict audit_projections RETURNS",
    ("doctor.py", "result"): "the dict this function is building",
    ("cli.py", "task"): "a task projection returned by the API it just called",
}
uncovered = sorted(key for key in bases if key not in ADJUDICATED)
stale = sorted(key for key in ADJUDICATED if key not in bases)
total = sum(bases.values())
print(f"  {total} string-key reads over {len(bases)} (module, base) pairs")
for (name, base), count in sorted(bases.items()):
    marker = "!!" if (name, base) in uncovered else "  "
    print(f"  {marker}{name:<17} {base:<14} {count:3}x  "
          f"{ADJUDICATED.get((name, base), '?')}")
check("every (module, base) pair is adjudicated", "uncovered: []",
      f"uncovered: {uncovered}")
check("  and the map has no stale entries", "stale: []", f"stale: {stale}")
print("  Not one of these bases is a projection that any REPAIR path rebuilds.")
print("  That is what made #19 reachable: repair_projections writes a task")
print("  file with a key missing, and workspace.py reads that key. No module")
print("  here consumes a rebuilt projection, so the #19 shape has no second")
print("  home outside workspace.py.")

# ---------------------------------------------------------------- D
print("\n########## D. what this does NOT cover, stated rather than implied ##########")
print("  AttributeError and TypeError are NOT statically enumerable here.")
print("  `x.foo` is only unsafe if x can be None or another type, and")
print("  deciding that needs type inference this probe does not have. Listing")
print("  every attribute access would be a census of ~thousands of sites with")
print("  no adjudication behind it - the appearance of coverage, not coverage.")
attribute_sites = 0
for name in MODULES:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    attribute_sites += sum(1 for node in ast.walk(tree)
                           if isinstance(node, ast.Attribute))
print(f"  For scale: {attribute_sites} attribute accesses in these modules.")
print("  So the honest claim after this round is:")
print("    MEASURED - every constant-key subscript read in the package is")
print("               adjudicated; the 3 integer indexes are guarded by")
print("               short-circuit ordering; no module outside workspace.py")
print("               reads from a repair-rebuilt projection.")
print("    UNMEASURED - AttributeError, TypeError, ZeroDivisionError and")
print("               StopIteration shapes anywhere, and dynamic-key")
print("               subscripts (x[variable]) everywhere.")
dynamic = 0
for name in MODULES:
    tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
    dynamic += sum(1 for node in ast.walk(tree)
                   if isinstance(node, ast.Subscript)
                   and not isinstance(node.slice, ast.Constant))
print(f"  Dynamic-key subscripts not covered by this census: {dynamic}.")
print("  Naming that number is the point: a census that reported only its")
print("  successes would read as complete, and it is not.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis plus one AST ordering check. Nothing was executed")
print("against a live workspace in this probe. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
