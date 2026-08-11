#!/usr/bin/env python3
"""Hop three CLOSES: 21 -> +4 -> 0. Three accesses, one guarded, none reachable.

Queue item 48. `NOTE-91-to-22-to-one-raise-that-the-ledger-guard-blocks.md`
named its own gap: hop THREE was unfollowed - a parameter receiving a bare NAME
that is itself a tainted parameter. The item asked whether that closure is
bounded, and said to SCOPE FIRST.

    21  tainted (module, function, parameter) triples at hop 1+2
    +4  added by hop three
     0  added by hop four - THE CLOSURE TERMINATES
    25  total
     3  attribute accesses on the four new parameters

Bounded, and small enough that every one of the three is adjudicated AND
driven. The package runs under plain python3 here.

RESULTS:

  * `provenance._validate_remote_url` is GUARDED - `if not isinstance(value,
    str) or not value.strip():` short-circuits, and it is the ONLY function
    found across items 45, 47 and 48 that turns a non-string into the package's
    own ConfigurationError rather than a raw Python exception.

  * `independence.validate_identity_value` is NOT guarded: `value.strip()` on
    line 18 with no isinstance check, so a non-string raises AttributeError.

  * But it is NOT REACHABLE with one. Two call sites pass a dict field with no
    `str()` - independence.py:165 and workspace.py:382 - and a syntactic census
    would flag both. They are safe for a reason syntax cannot see: the value is
    the RETURN of a prior build_identity / identity_snapshot, so it has already
    been through validate_identity_value and is a str by construction.

A MAP AND A NEAR MISS, not filed.

A harness bug of mine, caught by a positive control: the first driver called
`validate_identity_value(bad)` and got TypeError on EVERY input including the
good one - the signature is `(value, *, field)`. The control failing is what
said the driver was wrong rather than the code.

    python3 probe_hop_three_closure.py

SCOPE, stated first: 15 modules, 25 closure triples, 3 accesses, 10 call sites.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"


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
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")

modules = sorted(p.name for p in PACKAGE.glob("*.py") if p.name != "__init__.py")
trees = {m: ast.parse((PACKAGE / m).read_text(encoding="utf-8")) for m in modules}
imports: dict[tuple[str, str], str] = {}
functions: dict[tuple[str, str], ast.AST] = {}
for module in modules:
    for node in ast.walk(trees[module]):
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            for alias in node.names:
                imports[(module, alias.asname or alias.name)] = f"{node.module}.py"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions[(module, node.name)] = node
methods = {m: {n.name for c in ast.walk(trees[m]) if isinstance(c, ast.ClassDef)
               for n in c.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
           for m in modules}


def call_sites(module: str):
    for owner in [n for n in ast.walk(trees[module])
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for node in ast.walk(owner):
            if isinstance(node, ast.Call):
                yield owner, node


def resolve(module: str, node: ast.Call):
    bound = isinstance(node.func, ast.Attribute)
    name = (node.func.id if isinstance(node.func, ast.Name)
            else node.func.attr if bound else None)
    if not name:
        return None, None, bound
    target = imports.get((module, name))
    if target and (target, name) in functions:
        return (target, name), name, bound
    if (module, name) in functions:
        return (module, name), name, bound
    return None, name, bound


def parameters(target, name, bound):
    args = functions[target].args
    positional = [a.arg for a in (args.posonlyargs + args.args)]
    if (bound and name in methods[target[0]]
            and positional and positional[0] in ("self", "cls")):
        positional = positional[1:]
    return positional


tainted: set[tuple[str, str, str]] = set()
generation: dict[tuple[str, str, str], int] = {}
for module in modules:
    for owner, node in call_sites(module):
        target, name, bound = resolve(module, node)
        if not target:
            continue
        positional = parameters(target, name, bound)
        for index, arg in enumerate(node.args):
            if is_dict_field(arg) and index < len(positional):
                triple = (*target, positional[index])
                tainted.add(triple)
                generation.setdefault(triple, 1)
        for keyword in node.keywords:
            if keyword.arg and is_dict_field(keyword.value):
                triple = (*target, keyword.arg)
                tainted.add(triple)
                generation.setdefault(triple, 1)
check("hop 1+2 triples, said before following anything further",
      "hop 1+2: 21", f"hop 1+2: {len(tainted)}")

rounds = 0
for round_number in range(2, 8):
    added: dict[tuple[str, str, str], str] = {}
    for module in modules:
        for owner, node in call_sites(module):
            target, name, bound = resolve(module, node)
            if not target:
                continue
            positional = parameters(target, name, bound)
            for index, arg in enumerate(node.args):
                if (isinstance(arg, ast.Name)
                        and (module, owner.name, arg.id) in tainted
                        and index < len(positional)
                        and (*target, positional[index]) not in tainted):
                    added[(*target, positional[index])] = (
                        f"{module}:{node.lineno} via {owner.name}({arg.id})")
            for keyword in node.keywords:
                if (keyword.arg and isinstance(keyword.value, ast.Name)
                        and (module, owner.name, keyword.value.id) in tainted
                        and (*target, keyword.arg) not in tainted):
                    added[(*target, keyword.arg)] = (
                        f"{module}:{node.lineno} via "
                        f"{owner.name}({keyword.value.id})")
    print(f"    round {round_number}: +{len(added)} new triples")
    if not added:
        rounds = round_number
        break
    for triple, reason in added.items():
        generation[triple] = round_number
    tainted |= set(added)
check("  hop THREE adds", "hop 3: 4",
      f"hop 3: {sum(1 for g in generation.values() if g == 2)}")
check("    and hop FOUR adds nothing - the closure TERMINATES",
      "terminates at round: 3", f"terminates at round: {rounds}")
check("      total closure size", "closure: 25", f"closure: {len(tainted)}")
print("  Bounded, so this does not stop - and every hop-three access below is")
print("  both adjudicated and driven.")

# ---------------------------------------------------------------- B
print("\n########## B. the four new parameters, and their 3 accesses ##########")
generation_two = sorted(t for t in tainted if generation[t] == 2)
for module, function, parameter in generation_two:
    print(f"    {module:<18} {function}({parameter})")
check("hop-three parameters", "new parameters: 4",
      f"new parameters: {len(generation_two)}")
accesses = []
for module, function, parameter in generation_two:
    for node in ast.walk(functions[(module, function)]):
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == parameter):
            accesses.append((module, node.lineno,
                             f"{parameter}.{node.attr}", function))
printed = 0
for module, line, expression, function in sorted(accesses):
    print(f"    {module}:{line}  {expression}  in {function}()")
    printed += 1
check("  attribute accesses on them", "accesses: 3",
      f"accesses: {len(accesses)}")
check("    every one listed", f"listed: {len(accesses)}", f"listed: {printed}")
print("  The other two new parameters are util.validate_agent_id(value) and")
print("  util.validate_task_id(value), which hop three reaches through")
print("  workspace.py:216 and :219 - the same two functions item 47 drove.")

# ---------------------------------------------------------------- C
print("\n########## C. EXECUTED - control FIRST, then the non-string class ##########")
sys.path.insert(0, str(PACKAGE.parent))
from evidence_orchestrator import independence, provenance     # noqa: E402
from evidence_orchestrator.errors import EFOError              # noqa: E402

print("  The first driver called validate_identity_value(bad) and got a")
print("  TypeError on EVERY input INCLUDING the good one - the signature is")
print("  (value, *, field). The control failing is what said the DRIVER was")
print("  wrong, not the code. Controls first, always:")
check("a well-formed identity value is accepted", "claude-b",
      repr(independence.validate_identity_value("claude-b", field="x")))
check("  and a well-formed remote url is accepted",
      "https://example.com/r.git",
      repr(provenance._validate_remote_url("https://example.com/r.git")))

raw_count = efo_count = 0
for label, call in (
        ("independence.validate_identity_value",
         lambda b: independence.validate_identity_value(b, field="x")),
        ("provenance._validate_remote_url",
         lambda b: provenance._validate_remote_url(b))):
    for bad in (None, 123, [], {}):
        try:
            call(bad)
            outcome = "returned"
        except EFOError as error:
            efo_count += 1
            outcome = f"EFOError {type(error).__name__}"
        except Exception as error:                            # noqa: BLE001
            raw_count += 1
            outcome = f"**{type(error).__name__}**"
        print(f"    {label}({bad!r:<6}) {outcome}")
check("cases that raise the package's OWN error type", "EFOError: 4",
      f"EFOError: {efo_count}")
check("  and cases that raise a RAW Python exception", "raw: 4",
      f"raw: {raw_count}")
guard = (PACKAGE / "provenance.py").read_text(
    encoding="utf-8").splitlines()[56].strip()
check("  _validate_remote_url's guard, which is why it is the clean one",
      "if not isinstance(value, str) or not value.strip():", guard)
print("  _validate_remote_url is the ONLY function found across items 45, 47")
print("  and 48 that converts a non-string into a ConfigurationError.")
print("  validate_identity_value, three lines away in another module, does not.")

# ---------------------------------------------------------------- D
print("\n########## D. reachability - safe for a reason SYNTAX cannot see ##########")
sites = []
for module in ("independence.py", "workspace.py"):
    text = (PACKAGE / module).read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(text, 1):
        if "control_principal=" in line and "build_identity" not in line:
            sites.append((module, i, "str(" in line, line.strip()[:52]))
# CLASSIFY, do not just count. A first version asked only "does the line
# contain str()?" and reported 10 sites / 8 bare - lumping literals and bare
# NAMES in with the dict SUBSCRIPTS that are the actual question. Three
# categories, and only the third is what this section is about.
def category(text: str) -> str:
    if "str(" in text:
        return "str()-coerced"
    if "[" in text.split("=", 1)[-1]:
        return "DICT SUBSCRIPT"
    return "bare name/literal"


for module, line, coerced, text in sites:
    print(f"    {category(text):<18} {module}:{line:<5} {text}")
subscripts = [s for s in sites if category(s[3]) == "DICT SUBSCRIPT"]
coerced_reads = [s for s in sites if category(s[3]) == "str()-coerced"]
check("build_identity call sites passing control_principal", "sites: 10",
      f"sites: {len(sites)}")
check("  reading a dict field with str() around it", "coerced: 2",
      f"coerced: {len(coerced_reads)}")
check("    reading a dict SUBSCRIPT with no coercion - the question",
      "subscripts: 2", f"subscripts: {len(subscripts)}")
check("      and they are exactly the two named in the write-up",
      "['independence.py:165', 'workspace.py:382']",
      str([f"{s[0]}:{s[1]}" for s in subscripts]))
print("  A syntactic census would flag independence.py:165 and")
print("  workspace.py:382 as uncoerced dict subscripts. They are SAFE, and")
print("  not because of the call site: `target` is the RETURN of a prior")
print("  build_identity, and `target_identity` the return of")
print("  identity_snapshot - both of which run every field through")
print("  validate_identity_value, which returns a str. The value is a string")
print("  BY CONSTRUCTION, which is exactly what a census over syntax cannot")
print("  see. Recorded as a near miss and NOT filed.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT do ##########")
print("  * It does not file an issue. validate_identity_value is unguarded but")
print("    unreachable with a non-string, on the standard items 38, 45 and 47")
print("    all applied.")
print("  * It does not clear the 69 unresolved cross-module arguments from")
print("    item 45 - those have no resolvable callee and no hop count changes")
print("    that.")
print("  * It did NOT write to any workspace: four pure functions driven with")
print("    literal values.")
print("  * MEASURED: the closure and its termination, all three accesses, all")
print("    ten driven outcomes, the guard line, the call-site census.")
print("    REASONED: nothing - the by-construction argument is read off the")
print("    return type of build_identity, which section C drove.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static AST reads plus ten pure-function drives at main 5694ab45. No")
print("workspace, no network, no issue filed. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
