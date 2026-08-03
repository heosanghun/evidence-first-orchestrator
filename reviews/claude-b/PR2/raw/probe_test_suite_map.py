#!/usr/bin/env python3
"""EFO at main (5694ab45): what does the shipped test suite actually assert,
and which of the 16 issues this review filed would it have caught?

Queue item 31. The documents are exhausted; `tests/` is the last untouched
surface. This review has invoked the suite (via CI) many times and never read
it.

The answer is not a score. A test suite that misses a defect is not thereby
bad - the useful output is the MAP: which failure classes the suite is
structurally blind to, and why. Two results are precise enough to be worth the
pass on their own:

  * the single test that exercises `repair_projections` asserts exactly two
    things, and #19 lives underneath both of them;
  * the suite's ONLY mention of `last_event_hash` is an EXCLUSION from a
    comparison - the same exclusion `workspace.py:1511` makes, which is what
    #19 is about.

A caveat stated up front, because it bounds every number below: name presence
is an UPPER bound on coverage and its ABSENCE is the load-bearing half. A token
that never appears in `tests/` cannot be asserted there. A token that appears
may still be asserted about something else entirely, so section C's "present"
column is a lead, not a verdict, and section D adjudicates the ones that
matter by reading them.

    python3 probe_test_suite_map.py
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
WEB_TESTS = SOURCE / "web_tests"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# `tests/*.py` and NOT `tests/**`: a first pass used `grep -rl` over the
# directory and matched compiled bytecode in `tests/__pycache__`, which
# reported `archive_evidence_bundle` and `verify_git_provenance` as present in
# two files each. Both are absent from the sources. That is the sixth
# hand-rolled filter in this review to be the bug, and it would have inverted
# the headline finding of this very probe.
TEST_SOURCES = sorted(TESTS.glob("*.py"))
WEB_SOURCES = sorted(WEB_TESTS.glob("*.mjs"))
TEST_TEXT = {p.name: p.read_text(encoding="utf-8") for p in TEST_SOURCES}
WEB_TEXT = {p.name: p.read_text(encoding="utf-8") for p in WEB_SOURCES}


def mentions(token: str) -> list[str]:
    return sorted(name for name, text in {**TEST_TEXT, **WEB_TEXT}.items()
                  if token in text)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL and suite inventory ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
# The list is derived from the directory, not written by hand.
check("  no compiled bytecode is being read as a test source",
      "pycache in sources: False",
      "pycache in sources: "
      + str(any("__pycache__" in str(p) for p in TEST_SOURCES)))

functions = 0
assertions = 0
per_module: list[tuple[str, int, int]] = []
for path in TEST_SOURCES:
    tree = ast.parse(TEST_TEXT[path.name])
    names = [node for node in ast.walk(tree)
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name.startswith("test")]
    calls = sum(1 for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr.startswith("assert"))
    bare = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))
    functions += len(names)
    assertions += calls + bare
    per_module.append((path.name, len(names), calls + bare))
for name, count, asserted in per_module:
    print(f"    {name:<28} {count:3} tests, {asserted:3} assertions")
check("Python test functions in tests/", "functions: 93",
      f"functions: {functions}")
check("  assertions across them", "assertions: 318",
      f"assertions: {assertions}")
print(f"  plus {len(WEB_SOURCES)} Node test files: "
      f"{[p.name for p in WEB_SOURCES]}")
print("  NOTE: the standing check-in text has carried `33 test methods` for")
print("  several rounds. That figure is from the branch's OLD base dad3f4c4,")
print("  which was missing four whole test modules - the branch-base defect")
print("  already recorded in SYNTHESIS.md, resurfacing in a number. The real")
print("  count at main is 93.")

# ---------------------------------------------------------------- B
print("\n########## B. what the suite STUBS OUT ##########")
patched: list[tuple[str, int, str]] = []
for path in TEST_SOURCES:
    tree = ast.parse(TEST_TEXT[path.name])
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = (node.func.id if isinstance(node.func, ast.Name)
                else node.func.attr if isinstance(node.func, ast.Attribute)
                else "")
        if name not in {"patch", "patch.object"} or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            patched.append((path.name, node.lineno, first.value))
patched = sorted(set(patched))
for name, line, target in patched:
    print(f"    {name}:{line}  {target}")
check("mock targets across the whole suite", "patched: 21",
      f"patched: {len(patched)}")
package = [entry for entry in patched
           if entry[2].startswith("evidence_orchestrator.")]
collector = [entry for entry in patched
             if entry[2].startswith("monitor.collector.")]
check("  of which are in the EFO package proper", "package: 3",
      f"package: {len(package)}")
check("  the rest are the collector's own helpers", "collector: 18",
      f"collector: {len(collector)}")
check("  and the package ones sit in a single file",
      "files: ['test_proxy_status.py']",
      f"files: {sorted({entry[0] for entry in package})}")
print("  A first version of this section matched any line naming the")
print("  package and counted an IMPORT at test_proxy_status.py:8 as a")
print("  mock. It is now read from the AST: a call to `patch` with a")
print("  string first argument. Seventh filter bug of the pass, and it")
print("  changed the answer - the real count is 21, not 3.")
print("  The 18 collector patches are a different thing: the collector")
print("  shells out to nvidia-smi and reads /proc, so stubbing those is")
print("  what makes it testable at all. Worth noting only because it means")
print("  the collector suite measures the collector's LOGIC and never its")
print("  interaction with a real machine.")
print("  The 3 package patches sit in ONE test - the suite's only end-to-end")
print("  proxy submission. It mocks evidence validation, Git provenance")
print("  verification, and evidence archiving: the three components carrying")
print("  issues #4, #5, #8, #10 and #18. The test measures that proxy_submit")
print("  ORCHESTRATES them, which it does. It cannot measure what they do.")

# ---------------------------------------------------------------- C
print("\n########## C. every issue this review filed, against the suite ##########")
# issue -> (module, the function or symbol the defect lives in, token to search)
# The function name is CHECKED to exist in its module below; a typo here would
# otherwise silently turn a covered issue into an uncovered one.
ISSUES = [
    ("#3",  "independence.py", "resolve_identity_registry", "alias_of"),
    ("#4",  "provenance.py",   "validate_git_provenance",   "no-replace-objects"),
    ("#5",  "provenance.py",   "validate_git_provenance",   "refs/remotes"),
    ("#6",  None,              None,                        "stale"),
    ("#7",  "model.py",        "lease_expiry",              "lease_ceiling"),
    ("#8",  "evidence.py",     "validate_submission",       "[FILL]"),
    ("#9",  "ledger.py",       "Ledger.verify",             "truncat"),
    ("#10", "archive.py",      "archive_evidence_bundle",   "archive_evidence_bundle"),
    ("#11", "adapter.py",      "run_once",                  "events.jsonl"),
    ("#12", "doctor.py",       "_scan_secrets",             "AWS_SECRET"),
    ("#13", None,              None,                        "instructions"),
    ("#14", None,              None,                        "FORBIDDEN_KEYS"),
    ("#15", "model.py",        "validate_task",             "allow_skips"),
    ("#17", "doctor.py",       "audit_legacy_workspace",    "write_test"),
    ("#18", "archive.py",      "archive_evidence_bundle",   "max_evidence_bytes"),
    ("#19", "workspace.py",    "Workspace.repair_projections", "last_event_hash"),
]


def defines(module: str, symbol: str) -> bool:
    tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
    if "." in symbol:
        class_name, method = symbol.split(".", 1)
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return any(isinstance(inner, (ast.FunctionDef,
                                              ast.AsyncFunctionDef))
                           and inner.name == method for inner in node.body)
        return False
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == symbol for node in tree.body)


missing_symbol = [f"{issue} {module}::{symbol}"
                  for issue, module, symbol, _ in ISSUES
                  if module and not defines(module, symbol)]
check("every function this map names exists in its module",
      "not found: []", f"not found: {missing_symbol}")
print("  (that check is the point: a typo in the map would have turned a")
print("   covered issue into an uncovered one, silently.)")

absent: list[str] = []
present: list[str] = []
for issue, module, symbol, token in ISSUES:
    where = mentions(token)
    site = f"{module}::{symbol}" if module else "JS / dashboard"
    if where:
        present.append(issue)
        print(f"    {issue:<4} {site:<44} token {token!r} -> {where}")
    else:
        absent.append(issue)
        print(f"    {issue:<4} {site:<44} token {token!r} -> ABSENT "
              f"from every test source")
check("issues whose defect token appears NOWHERE in either suite",
      f"absent: {len(absent)}", f"absent: {len(absent)} {absent}")
print("  ABSENCE is decisive: a token no test source contains cannot be")
print("  asserted by one. PRESENCE is only a lead - section D reads them.")

# ---------------------------------------------------------------- D
print("\n########## D. the two blind spots worth naming, read rather than grepped ##########")
workspace_tests = TEST_TEXT["test_workspace.py"].splitlines()
repair_lines = [index + 1 for index, line in enumerate(workspace_tests)
                if "repair_projections" in line]
check("  repair_projections is exercised by exactly one test",
      "call sites: 1", f"call sites: {len(repair_lines)}")
start = repair_lines[0]
body = workspace_tests[start - 6:start + 3]
before = [line.strip() for index, line in enumerate(body, start=start - 5)
          if "assert" in line and index < start]
after = [line.strip() for index, line in enumerate(body, start=start - 5)
         if "assert" in line and index > start]
print(f"    test_workspace.py:{start - 5} "
      f"test_projection_loss_is_detected_and_repairable")
print("      before the repair call:")
for line in before:
    print(f"        {line}")
print("      after it:")
for line in after:
    print(f"        {line}")
# A first draft counted all three as assertions ABOUT the repair. The
# assertRaises is about audit_projections DETECTING the loss, which is a
# different property and one the suite gets right - so the number that
# matters is the two that follow the repair.
check("  assertions about what the repair PRODUCED", "after: 2",
      f"after: {len(after)}")
check("  neither of which mentions the key #19 drops",
      "mentions last_event_hash: False",
      "mentions last_event_hash: "
      + str(any("last_event_hash" in line for line in after)))
print("    So #19 sits directly underneath the one test of the function that")
print("    causes it. The test asserts the projection is REBUILT and that its")
print("    `state` is right. #19 is a different key going missing from the")
print("    same rebuild, so this test passes with the defect present.")

status_tests = TEST_TEXT["test_proxy_status.py"].splitlines()
hits = [(index + 1, line.strip()) for index, line in enumerate(status_tests)
        if "last_event_hash" in line]
check("  the suite's only mention of last_event_hash", "mentions: 1",
      f"mentions: {len(hits)}")
for line_number, text in hits:
    print(f"    test_proxy_status.py:{line_number}  {text}")
check("  and it is an EXCLUSION, not an assertion", 'if key != "last_event_hash"',
      hits[0][1])
workspace_source = (PACKAGE / "workspace.py").read_text(
    encoding="utf-8").splitlines()
print(f"    workspace.py:1511  {workspace_source[1510].strip()}")
print("    The test excludes the key from its comparison for the same reason")
print("    `audit_projections` excludes it: a projection carries it and a")
print("    ledger snapshot does not. The exclusion is correct in both places.")
print("    What neither does is assert the key is STILL THERE after a rebuild,")
print("    and that gap is #19. The suite encodes the same blindness as the")
print("    code it tests - which is the general shape worth taking away.")

# ---------------------------------------------------------------- E
print("\n########## E. what this pass does NOT establish ##########")
print("  * It does not run the suite. `pytest` is absent from this container")
print("    and the shipped runner is `python -m unittest`; every pass/fail")
print("    count this review has ever quoted is CI's, bound to a job id.")
print("  * It does not claim the suite is bad. 93 tests and 318 assertions")
print("    cover the paths they were written for; nothing here found a test")
print("    that asserts something FALSE.")
print("  * Section C classifies by TOKEN. A defect could in principle be")
print("    caught by a test that never names it - so 'absent' means")
print("    'cannot be asserted by name', not 'provably uncaught'. The two in")
print("    section D are read directly and are not subject to that caveat.")
print("  * The three Node test files are searched for tokens but not read.")
print("    #13 and #14 live in `functions/api/*.js`, and adjudicating")
print("    `chat.test.mjs` and `snapshot.test.mjs` line by line is a separate")
print("    pass.")
print("  * MEASURED: the inventory, the patch targets, the token map, and")
print("    both section-D readings. REASONED: that a token's absence implies")
print("    the class is unasserted.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis of the test sources only; nothing was executed.")
print("No issue is filed from this pass - a suite that does not test a defect")
print("is not itself a defect. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
