#!/usr/bin/env python3
"""#4, #5, #8, #18: the components ARE driven for real - the PROPERTIES are not.

Queue item 42 asked whether `test_proxy_status.py`'s three package mocks -
`validate_submission`, `validate_git_provenance`, `archive_evidence_bundle` -
stub out the only end-to-end path through the components carrying #4, #5, #8
and #18.

**The premise is wrong, and that is the first result.** Those three mocks live
in ONE file of twelve. `test_proxy_submission.py` drives `proxy_submit` with
ZERO patches of any kind, and `test_independence.py` drives `submit` and
`verify` the same way. All three functions are called unconditionally on those
paths - no guard, no feature flag - so every one of them executes for real many
times per run.

The useful question is the one item 36 and the node-suite note reached by a
different road: the component is reached, but is the PROPERTY the issue objects
to ever fed to it? Measured per issue:

  #4  `git replace` forging byte-exact provenance ....... 0 occurrences
  #5  a never-pushed commit passing .................... 0 occurrences
  #18 `max_evidence_bytes` as threshold vs ceiling ...... 0 occurrences
  #8  `[FILL]` compared with itself .................... guard exercised,
                                                         never with [FILL]

Three of the four have no vocabulary in the suite at all - the #6 shape. The
fourth has a guard with tests on both sides, fed only the input it already
handles - the #13/#14 shape.

    python3 probe_proxy_mocks.py

SCOPE, stated before starting: 12 test files, 3 components, 4 issues, 6 call
sites. Small enough to adjudicate every hit by hand, and every hit below IS
adjudicated rather than counted.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
TESTS = SOURCE / "tests"
PKG = SOURCE / "src/evidence_orchestrator"
MOCKED = ["validate_submission", "validate_git_provenance",
          "archive_evidence_bundle"]


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def token(name: str, text: str) -> list[int]:
    """Line numbers where `name` appears as a WHOLE WORD.

    Never a substring. `replace` inside `cannot_be_replaced` and `worker`
    inside `worker_identity` are the two traps this review has already fallen
    into, the second one after writing the rule down.
    """
    return [i for i, line in enumerate(text.splitlines(), 1)
            if re.search(rf"\b{re.escape(name)}\b", line)]


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
files = sorted(TESTS.glob("*.py"))
check("  and the suite is the size every write-up reports",
      "test files: 12", f"test files: {len(files)}")
print("  SCOPE: 12 files, 3 components, 4 issues. Stated before starting, so")
print("  that a population too large to adjudicate would have stopped here.")

# ---------------------------------------------------------------- B
print("\n########## B. the premise: are the three mocks the ONLY path? ##########")
patching = {}
for path in files:
    text = path.read_text(encoding="utf-8")
    hits = [n for n in MOCKED if any(
        "patch(" in text.splitlines()[i - 1] or "evidence_orchestrator.workspace" in text.splitlines()[i - 1]
        for i in token(n, text))]
    if hits:
        patching[path.name] = hits
for name, hits in sorted(patching.items()):
    print(f"    {name:<28} patches {hits}")
check("files that patch any of the three", "patching: 1",
      f"patching: {len(patching)}")

# `test_proxy_submission.py` is the file that drives the SAME entry point.
proxy_sub = (TESTS / "test_proxy_submission.py").read_text(encoding="utf-8")
patches_there = token("patch", proxy_sub) + token("monkeypatch", proxy_sub)
check("  and the OTHER file driving proxy_submit patches nothing",
      "patches in test_proxy_submission.py: 0",
      f"patches in test_proxy_submission.py: {len(patches_there)}")

# The call sites, enumerated from the AST rather than grepped.
tree = ast.parse((PKG / "workspace.py").read_text(encoding="utf-8"))
owners: dict[str, set[tuple[str, int]]] = {}
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id in MOCKED):
                owners.setdefault(node.name, set()).add((sub.func.id, sub.lineno))
for fn in sorted(owners):
    print(f"    workspace.{fn:<14} calls {sorted(owners[fn])}")
check("  the entry points that reach them, from the AST",
      "entry points: ['proxy_submit', 'submit', 'verify']",
      f"entry points: {sorted(owners)}")

driven = {fn: sum(len([i for i in token(fn, p.read_text(encoding='utf-8'))
                       if re.search(rf"\b{fn}\s*\(", p.read_text(encoding='utf-8').splitlines()[i - 1])])
                  for p in files) for fn in owners}
print(f"    test call sites driving them: {driven}")
check("  every entry point is driven by more than the patching file",
      "min call sites: True",
      f"min call sites: {min(driven.values()) > 1}   ({driven})")
print("  So the three functions run for real on every unpatched submit,")
print("  verify and proxy_submit. The item's premise does not hold, and")
print("  saying so is the finding rather than something to work around.")

# ---------------------------------------------------------------- C
print("\n########## C. #4 - `git replace`: no vocabulary at all ##########")
all_text = {p.name: p.read_text(encoding="utf-8") for p in files}
phrase = {
    name: [i for i, line in enumerate(text.splitlines(), 1)
           if "git replace" in line or "replace-ref" in line
           or "refs/replace" in line]
    for name, text in all_text.items()}
found = {n: v for n, v in phrase.items() if v}
check("tests mentioning a git replace ref", "sites: {}", f"sites: {found}")
print("  ADJUDICATED, not counted. Every whole-word `replace` hit, listed so")
print("  the reader can check the adjudication rather than trust the count:")
bare = [(n, i, all_text[n].splitlines()[i - 1].strip()[:66])
        for n in all_text for i in token("replace", all_text[n])]
bare += [(n, i, all_text[n].splitlines()[i - 1].strip()[:66])
         for n in all_text for i in token("replaced", all_text[n])]
for n, i, line in sorted(bare):
    print(f"    {n}:{i}  {line}")
check("  whole-word hits, each adjudicated as NOT a git replace",
      "adjudicated: 3", f"adjudicated: {len(bare)}")
substring = sum(1 for n in all_text
                for line in all_text[n].splitlines() if "replace" in line)
check("    and what a SUBSTRING search would have added",
      "substring: 5", f"substring: {substring}")
print("  All three whole-word hits are `str.replace` / `bytes.replace`. The")
print("  two a substring search adds are identifier-internal - the test names")
print("  `test_ready_does_not_replace_proxy_submission_requirements` and")
print("  `test_active_proxy_grant_cannot_be_replaced`. Five leads, zero real.")
print("  That is the trap this review has fallen into twice, and the reason")
print("  every count here is tokenised on a word boundary. Absence of the")
print("  PHRASE is decisive: no test constructs a replace ref, so #4's")
print("  mechanism is not exercised, refuted or regression-guarded anywhere.")
print("  I expected five whole-word hits going in. There are three. The")
print("  expectation was corrected to the measurement.")

# ---------------------------------------------------------------- D
print("\n########## D. #5 and #18 - the same shape ##########")
for issue, tokens in (("#5  never-pushed commit", ["push", "pushed", "git push"]),
                      ("#18 max_evidence_bytes", ["max_evidence_bytes",
                                                  "max_blob_bytes"])):
    sites = {n: [i for t in tokens for i in token(t, text)]
             for n, text in all_text.items()}
    sites = {n: v for n, v in sites.items() if v}
    check(f"{issue}: occurrences in the whole suite", "sites: {}",
          f"sites: {sites}")
print("  #5: nothing in the suite pushes, so no test can distinguish a")
print("  pushed commit from a never-pushed one - the property has no")
print("  vocabulary, which is the #6 answer rather than `the suite forgot`.")
print("  #18: the config key is never SET by any test, so both call sites")
print("  always take the 50 MiB default and the threshold-vs-ceiling")
print("  divergence the issue is about cannot appear.")

# ---------------------------------------------------------------- E
print("\n########## E. #8 - the guard IS tested, with input it already handles ##########")
evidence = (PKG / "evidence.py").read_text(encoding="utf-8").splitlines()
comparison = next(i for i, line in enumerate(evidence, 1)
                  if 'check["expected"] != check["observed"]' in line)
check("the known-answer comparison is a bare inequality",
      'if check["expected"] != check["observed"]:',
      evidence[comparison - 1].strip())
print(f"    evidence.py:{comparison}")
helpers = (TESTS / "helpers.py").read_text(encoding="utf-8")
block = helpers[helpers.index('"known_answer_checks"'):][:300]
expected_vals = re.findall(r'"expected": ([^,\n]+)', block)
observed_vals = re.findall(r'"observed": ([^,\n]+)', block)
check("  the only fixture feeds it integers", "expected: ['4']",
      f"expected: {expected_vals}")
check("    on both sides", "observed: ['4 if known_answer_passed else 5']",
      f"observed: {observed_vals}")
print("  So both branches ARE covered: 4 == 4 passes, 4 != 5 raises. What is")
print("  never fed is the input #8 is about - the SAME string on both sides.")

fill_guard = [i for i, line in enumerate(evidence, 1)
              if "exact value [FILL]" in line]
check("  the only [FILL] rejection in evidence.py", "sites: 1",
      f"sites: {len(fill_guard)}")
print(f"    evidence.py:{fill_guard[0]} - and it is in the CLAIMS loop, not the")
print("    known-answer loop. The known-answer loop has no [FILL] check at all.")
test_ev = (TESTS / "test_evidence.py").read_text(encoding="utf-8")
asserting = [i for i, line in enumerate(test_ev.splitlines(), 1)
             if "exact value" in line]
check("  the test that asserts it, and what it asserts about",
      "test_evidence.py sites: 1", f"test_evidence.py sites: {len(asserting)}")
print(f"    test_evidence.py:{asserting[0]} sets claims[-1]['value'] = 0.7 - a")
print("    CLAIM, not a known-answer check. So the one test naming [FILL]")
print("    guards a different loop than the one #8 objects to.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not run the Python suite. pytest is not installed in this")
print("    container; every result above is a static read of the test files")
print("    and the package at main 5694ab45.")
print("  * It does not claim the components are UNTESTED. They are driven")
print("    heavily. The claim is narrower and is the whole point: the four")
print("    properties named have either no vocabulary or no matching input.")
print("  * It does not re-confirm #4, #5, #8 or #18. Those were established")
print("    by executed attacks against pinned refs and are cited in the")
print("    issues; this is a MAP of what the suite would catch, not a")
print("    finding.")
print("  * It does not file an issue. A map is not a defect report.")
print("  * MEASURED: every occurrence count, every adjudication, the AST call")
print("    graph, the comparison line, the fixture values. REASONED: that a")
print("    property with no vocabulary cannot regress detectably - which")
print("    follows from the absence, not from running anything.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static reads of tests/ and the package at main 5694ab45. Nothing")
print("executed against a workspace, no issue filed. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
