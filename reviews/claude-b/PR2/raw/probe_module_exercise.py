#!/usr/bin/env python3
"""Seven of fifteen modules are never named by the suite - and five issues live there.

Queue item 44. Item 42 found that `provenance.py` (six top-level functions) and
`archive.py` (three) are never CALLED by any test - each appears exactly once,
as a patch target - and asked whether that is true of other modules, i.e.
whether it is a structural fact about the suite rather than a coincidence about
the two components carrying #4, #5, #10 and #18.

It is structural, and the set is larger:

    15  top-level modules in the package
     8  exercised by NAME: called, raised in assertRaises, or reached through
        a Workspace attribute
     7  never - `__main__`, `dashboard`, `lock`, `model`, `util`, and
        `archive` / `provenance` whose single mention each is a patch target

The issues living in the never-named set: **#4, #5, #10, #15, #18**. Item 42
predicted four; `model.py` (#15) is the fifth, and `validate_task` - the exact
function #15 is about - appears nowhere in the suite.

WHAT THIS IS NOT: a claim that the code is unexecuted. Item 42 measured the
opposite - `submit`, `verify` and `proxy_submit` are driven by 40 test call
sites and reach these modules unconditionally. The claim is narrower: no test
NAMES them, so no test can fail ABOUT their own contract.

A near miss, recorded because it nearly became a wrong finding: a name census
scored `ledger.py` as never-exercised on one hit, and that hit was
`title="Ledger test"` - a STRING in a fixture. The real exercise is
`workspace.ledger.verify()`, eight times, which a census over NAMES cannot see.
That is the same shape as #6's `.get` chain: a census over syntax cannot see a
value reached through an attribute.

    python3 probe_module_exercise.py

SCOPE, stated first: 15 modules, 95 top-level names, 12 test files. Small
enough to adjudicate every name, and every name below IS adjudicated.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
PACKAGE = SOURCE / "src/evidence_orchestrator"
TESTS = SOURCE / "tests"


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
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")

modules = sorted(p.name for p in PACKAGE.glob("*.py") if p.name != "__init__.py")
test_files = sorted(TESTS.glob("*.py"))
test_text = "\n".join(p.read_text(encoding="utf-8") for p in test_files)
tops: dict[str, list[ast.stmt]] = {}
for module in modules:
    tops[module] = [n for n in ast.parse(
        (PACKAGE / module).read_text(encoding="utf-8")).body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
check("top-level modules in the package", "modules: 15",
      f"modules: {len(modules)}")
check("  test files", "test files: 12", f"test files: {len(test_files)}")
check("  top-level names to adjudicate", "names: 95",
      f"names: {sum(len(v) for v in tops.values())}")
print("  Small enough to adjudicate every name, and every one below is.")

# ---------------------------------------------------------------- B
print("\n########## B. how a Workspace attribute hides a module from a name census ##########")
# self.X = SomeClass(...) - the module is reached as `.X`, never by class name.
attributes: dict[str, str] = {}
for node in ast.walk(ast.parse((PACKAGE / "workspace.py").read_text(
        encoding="utf-8"))):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)):
                attributes[target.attr] = node.value.func.id
for attribute, built_from in sorted(attributes.items()):
    reached = len(re.findall(rf"\.{re.escape(attribute)}\b", test_text))
    print(f"    self.{attribute:<10} = {built_from:<10} tests reach "
          f"`.{attribute}`: {reached}")
check("Workspace attributes built from a constructor", "attributes: 2",
      f"attributes: {len(attributes)}")
ledger_reached = len(re.findall(r"\.ledger\b", test_text))
check("  and the one the tests actually drive", "ledger reached: 8",
      f"ledger reached: {ledger_reached}")
print("  THE NEAR MISS: a pure name census scored ledger.py as never-exercised")
print("  on ONE hit, and that hit is `title=\"Ledger test\"` - a STRING in a")
print("  fixture, not the class. The real exercise is workspace.ledger.verify()")
print("  and .append(). A census over NAMES cannot see a value reached through")
print("  an ATTRIBUTE - the same shape as #6. Recorded rather than shipped.")

# ---------------------------------------------------------------- C
print("\n########## C. the census, three ways per module ##########")
ATTRIBUTE_EXERCISED = {"ledger.py"}
never: list[str] = []
patch_only: list[str] = []
print(f"    {'module':<16}{'defs':>5}{'called':>8}{'raised':>8}{'named':>7}  verdict")
for module in modules:
    names = [n.name for n in tops[module]]
    classes = {n.name for n in tops[module] if isinstance(n, ast.ClassDef)}
    called = [n for n in names
              if re.search(rf"\b{re.escape(n)}\s*\(", test_text)]
    raised = [n for n in classes
              if re.search(rf"assertRaises\w*\(\s*{re.escape(n)}\b", test_text)]
    named = [n for n in names if re.search(rf"\b{re.escape(n)}\b", test_text)]
    if module in ATTRIBUTE_EXERCISED:
        verdict = "exercised via attribute"
    elif called or raised:
        verdict = "exercised by name"
    elif named:
        verdict = "PATCH TARGET ONLY"
        patch_only.append(module)
    else:
        verdict = "NEVER NAMED"
        never.append(module)
    print(f"    {module:<16}{len(names):>5}{len(called):>8}{len(raised):>8}"
          f"{len(named):>7}  {verdict}")
check("modules never named by the suite at all", "never: 5",
      f"never: {len(never)}   {never}")
check("  modules whose only mention is a patch target", "patch-only: 2",
      f"patch-only: {len(patch_only)}   {patch_only}")
check("    together, the never-exercised set", "unexercised: 7",
      f"unexercised: {len(never) + len(patch_only)}")
check("      out of fifteen", "fraction: 7/15",
      f"fraction: {len(never) + len(patch_only)}/{len(modules)}")

# ---------------------------------------------------------------- D
print("\n########## D. and five issues live in that set ##########")
ISSUES = {"provenance.py": ["#4", "#5", "#18"], "archive.py": ["#10", "#18"],
          "model.py": ["#15"]}
unexercised = sorted(never + patch_only)
living = sorted({i for m, v in ISSUES.items() if m in unexercised for i in v})
for module in unexercised:
    print(f"    {module:<16} {ISSUES.get(module, ['(no issue filed)'])}")
check("issues whose component is never exercised by name",
      "issues: ['#10', '#15', '#18', '#4', '#5']", f"issues: {living}")
check("  item 42 predicted four; the fifth is model.py", "model.py in set: True",
      f"model.py in set: {'model.py' in unexercised}")
model_names = [n.name for n in tops["model.py"]]
validate_task_hits = len(re.findall(r"\bvalidate_task\b", test_text))
check("    and #15's own function is not in the suite",
      "validate_task named: 0",
      f"validate_task named: {validate_task_hits}")
print(f"    model.py's five names, none of them in tests: {model_names}")
print("  So it is a structural fact about the suite, not a coincidence about")
print("  two components. `errors.py` is the counter-example that shows the")
print("  census is not just counting silence: it has zero CALLS but six of its")
print("  eight classes appear in assertRaises, so it lands in `exercised`.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT claim ##########")
print("  * NOT that the code is unexecuted. Item 42 measured the opposite:")
print("    submit / verify / proxy_submit are driven by 40 test call sites and")
print("    reach archive.py and provenance.py UNCONDITIONALLY on every run.")
print("    The claim is that no test NAMES them, so none can fail ABOUT their")
print("    own contract.")
print("  * NOT that a name census is sufficient. ledger.py proves it is not,")
print("    and that near miss is in section B rather than hidden.")
print("  * NOT a finding. This is a MAP, no issue is filed, and #4, #5, #10,")
print("    #15 and #18 are neither re-confirmed nor retracted here.")
print("  * It does not run the Python suite - pytest is not installed in this")
print("    container. Every result is a static read at main 5694ab45.")
print("  * MEASURED: every count, every verdict, the attribute table, the")
print("    per-name listings. REASONED: that a module no test names cannot")
print("    have a failing test about its contract - which follows from the")
print("    absence, not from running anything.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static AST and text reads of the package and tests at main 5694ab45.")
print("Nothing executed against a workspace, no issue filed. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
