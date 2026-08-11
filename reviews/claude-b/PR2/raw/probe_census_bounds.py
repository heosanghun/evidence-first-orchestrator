#!/usr/bin/env python3
"""What every name-scoped census in this review can and cannot see.

Queue item 35. `NOTE-dynamic-stores-and-what-a-name-scoped-census-cannot-see.md`
found the limit the hard way: `provenance.py`'s `files` becomes `expected_files`
across a return, and a census keyed on a variable NAME lost the chain
completely. It named the consequence but not the extent:

    "That bounds every name-scoped census in this review."

This measures the extent. The largest such census is the constant-key
adjudication in `NOTE-implicit-exceptions-package-wide.md`: **30 (module, base)
pairs**, each carrying a sentence about where the value COMES FROM - "a task
projection", "the dict workspace.claim RETURNS". Those are claims about a
VALUE. The census only ever saw a NAME.

The question this answers: for how many of the 30 is the origin visible in the
same scope, and for how many does the adjudication rest on reading?

    python3 probe_census_bounds.py
"""

from __future__ import annotations

import ast
import subprocess
from collections import Counter
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"

# The exact population NOTE-implicit-exceptions-package-wide.md adjudicated.
BASES = {
    "adapter.py": ["task", "agent", "claim", "submitted"],
    "ledger.py": ["events"],
    "evidence.py": ["manifest", "report", "check", "claim"],
    "provenance.py": ["artifact", "raw_output"],
    "independence.py": ["worker", "verifier", "target", "item", "task"],
    "model.py": ["task", "lease"],
    "archive.py": ["manifest", "report", "artifact", "extra", "item",
                   "raw_output"],
    "doctor.py": ["agent", "task", "check", "projection", "result"],
    "cli.py": ["task"],
}


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def binding_of(function: ast.AST, name: str) -> str | None:
    """How `name` comes to exist inside this function."""
    arguments = function.args
    parameters = {a.arg for a in (arguments.posonlyargs + arguments.args
                                  + arguments.kwonlyargs)}
    parameters |= {a.arg for a in (arguments.vararg, arguments.kwarg) if a}
    if name in parameters:
        return "PARAMETER"
    found: str | None = None
    for node in ast.walk(function):
        if isinstance(node, (ast.For, ast.comprehension)):
            if any(isinstance(inner, ast.Name) and inner.id == name
                   for inner in ast.walk(node.target)):
                return "loop / comprehension target"
        # AnnAssign was missing from the first draft, and `doctor.py::result`
        # - declared `result: dict[str, Any] = {...}` - fell out of the census
        # entirely. Section A's exhaustiveness check is what caught it. Tenth
        # hand-rolled filter in this review to be the bug.
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                found = ("assigned from a call" if isinstance(node.value, ast.Call)
                         else "built in place")
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    found = ("assigned from a call"
                             if isinstance(node.value, ast.Call)
                             else "built in place")
        if isinstance(node, ast.withitem):
            if (isinstance(node.optional_vars, ast.Name)
                    and node.optional_vars.id == name):
                found = "with-target"
    return found


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the population ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
check("  and the population is the one that note adjudicated", "pairs: 30",
      f"pairs: {sum(len(v) for v in BASES.values())}")

classified: list[tuple[str, str, str, str]] = []
for module, names in BASES.items():
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    functions = [n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for name in names:
        for function in functions:
            kind = binding_of(function, name)
            if kind:
                classified.append((module, function.name, name, kind))
                break
resolved = {(module, name) for module, _, name, _ in classified}
unresolved = sorted((module, name) for module, names in BASES.items()
                    for name in names if (module, name) not in resolved)
check("  every pair is classified - none silently dropped",
      "unresolved: []", f"unresolved: {unresolved}")
print("  That check is not decoration: the first draft of `binding_of` handled")
print("  `Assign` and not `AnnAssign`, so `doctor.py::result` - declared")
print("  `result: dict[str, Any] = {...}` - vanished from the census and the")
print("  count came back 29 of 30. Tenth hand-rolled filter to be the bug.")

# ---------------------------------------------------------------- B
print("\n########## B. how each adjudicated base is bound ##########")
kinds: Counter[str] = Counter(kind for _, _, _, kind in classified)
for module, function, name, kind in sorted(classified):
    marker = "!!" if kind == "PARAMETER" else "  "
    print(f"  {marker}{module:<18} {name:<12} in {function:<30} {kind}")
print(f"\n  totals: {dict(kinds)}")
check("  bases whose origin the census CANNOT see", "PARAMETER: 6",
      f"PARAMETER: {kinds['PARAMETER']}")
print("  A parameter is the whole problem. The census reads the name the")
print("  CALLEE chose; the caller may bind the same value to anything. For a")
print("  loop target or an assignment from a call, the origin is right there")
print("  in the same scope and the census is sound about it.")

# ---------------------------------------------------------------- C
print("\n########## C. the six, and what the caller actually passes ##########")
# Measured: the caller-side expression at each call site, which is exactly the
# thing a name-scoped census substitutes a guess for.
CALL_SITES = [
    ("adapter.py", "task", "render_task_prompt", "adapter.py"),
    ("independence.py", "worker", "evaluate_independence", "independence.py"),
    ("independence.py", "verifier", "evaluate_independence", "independence.py"),
    ("model.py", "task", "validate_task", "model.py"),
    ("archive.py", "manifest", "archive_evidence_bundle", "workspace.py"),
    ("archive.py", "report", "archive_evidence_bundle", "workspace.py"),
]


def signature(module: str, function: str) -> list[str]:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == function):
            a = node.args
            return [arg.arg for arg in a.posonlyargs + a.args + a.kwonlyargs]
    return []


