#!/usr/bin/env python3
"""EFO guards 66 places - and only ELEVEN of them guard an ARGUMENT.

Queue item 51. Items 45, 47 and 48 each ended at the same place: a function
that takes a non-string and raises a raw Python exception rather than an
`EFOError`. Item 48 found `provenance._validate_remote_url` to be the only
function across those three populations that converts one into a
`ConfigurationError`, and called that a positive pattern rather than a defect.

This censuses the guard itself instead of its absence: how many functions in
the package type-check at all, and - the question that turns out to matter -
WHAT they type-check.

    147  functions in the package (16 .py files; 13 of them hold one)
     24  contain an `isinstance` call            -  16%
     66  `isinstance` call sites in those 24
      4  modules with functions and NO isinstance: archive, dashboard,
         doctor, lock

Of the 66 call sites, by what the FIRST argument is:

     43  a LOCAL - a value the function itself read, parsed or assigned
     11  a PARAMETER of the enclosing function
      8  a dict FIELD (`d.get(...)` / `d[...]`)
      4  a name bound by a loop or comprehension in an outer scope

So EFO type-checks **the data it reads**, not **the arguments it is handed**.
That is not a defect - this review's threat model is a tampered file, and the
guards sit on the tampered-file path. It is the single sentence that explains
every "raw Python exception" result items 45, 47 and 48 recorded: those items
drove ARGUMENTS, and arguments are the 11, not the 43.

Both halves are DRIVEN here, not merely parsed:

    read_json(a file containing `[]`)  ->  ConfigurationError   (LOCAL guard)
    read_json(None)                    ->  AttributeError       (no PARAM guard)

    python3 probe_isinstance_census.py

SCOPE, stated first: 16 files, 147 functions, 66 call sites, 5 driven calls.
A MAP with one positive finding. No issue filed.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SRC = ANCHOR / "src" / "evidence_orchestrator"

EFO_ERRORS = {"EFOError", "ConfigurationError", "AuthorizationError",
              "TransitionError", "LeaseError", "EvidenceError",
              "IntegrityError", "LockTimeout"}


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {subprocess.run(['git', '-C', str(ANCHOR), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()!r}")

MODULES = sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in str(p))
check("  .py files under src/evidence_orchestrator", "files: 16",
      f"files: {len(MODULES)}")

# The error classes are READ from errors.py, not typed in here - a hardcoded
# list would go stale the moment a class is added, and the whole point of
# section C is which exceptions are the package's own.
declared = {n.name for n in ast.parse(
    (SRC / "errors.py").read_text(encoding="utf-8")).body
    if isinstance(n, ast.ClassDef)}
check("    and errors.py still declares exactly the set used below",
      f"declared: {sorted(EFO_ERRORS)}", f"declared: {sorted(declared)}")


def parents_of(tree: ast.AST) -> dict:
    table = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            table[child] = node
    return table


def enclosing_function(node: ast.AST, parents: dict):
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


functions = 0
with_guard = 0
call_sites = []
zero_guard = []
for module in MODULES:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    parents = parents_of(tree)
    fns = [n for n in ast.walk(tree)
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "isinstance"]
    guarded = {enclosing_function(c, parents) for c in calls} - {None}
    functions += len(fns)
    with_guard += len(guarded)
    if fns and not calls:
        zero_guard.append(module.name)
    for call in calls:
        call_sites.append((module.name, call, parents,
                           enclosing_function(call, parents)))

check("functions in the package", "functions: 147", f"functions: {functions}")
check("  of which contain an isinstance", "guarding: 24",
      f"guarding: {with_guard}")
check("    isinstance call sites in them", "call sites: 66",
      f"call sites: {len(call_sites)}")
check("      modules that hold functions but NO isinstance at all",
      "no guard: ['archive.py', 'dashboard.py', 'doctor.py', 'lock.py']",
      f"no guard: {sorted(zero_guard)}")
print("  Sixteen per cent of the package type-checks anything. That number on")
print("  its own says nothing - section B asks what the checks are ON.")

# ---------------------------------------------------------------- B
print("\n########## B. what is being type-checked: ARGUMENT or DATA ##########")


def first_argument_class(call: ast.Call, fn) -> tuple[str, str]:
    """Classify `isinstance(X, T)` by what X is.

    The categories are the ones the ARGUMENT needs, not present-or-absent: a
    guard on a parameter protects the caller's input, a guard on a local
    protects data the function itself read. Items 45/47/48 drove parameters
    and found no EFOError; this is the category that explains why.
    """
    argument = call.args[0] if call.args else None
    if fn is None:
        return "OTHER", ast.unparse(argument) if argument else "?"
    spec = fn.args
    params = {a.arg for a in
              spec.posonlyargs + spec.args + spec.kwonlyargs}
    if spec.vararg:
        params.add(spec.vararg.arg)
    if spec.kwarg:
        params.add(spec.kwarg.arg)
    bound = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            bound |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif (isinstance(node, (ast.AnnAssign, ast.AugAssign))
              and isinstance(node.target, ast.Name)):
            bound.add(node.target.id)
        elif isinstance(node, (ast.For, ast.comprehension)) and isinstance(
                node.target, ast.Name):
            bound.add(node.target.id)
    if isinstance(argument, ast.Name):
        if argument.id in params:
            return "PARAMETER", argument.id
        if argument.id in bound:
            return "LOCAL", argument.id
        return "OUTER-NAME", argument.id
    if isinstance(argument, ast.Subscript):
        return "FIELD", ast.unparse(argument)
    if (isinstance(argument, ast.Call)
            and isinstance(argument.func, ast.Attribute)
            and argument.func.attr == "get"):
        return "FIELD", ast.unparse(argument)
    return "OTHER", ast.unparse(argument) if argument else "?"


classes = Counter()
parameter_sites = []
for name, call, parents, fn in call_sites:
    kind, what = first_argument_class(call, fn)
    classes[kind] += 1
    if kind == "PARAMETER":
        parameter_sites.append((name, call.lineno,
                                fn.name if fn else "?", what))
for kind, count in classes.most_common():
    print(f"    {count:>3}  {kind}")
check("  every call site fell into a named class - the table is exhaustive",
      f"classified: {len(call_sites)}", f"classified: {sum(classes.values())}")
check("    guards on a LOCAL - data the function read or parsed itself",
      "LOCAL: 43", f"LOCAL: {classes['LOCAL']}")
check("    guards on a PARAMETER - the caller's input", "PARAMETER: 11",
      f"PARAMETER: {classes['PARAMETER']}")
check("    guards on a dict FIELD", "FIELD: 8", f"FIELD: {classes['FIELD']}")
check("    names bound in an outer loop or comprehension", "OUTER-NAME: 4",
      f"OUTER-NAME: {classes['OUTER-NAME']}")

print("\n  The ELEVEN that guard an argument, named in full:")
for module, line, fn, what in sorted(parameter_sites):
    print(f"    {module}:{line:<5} {fn}({what})")
check("  in how many distinct functions", "functions: 8",
      f"functions: {len({(m, f) for m, _, f, _ in parameter_sites})}")
check("    provenance.py holds the largest share",
      "provenance: 4",
      f"provenance: {sum(1 for m, _, _, _ in parameter_sites if m == 'provenance.py')}")

# ---------------------------------------------------------------- C
print("\n########## C. what happens when the check fails ##########")


def negated(call: ast.Call, parents: dict) -> bool:
    node, count = call, 0
    while node in parents:
        parent = parents[node]
        if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.Not):
            count += 1
        if isinstance(parent, (ast.If, ast.IfExp, ast.comprehension,
                               ast.FunctionDef)):
            break
        node = parent
    return count % 2 == 1


def raised_in(body) -> set:
    found = set()
    for statement in body:
        for node in ast.walk(statement):
            if not isinstance(node, ast.Raise):
                continue
            exc = node.exc
            name = None
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            found.add(name)
    return found


outcomes = Counter()
by_error = Counter()
for module, call, parents, fn in call_sites:
    node, host, kind = call, None, None
    while node in parents:
        parent = parents[node]
        if isinstance(parent, ast.Assert):
            kind = "assert"
            break
        if isinstance(parent, ast.comprehension):
            kind = "comprehension filter"
            break
        if isinstance(parent, ast.IfExp):
            kind = "ternary"
            break
        if isinstance(parent, ast.If) and node is parent.test:
            kind, host = "if", parent
            break
        node = parent
    if kind != "if":
        outcomes[kind or "used as a value"] += 1
        continue
    if negated(call, parents):
        names = raised_in(host.body)
        if names & EFO_ERRORS:
            outcomes["rejects with an EFOError"] += 1
            for name in names & EFO_ERRORS:
                by_error[name] += 1
        elif names:
            outcomes["rejects with a builtin exception"] += 1
        else:
            outcomes["rejects by skipping or defaulting"] += 1
    else:
        outcomes["branches (no rejection path)"] += 1
for kind, count in outcomes.most_common():
    print(f"    {count:>3}  {kind}")
check("  the outcome table is exhaustive too",
      f"accounted: {len(call_sites)}", f"accounted: {sum(outcomes.values())}")
check("    call sites that reject with the package's OWN error type",
      "EFOError: 35", f"EFOError: {outcomes['rejects with an EFOError']}")
check("      broken down by which error",
      "by error: {'EvidenceError': 17, 'ConfigurationError': 16, "
      "'IntegrityError': 1, 'AuthorizationError': 1}",
      f"by error: {dict(by_error.most_common())}")
check("    call sites that reject with a builtin",
      "builtin: 2", f"builtin: {outcomes['rejects with a builtin exception']}")
check("    and the five that reject WITHOUT raising",
      "no-raise: 5", f"no-raise: {outcomes['rejects by skipping or defaulting']}")
print("    (return None x1, continue x2, set to None x2 - a skipped record,")
print("     not an accepted one.)")
print("  So where EFO does guard, it converts almost every raising failure")
print("  into its own error type - 35 of the 37 that raise. The problem items")
print("  45, 47 and 48 kept hitting was never the CONVERSION of a bad value.")
print("  It was the POSITION of the check.")

# ---------------------------------------------------------------- D
print("\n########## D. DRIVEN - the LOCAL/PARAMETER split, not just parsed ##########")
sys.path.insert(0, str(ANCHOR / "src"))
from evidence_orchestrator import util  # noqa: E402
from evidence_orchestrator import provenance  # noqa: E402
from evidence_orchestrator.errors import ConfigurationError  # noqa: E402


def drive(label, fn, *args):
    try:
        return label, f"returned {fn(*args)!r}"
    except Exception as exc:  # noqa: BLE001 - the type IS the measurement
        return label, type(exc).__name__


with tempfile.TemporaryDirectory() as tmp:
    good = Path(tmp) / "good.json"
    good.write_text(json.dumps({"a": 1}), encoding="utf-8")
    array = Path(tmp) / "array.json"
    array.write_text("[]", encoding="utf-8")

    driven = [
        drive("read_json(a JSON object)      CONTROL", util.read_json, good),
        drive("read_json(a file holding [])  LOCAL guard", util.read_json,
              array),
        drive("read_json(None)               no PARAM guard", util.read_json,
              None),
        drive("_validate_source_path('x')    CONTROL",
              provenance._validate_source_path, "x"),
        drive("_validate_source_path(123)    PARAM guard",
              provenance._validate_source_path, 123),
    ]
for label, result in driven:
    print(f"    {label:<42}{result}")
results = dict(driven)
check("the control returns the parsed object",
      "returned {'a': 1}", results["read_json(a JSON object)      CONTROL"])
check("  a JSON ARRAY in the file trips the LOCAL guard",
      "ConfigurationError", results["read_json(a file holding [])  LOCAL guard"])
check("    but a non-path ARGUMENT raises a raw Python exception",
      "AttributeError", results["read_json(None)               no PARAM guard"])
check("  the parameter-guarding control accepts a str",
      "returned 'x'", results["_validate_source_path('x')    CONTROL"])
check("    and converts a non-string ARGUMENT into an EFOError",
      "ConfigurationError", results["_validate_source_path(123)    PARAM guard"])
print("  Same module pair, same round: one function rejects bad DATA with the")
print("  package's own error and lets a bad ARGUMENT through to AttributeError;")
print("  the other rejects the ARGUMENT. That is the 43/11 split, driven.")

# ---------------------------------------------------------------- E
print("\n########## E. what this reframes, and what it does NOT retract ##########")
note = (Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
        / "NOTE-hop-three-closes-and-the-one-unguarded-validator-is-unreachable.md"
        ).read_text(encoding="utf-8").replace("\n", " ")
check("item 48 scoped its `only` to three items, not to the package",
      "only** function found across items 45, 47 and 48", note)
print("  That wording is correct as written and is NOT corrected here. But it")
print("  reads as a statement about EFO, and the package-wide number is 35")
print("  rejecting sites, 16 of them ConfigurationError. `_validate_remote_url`")
print("  is one of FOUR parameter guards in provenance.py alone. What made it")
print("  singular was the POPULATION those three items walked - values")
print("  reachable from a document - not any scarcity in the package.")

print("\n########## F. what this does NOT do ##########")
print("  * It does not file an issue. Nothing here is a defect; the guards")
print("    sit where this review's threat model needs them.")
print("  * It does not claim the 43 LOCAL guards are sufficient, nor that the")
print("    11 are too few. It says which is which.")
print("  * `isinstance` is not the only way to type-check. A `try/except")
print("    TypeError`, a `str()` coercion or an annotation check would not be")
print("    counted. This censuses ONE mechanism and says so.")
print("  * A census over SYNTAX cannot see a VALUE: a LOCAL assigned from a")
print("    validated return is already safe, and a PARAMETER may be private.")
print("    Section D drives the two ends rather than inferring them.")
print("  * MEASURED: every count, both exhaustiveness assertions, all five")
print("    driven calls, item 48's wording. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static AST reads of the anchor plus five driven calls against a")
print("temporary directory. No workspace, no network, no issue filed.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED.")
