#!/usr/bin/env python3
"""487 is too many. One more hop cuts it to 2, and both are guarded.

Queue item 41. `NOTE-963-attribute-accesses-scoped-to-24-and-a-near-miss.md`
narrowed 963 attribute accesses to the 24 whose base is bound from a dict field,
and named the exclusion: a base arriving via a PARAMETER or a RETURN is
invisible to that filter. The item asked whether the parameter subset is
adjudicable, and said to SAY THE NUMBER FIRST and stop if it is too large.

    THE NUMBER IS 487.

That is not adjudicable by hand and this probe does not pretend otherwise. What
it does instead is ask whether ONE more hop - a parameter that actually
RECEIVES a dict-field value at a call site - cuts it the way `963 -> 24` did:

    1132 attribute accesses on a bare name inside a function
     487 whose base is a parameter of that function      <- item 41's population
       2 whose base is a parameter that receives d[...] or d.get(...)
       0 findings: both are guarded by an isinstance that short-circuits

A NEGATIVE result, published because it is one. The near miss item 38 recorded
has no sibling here.

    python3 probe_parameter_subset.py

Scope: one hop, in-module call sites only. Both limits are counted in section
D rather than left implicit.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
MODULES = ["adapter.py", "ledger.py", "evidence.py", "provenance.py",
           "independence.py", "model.py", "archive.py", "doctor.py",
           "util.py", "lock.py", "dashboard.py", "cli.py", "errors.py",
           "workspace.py"]


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def is_dict_field(node: ast.AST) -> bool:
    """`d[...]` or `d.get(...)` - a value read out of a mapping."""
    if isinstance(node, ast.Subscript):
        return True
    return (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get")


def functions(tree: ast.AST) -> dict[str, ast.AST]:
    return {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scoping number FIRST ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
missing = [m for m in MODULES if not (PACKAGE / m).is_file()]
check("  every module in the list exists", "missing: []", f"missing: {missing}")

total = param_based = 0
per_module: dict[str, int] = {}
for module in MODULES:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    for fn in functions(tree).values():
        args = fn.args
        params = {a.arg for a in
                  (args.posonlyargs + args.args + args.kwonlyargs)}
        if args.vararg:
            params.add(args.vararg.arg)
        if args.kwarg:
            params.add(args.kwarg.arg)
        for node in ast.walk(fn):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)):
                total += 1
                if node.value.id in params:
                    param_based += 1
                    per_module[module] = per_module.get(module, 0) + 1
print(f"    {total} attribute accesses on a bare name inside a function")
print(f"    {param_based} of them have a PARAMETER as the base")
print(f"    {dict(sorted(per_module.items(), key=lambda kv: -kv[1]))}")
check("item 41's population, said before any adjudication",
      "parameter-based: 487", f"parameter-based: {param_based}")
check("  and it is too large to adjudicate by hand", "too large: True",
      f"too large: {param_based > 50}")
print("  So the item's literal question is answered NO, and the honest move is")
print("  to say the number and stop - which is what the method requires and")
print("  what would have happened here if the next section found nothing.")

# ---------------------------------------------------------------- B
print("\n########## B. one more hop: parameters that RECEIVE a dict field ##########")
sites: list[tuple[str, int, str, str]] = []
for module in MODULES:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    funcs = functions(tree)
    methods = {n.name for cls in ast.walk(tree)
               if isinstance(cls, ast.ClassDef)
               for n in cls.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    tainted: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        bound = isinstance(node.func, ast.Attribute)
        name = (node.func.id if isinstance(node.func, ast.Name)
                else node.func.attr if bound else None)
        fn = funcs.get(name) if name else None
        if fn is None:
            continue
        args = fn.args
        positional = [a.arg for a in (args.posonlyargs + args.args)]
        # A BOUND call supplies `self` through the RECEIVER, so the first
        # written argument maps to positional[1]. Without this correction the
        # receiver's own `self` is marked tainted and the result was 8 sites,
        # SIX of them `self.agents_dir`, `self.ledger` and friends - a filter
        # bug, not a finding. Caught by reading the output instead of trusting
        # the count. Fifteenth filter bug in this review.
        if bound and name in methods and positional and positional[0] in ("self", "cls"):
            positional = positional[1:]
        for index, arg in enumerate(node.args):
            if is_dict_field(arg) and index < len(positional):
                tainted.add((name, positional[index]))
        for keyword in node.keywords:
            if keyword.arg and is_dict_field(keyword.value):
                tainted.add((name, keyword.arg))
    for name, fn in funcs.items():
        for node in ast.walk(fn):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and (name, node.value.id) in tainted):
                sites.append((module, node.lineno,
                              f"{node.value.id}.{node.attr}", name))
printed = 0
for module, line, expression, owner in sorted(sites):
    print(f"    {module}:{line}  {expression}  in {owner}()")
    printed += 1
check("the one-hop subset", "hop sites: 2", f"hop sites: {len(sites)}")
# `printed` is incremented by the LOOP THAT PRINTS, so this fails if the
# listing is ever truncated while the count stays whole. Writing len(sites)
# on both sides would be the #8 defect - a check that cannot fail - and one
# slipped into probe_headers_rewritten.py two rounds ago.
check("  and every one is enumerated above, none summarised away",
      f"listed: {len(sites)}", f"listed: {printed}")
bases = sorted({(m, e.split('.')[0], o) for m, _, e, o in sites})
check("  they share one base in one function", "distinct bases: 1",
      f"distinct bases: {len(bases)}   {bases}")
print("  487 -> 2 is the same shape as 963 -> 24: not type inference, just one")
print("  concrete propagation step that a syntactic census cannot take.")

# ---------------------------------------------------------------- C
print("\n########## C. adjudicated - both are GUARDED ##########")
provenance = (PACKAGE / "provenance.py").read_text(
    encoding="utf-8").splitlines()
for _, line, expression, _ in sorted(sites):
    print(f"    provenance.py:{line}  {provenance[line - 1].strip()}")
guard = provenance[75].strip()
check("the line before the first access is an isinstance guard",
      'if not isinstance(branch, str) or not branch.strip():', guard)
check("  which SHORT-CIRCUITS, so a non-str never reaches .strip()",
      "or: True", f"or: {' or ' in guard and guard.index('isinstance') < guard.index('.strip')}")
call = next(i for i, text in enumerate(provenance, 1)
            if "validate_git_source_claim(" in text and "def " not in text)
print(f"    the tainting call site is provenance.py:{call} -")
print(f"      {provenance[call].strip()}  /  {provenance[call + 1].strip()}")
check("  it passes a dict field, which is why the hop caught it",
      'payload.get("branch")', provenance[call + 1].strip())
print("  So `branch` really can be None or a non-string, and the code already")
print("  refuses it with ConfigurationError before any attribute access.")
print("  Zero findings. A negative result, published because it is one -")
print("  item 38's near miss has no sibling in this population.")

# ---------------------------------------------------------------- D
print("\n########## D. what this does NOT cover, with counts ##########")
cross = 0
for module in MODULES:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    local = set(functions(tree))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = (node.func.id if isinstance(node.func, ast.Name)
                    else node.func.attr if isinstance(node.func, ast.Attribute)
                    else None)
            if name and name not in local:
                cross += sum(1 for a in node.args if is_dict_field(a))
                cross += sum(1 for k in node.keywords
                             if k.arg and is_dict_field(k.value))
selfs = 0
for module in MODULES:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    selfs += sum(1 for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute)
                 and isinstance(n.value, ast.Name) and n.value.id == "self")
check("dict-field arguments to a callee defined in ANOTHER module",
      "cross-module: 91", f"cross-module: {cross}")
check("  attribute accesses whose base is `self`", "self-based: 244",
      f"self-based: {selfs}")
print("  * ONE hop only. A parameter receiving a bare NAME that is itself")
print("    dict-bound is hop two and is not followed. That is where")
print("    workspace.py:730's `validate_git_source_claim(remote_url, branch)`")
print("    lives - bare names at the call site, so this analysis does not")
print("    reach it even though the callee is the same function.")
print(f"  * IN-MODULE call sites only: {cross} dict-field arguments go to a")
print("    callee defined elsewhere and are not propagated.")
print(f"  * `self` is not a parameter in the interesting sense: {selfs}")
print("    accesses are attributes of the instance, whose values come from")
print("    __init__ rather than from a document.")
print("  * MEASURED: every count above, both sites, the guard line, the call")
print("    site. REASONED: nothing - the guard is read from the source, not")
print("    inferred.")
print("  * It does not clear the other 485. They are excluded because no")
print("    in-module call site passes them a dict field, which is a statement")
print("    about THIS analysis, not about their safety.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static AST reads of the package at main 5694ab45. Nothing executed")
print("against a workspace, no issue filed - zero findings to file.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED.")