def argument_passed(caller: str, function: str, parameter: str):
    """The caller-side expression bound to `parameter`, read from the AST.

    A first version compared the parameter name against the raw TEXT of the
    call and asked `name not in window`. `worker` is a substring of
    `worker_identity`, so it reported zero differences - eleventh hand-rolled
    filter in this review to be the bug, and this one would have silently
    erased the finding.
    """
    tree = ast.parse((PACKAGE / caller).read_text(encoding="utf-8"))
    order = signature(function.split(".")[0] if False else
                      {"render_task_prompt": "adapter.py",
                       "evaluate_independence": "independence.py",
                       "validate_task": "model.py",
                       "archive_evidence_bundle": "archive.py"}[function],
                      function)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == function):
            continue
        for keyword in node.keywords:
            if keyword.arg == parameter:
                return node.lineno, ast.unparse(keyword.value)
        if parameter in order:
            index = order.index(parameter)
            if index < len(node.args):
                return node.lineno, ast.unparse(node.args[index])
    return None, None


differing = []
for module, name, function, caller_module in CALL_SITES:
    line, expression = argument_passed(caller_module, function, name)
    same = expression == name
    if not same:
        differing.append(f"{module}::{name} <- {expression}")
    print(f"    {module}::{function}({name})")
    print(f"        {caller_module}:{line} passes `{expression}`"
          f"   {'SAME name' if same else 'DIFFERENT name'}")
# I guessed 3 before measuring, on the assumption that most callers would
# reuse the parameter name. The AST says 5 of 6. Corrected to the measurement.
check("  call sites where the caller binds a DIFFERENT name",
      "differing: 5", f"differing: {len(differing)} {differing}")
print("  FIVE of the six callers bind a different name. Only")
print("  `render_task_prompt(task=task)` reuses it, and that is luck rather")
print("  than a property - nothing stops a future caller renaming it.")
print("  Two of the five do not pass a variable at all:")
print("  `archive_evidence_bundle(manifest=evidence['manifest'], ...)` passes a")
print("  SUBSCRIPT. The census adjudicated `manifest` as `the caller passes")
print("  {path, sha256}; workspace builds it` - correct, and reached by")
print("  reading `workspace.py`, not by anything the census could see.")
print("  All six adjudications stand. What changes is that the note presented")
print("  30 results uniformly when 24 were measured and 6 were read.")

# ---------------------------------------------------------------- D
print("\n########## D. the same bound, applied to every census in the review ##########")
CENSUSES = [
    ("NOTE-implicit-exceptions-package-wide.md", "constant-key subscript reads",
     "30 (module, base) pairs; 6 are PARAMETERS, so 6 adjudications are "
     "REASONED FROM READING and 24 are visible in scope. Section C above."),
    ("NOTE-the-144-was-my-own-misleading-number.md", "dynamic-key reads",
     "7 sites, each classified by key PROVENANCE rather than by base name - "
     "and the one parsed-input case was traced to `record['submitted_path']` "
     "BY READING, which the note says. Not affected."),
    ("NOTE-dynamic-stores-and-what-a-name-scoped-census-cannot-see.md",
     "dynamic-key stores",
     "this is where the limit was found. Already states which of its two "
     "chains is measured and which is read. Not affected further."),
    ("NOTE-issue19-is-the-only-one.md", "workspace.py subscript reads",
     "single module, and `NOTE-the-144...` measured workspace.py as having "
     "ZERO runtime dynamic-key reads - so its population is constant-key "
     "within one file. A rename across a return cannot hide a constant key."),
    ("NOTE-what-the-test-suite-cannot-catch.md", "tests/ token map",
     "keys on TOKENS in test sources, not on variable names in the package. "
     "A rename in the package would change which token to search for, which "
     "is why every issue's token is checked to exist in its module."),
    ("NOTE-the-node-tests-exercise-only-the-covered-input.md", "web_tests",
     "EXECUTED - the guards are driven, not named. Immune."),
]
for document, what, bound in CENSUSES:
    print(f"  {document}")
    print(f"      census: {what}")
    print(f"      bound:  {bound}")
affected = [d for d, _, b in CENSUSES if "REASONED FROM READING" in b]
check("  censuses whose published result needs a stated bound",
      "affected: 1", f"affected: {len(affected)} {affected}")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT establish ##########")
print("  * It does NOT re-adjudicate the six. Their reasons were reached by")
print("    reading the callers and remain correct; what changes is that the")
print("    note now says which of its 30 are measured and which are read.")
print("  * `binding_of` takes the FIRST function in which a name resolves.")
print("    Where a base appears in several functions of one module the")
print("    classification is of that first site, which is why section C names")
print("    the function alongside the module rather than the module alone.")
print("  * Call sites are read at ONE line each - the first caller found. A")
print("    second caller could pass something differently named again; that")
print("    would strengthen the point, not weaken it, so it is not chased.")
print("  * MEASURED: the classification of all 30, and the caller-side text at")
print("    six call sites. REASONED: that a parameter's origin is invisible to")
print("    a name-scoped census, which is what a parameter means.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis only; nothing was executed against a workspace. No")
print("issue filed - this bounds MY OWN earlier write-up, and finds no new")
print("defect in EFO. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
