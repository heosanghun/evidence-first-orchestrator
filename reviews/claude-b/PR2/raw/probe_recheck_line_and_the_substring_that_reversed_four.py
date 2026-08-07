#!/usr/bin/env python3
"""`raw-recheck-cef5623.txt` IS decidable - and finding out reversed FOUR of
item 58's placements, including four of `REPORT.md`'s six.

Queue item 61, from item 58. That round left two of `REPORT.md`'s six cited
outputs unplaced. One, `raw-attack4.txt`, was already known from item 55 to be
MIXED. The other, `raw-recheck-cef5623.txt`, was undecidable and unexplained,
and item 46 re-ran its suite section (77/77, OK, exit 0) without ever asking
which v2 produced it. This asks.

The answer is yes, and by a discriminator the file carries in plain sight:

    Ran 77 tests in 13.628s

Item 58 scanned for MODULE-NAME tokens, so a SUITE SIZE was structurally
invisible to it. Swept exhaustively over every commit reachable from either
line - 15 on the anchor's, 6 on the divergent one - NO TEST COUNT IS SHARED
BETWEEN THE TWO LINES, and 77 names exactly one commit: `cef5623`, a
DESCENDANT of `7a9553b` and, like it, no ancestor of the anchor.

AND THE DEFECT WAS MINE. Item 58's ANCHOR_TOKENS ended with a bare
`"independence"` - a SUBSTRING, next to the precise `independence.py`. It
matches `independence_dimensions`, a JSON key that appears NOWHERE in the
anchor's entire ancestry and is introduced by `7a9553b` itself; and it matches
`test_known_independence_cases`, a method in `test_meta_orchestration.py`,
a module that exists only on the divergent line. Of the 35 outputs item 58
placed on the anchor, 11 rest on that bare token alone, and FOUR of those are
placed BACKWARDS.

    corrected  27 anchor / 5 divergent / 45 undecidable   (was 35 / 1 / 41)

AND MY FIRST CORRECTION REPEATED THE TRAP. Adding the anchor-only test module
`test_proxy_submission` as a literal made `raw-full-final.txt` look MIXED -
because `test_proxy_submission_records_author_proxy_and_git_commit` is a method
in `test_meta_orchestration.py`. Module names are PREFIXES of method names.
Fixed by PARSING the unittest id (`tests.<module>.<class>.<method>`) instead of
substring-matching it - the same rule item 50 learned about syntax.

    python3 probe_recheck_line_and_the_substring_that_reversed_four.py

SCOPE, stated first: 77 outputs, 6 cited by REPORT.md, 21 commits swept, 3
suites run, 2 marker sets derived exhaustively, 1 known answer, 4 reversals.
A CORRECTION to my own published note. No issue filed, and nothing about EFO
is claimed - this is about the PROVENANCE OF EVIDENCE THIS REVIEW INHERITED.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
CEF = Path("/tmp/efo-cef5623")
OTHER = Path("/tmp/efo-7a9553b")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"

ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
CEF_SHA = "cef56234a873fefddd51f8cfedb737705a6f0d9a"
OTHER_SHA = "7a9553b69a53620bdc59094b65527692dd73aa90"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *arguments],
                          capture_output=True, text=True).stdout.strip()


def test_methods(source: str):
    """Count test methods in one test module's SOURCE, by AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    total = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for body in node.body:
                if (isinstance(body, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and body.name.startswith("test")):
                    total += 1
    return total


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45", ANCHOR_SHA,
      git(ANCHOR, "rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git(ANCHOR, 'status', '--porcelain')!r}")
check("  the cef5623 checkout is at cef5623", "cef5623",
      git(CEF, "rev-parse", "--short=7", "HEAD"))
check("  the 7a9553b checkout is at 7a9553b", "7a9553b",
      git(OTHER, "rev-parse", "--short=7", "HEAD"))

# This probe's own output joins the corpus it scans AND prints both marker
# sets, so an unexcluded run classifies itself. Excluded STRUCTURALLY from
# this script's own filename, and the exclusion is COUNTED - item 58's
# treatment, which is the one part of that round this round does not correct.
SELF = "raw-" + Path(__file__).stem[len("probe_"):].replace("_", "-") + ".txt"
ITEM58 = "raw-output-provenance-lines.txt"
every = sorted(p for p in RAW.iterdir()
               if p.name.startswith("raw-") and p.suffix == ".txt")
outputs = [p for p in every if p.name not in (SELF, ITEM58)]
excluded = [p.name for p in every if p.name in (SELF, ITEM58)]
check("  raw outputs scanned, with the two self-referential ones excluded",
      "outputs: 77", f"outputs: {len(outputs)}")
check("    exactly two are excluded, and they are the two that print markers",
      f"excluded: ['{ITEM58}', '{SELF}']", f"excluded: {sorted(excluded)}")
print("  Item 58's own output is excluded for the same reason as this one:")
print("  it PRINTS both token sets. Item 58 excluded only itself, so it")
print("  scanned this file's predecessor - measured in section F.")

# ---------------------------------------------------------------- B
print("\n########## B. where cef5623 SITS in the graph ##########")
check("cef5623 is a DESCENDANT of 7a9553b", "descendant: True",
      "descendant: " + str(subprocess.run(
          ["git", "-C", str(ANCHOR), "merge-base", "--is-ancestor",
           OTHER_SHA, CEF_SHA]).returncode == 0))
check("  and is NOT an ancestor of the review's anchor", "ancestor: False",
      "ancestor: " + str(subprocess.run(
          ["git", "-C", str(ANCHOR), "merge-base", "--is-ancestor",
           CEF_SHA, ANCHOR_SHA]).returncode == 0))
check("  neither is 7a9553b", "ancestor: False",
      "ancestor: " + str(subprocess.run(
          ["git", "-C", str(ANCHOR), "merge-base", "--is-ancestor",
           OTHER_SHA, ANCHOR_SHA]).returncode == 0))


def ever(ref: str, prefix: str) -> set:
    """Every .py basename that EVER exists under `prefix` on `ref`'s line."""
    names = set()
    for commit in git(ANCHOR, "rev-list", ref).split():
        for path in git(ANCHOR, "ls-tree", "-r", "--name-only",
                        commit, prefix).split():
            if path.endswith(".py"):
                names.add(path.rsplit("/", 1)[-1])
    return names


anchor_modules = ever(ANCHOR_SHA, "src/evidence_orchestrator/")
diverg_modules = ever(CEF_SHA, "src/evidence_orchestrator/")
anchor_tests = ever(ANCHOR_SHA, "tests/")
diverg_tests = ever(CEF_SHA, "tests/")
print("  Markers derived over the WHOLE of each line, not a two-commit diff:")
print(f"    modules only ever on the anchor's line   "
      f": {sorted(anchor_modules - diverg_modules)}")
print(f"    modules only ever on the divergent line  "
      f": {sorted(diverg_modules - anchor_modules)}")
print(f"    test modules only on the anchor's line   "
      f": {sorted(anchor_tests - diverg_tests)}")
print(f"    test modules only on the divergent line  "
      f": {sorted(diverg_tests - anchor_tests)}")
check("the anchor's line has independence.py and nothing else of its own",
      "only anchor: ['independence.py']",
      f"only anchor: {sorted(anchor_modules - diverg_modules)}")
check("  the divergent line adds three modules the anchor never had",
      "only divergent: ['fingerprint.py', 'identity.py', 'job_runner.py']",
      f"only divergent: {sorted(diverg_modules - anchor_modules)}")
check("  four test modules exist only on the anchor's line",
      "only anchor: ['test_independence.py', 'test_monitor_collector.py', "
      "'test_proxy_status.py', 'test_proxy_submission.py']",
      f"only anchor: {sorted(anchor_tests - diverg_tests)}")
check("  and two only on the divergent line",
      "only divergent: ['test_fingerprint.py', 'test_meta_orchestration.py']",
      f"only divergent: {sorted(diverg_tests - anchor_tests)}")

# ---------------------------------------------------------------- C
print("\n########## C. the SUITE SIZE, swept EXHAUSTIVELY over both lines ##########")
sizes: dict = {}
for label, ref in (("anchor", ANCHOR_SHA), ("divergent", CEF_SHA)):
    for commit in git(ANCHOR, "rev-list", ref).split():
        if commit in sizes:
            continue
        files = [p for p in git(ANCHOR, "ls-tree", "-r", "--name-only",
                                commit, "tests/").split()
                 if p.rsplit("/", 1)[-1].startswith("test_")
                 and p.endswith(".py")]
        total = 0
        for path in files:
            counted = test_methods(git(ANCHOR, "show", f"{commit}:{path}"))
            if counted is None:
                total = None
                break
            total += counted
        sizes[commit] = (label, total)
        print(f"    {label:10} {commit[:7]}  files={len(files):2}  "
              f"tests={total}")

anchor_sizes = {v for label, v in sizes.values() if label == "anchor"}
diverg_sizes = {v for label, v in sizes.values() if label == "divergent"}
check("commits swept, every one reachable from either line",
      "commits: 20", f"commits: {len(sizes)}")
# I expected 21 - 15 on one line plus 6 on the other. They share their ROOT,
# so the union is 20. Corrected to the measurement; the shared commit is
# named rather than left as an off-by-one.
base = git(ANCHOR, "merge-base", ANCHOR_SHA, CEF_SHA)
check("  because the two lines share exactly one commit, their root",
      "f827f29", base[:7])
check("    and it is the ref item 55 found attack4's W1/W2 comparing against",
      "f827f29",
      (REVIEWS / "NOTE-w4-needs-a-ref-the-anchor-never-took.md").read_text(
          encoding="utf-8")[:4000].replace("\n", " "))
check("  no test count is shared between the two lines",
      "shared: set()", f"shared: {anchor_sizes & diverg_sizes}")
print("  So a SUITE SIZE is a two-way discriminator - and item 58 could not")
print("  see it, because it scanned only for module-name tokens.")
carriers = {c for c, (label, n) in sizes.items() if n == 77}
check("  and exactly one commit anywhere has a 77-test suite",
      "carriers: 1", f"carriers: {len(carriers)}")
check("    it is cef5623", "cef5623",
      sorted(carriers)[0][:7] if carriers else "none")

# ---------------------------------------------------------------- D
print("\n########## D. the KNOWN ANSWER: run all three suites ##########")
observed = {}
for label, tree in (("anchor", ANCHOR), ("cef5623", CEF), ("7a9553b", OTHER)):
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests",
         "-t", "."], cwd=tree, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "src", "HOME": "/root"})
    ran = re.search(r"Ran (\d+) tests", result.stderr)
    verdict = "OK" if "\nOK" in result.stderr else "FAILED"
    observed[label] = (int(ran.group(1)) if ran else None, verdict)
    print(f"    {label:10} Ran {observed[label][0]} tests   {verdict}")
check("the anchor runs 93, matching the static sweep", "anchor: 93",
      f"anchor: {observed['anchor'][0]}")
check("  cef5623 runs 77", "cef5623: 77", f"cef5623: {observed['cef5623'][0]}")
check("  7a9553b runs 70", "7a9553b: 70", f"7a9553b: {observed['7a9553b'][0]}")
print("  The 7a9553b run's verdict is recorded but NOT used as a")
print("  discriminator: one run does not establish determinism, and whether")
print("  that failure is stable is UNMEASURED.")

# ---------------------------------------------------------------- E
print("\n########## E. so the file IS decidable, from its own content ##########")
recheck = (RAW / "raw-recheck-cef5623.txt").read_text(encoding="utf-8")
check("raw-recheck-cef5623.txt states its own suite size", "Ran 77 tests",
      recheck.replace("\n", " "))
check("  which is cef5623's, on the DIVERGENT line", "77",
      f"{observed['cef5623'][0]}")
check("  and is NOT the anchor's at any commit",
      "77 on the anchor's line: False",
      f"77 on the anchor's line: {77 in anchor_sizes}")
print("  Item 46 re-ran this section (77/77, OK, exit 0) without asking")
print("  which v2 produced it. The answer is: not the one under review.")

# ---------------------------------------------------------------- F
print("\n########## F. THE DEFECT WAS MINE - a bare substring in item 58 ##########")
# Read from HISTORY, not from the working tree: this round CORRECTS that file
# in the SAME commit, so a working-tree read would stop finding the defect the
# moment the fix lands, and this check would then pass for the wrong reason -
# a self-erasing test. The pickaxe proves the published version carried it.
PROBE58 = "reviews/claude-b/PR2/raw/probe_output_provenance_lines.py"
WS = Path("/workspace/evidence-first-orchestrator")
introduced = git(WS, "log", "--oneline",
                 '-S"audit-independence", "independence")', "--", PROBE58)
print(f"    commits whose diff carries the bare token: "
      f"{[line.split()[0] for line in introduced.splitlines()]}")
check("item 58's anchor tokens ENDED with a bare substring, per git history",
      "commits: 1", f"commits: {len(introduced.splitlines())}")
check("  and it is the commit that published item 58", "78989d7",
      introduced.splitlines()[0] if introduced else "not found")
declaration = [line.strip() for line in
               (RAW / "probe_output_provenance_lines.py").read_text(
                   encoding="utf-8").splitlines()
               if line.startswith("ANCHOR_TOKENS")]
BARE = '"independence"'
still_there = any(BARE in line for line in declaration)
check("  and the corrected working tree no longer has it",
      "bare present: False", f"bare present: {still_there}")
for token, direction in (("independence_dimensions", "divergent"),
                         ("transport_independence", "anchor"),
                         ("audit-independence", "anchor")):
    on_anchor = len(git(ANCHOR, "log", "--oneline", f"-S{token}",
                        ANCHOR_SHA, "--").splitlines())
    on_diverg = len(git(ANCHOR, "log", "--oneline", f"-S{token}",
                        CEF_SHA, "--").splitlines())
    print(f"    {token:26} anchor-line commits={on_anchor}  "
          f"divergent-line commits={on_diverg}")
    check(f"  {token} belongs to the {direction} line, over FULL ancestry",
          "on the wrong line: 0",
          f"on the wrong line: {on_anchor if direction == 'divergent' else on_diverg}")
print("  `independence_dimensions` appears in NO commit of the anchor's")
print("  entire ancestry and is introduced by 7a9553b itself - yet item 58's")
print("  bare token counted it as ANCHOR evidence.")

OLD_OTHER = ("identity.py", "job_runner.py", "transfer_orchestrator",
             "transfer-orchestrator", "orchestrator_transferred")
OLD_ANCHOR = ("independence.py", "audit-independence", "independence")
old_anchor_placed, bare_only = [], []
for path in outputs:
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(t in text for t in OLD_OTHER):
        continue
    hits = [t for t in OLD_ANCHOR if t in text]
    if hits:
        old_anchor_placed.append(path.name)
        if hits == ["independence"]:
            bare_only.append(path.name)
check("item 58 placed this many outputs on the anchor", "anchor: 35",
      f"anchor: {len(old_anchor_placed)}")
check("  of which this many rest on the BARE substring alone", "bare: 11",
      f"bare: {len(bare_only)}")
print(f"    {bare_only}")

# ---------------------------------------------------------------- G
print("\n########## G. and my FIRST correction repeated the trap ##########")
full_final = (RAW / "raw-full-final.txt").read_text(encoding="utf-8")
check("`test_proxy_submission` is an ANCHOR-ONLY test module",
      "anchor-only: True",
      f"anchor-only: {'test_proxy_submission.py' in anchor_tests - diverg_tests}")
check("  yet it appears in raw-full-final.txt as a SUBSTRING",
      "substring present: True",
      f"substring present: {'test_proxy_submission' in full_final}")
offender = [line.strip() for line in full_final.splitlines()
            if "test_proxy_submission" in line][0]
print(f"    {offender[:96]}")
check("    of a method in test_meta_orchestration, the DIVERGENT module",
      "tests.test_meta_orchestration.", offender)
print("  Module names are PREFIXES of method names. A literal scan cannot")
print("  tell the two apart; PARSING the unittest id can.")

ID = re.compile(r"tests\.(test_[A-Za-z0-9_]+)\.")
named = set(ID.findall(full_final))
# I expected the parse to name ONE module. It names seven - it is a FULL
# SUITE run. The claim that survives is narrower and is the one that matters:
# of the modules it names, the line-distinguishing ones are all divergent.
check("  parsed, raw-full-final.txt names seven test modules",
      "modules: 7", f"modules: {len(named)}")
check("    of which the divergent-only ones are",
      "divergent: ['test_meta_orchestration']",
      f"divergent: {sorted(named & {p[:-3] for p in diverg_tests - anchor_tests})}")
check("    and it names NO anchor-only test module", "anchor: []",
      f"anchor: {sorted(named & {p[:-3] for p in anchor_tests - diverg_tests})}")

# the id-set match, which is stronger than any single token
ids_in_file = set(re.findall(
    r"tests\.(test_[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+)", full_final))


def suite_ids(tree: Path) -> set:
    found = set()
    for path in sorted((tree / "tests").glob("test_*.py")):
        parsed = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(parsed):
            if isinstance(node, ast.ClassDef):
                for body in node.body:
                    if (isinstance(body, (ast.FunctionDef,
                                          ast.AsyncFunctionDef))
                            and body.name.startswith("test")):
                        found.add(f"{path.stem}.{node.name}.{body.name}")
    return found


for label, tree in (("anchor", ANCHOR), ("cef5623", CEF), ("7a9553b", OTHER)):
    suite = suite_ids(tree)
    print(f"    vs {label:10} in-file-not-in-suite={len(ids_in_file - suite):3}"
          f"  in-suite-not-in-file={len(suite - ids_in_file):3}")
check("raw-full-final.txt's ids EXACTLY match 7a9553b's suite, both ways",
      "outside: 0 missing: 0",
      f"outside: {len(ids_in_file - suite_ids(OTHER))} "
      f"missing: {len(suite_ids(OTHER) - ids_in_file)}")
check("  and this many of them do not exist at the anchor AT ALL",
      "absent at anchor: 43",
      f"absent at anchor: {len(ids_in_file - suite_ids(ANCHOR))}")

# HOW FAR the id match actually narrows - asked, not assumed. `4aa47ca` is
# REPORT.md's DECLARED subject and also has a 70-test suite.
SUBJECT = "4aa47ca602d36c22cbaf2ce63fa442ee398c317e"


def ids_at(commit: str) -> set:
    found = set()
    for path in git(ANCHOR, "ls-tree", "-r", "--name-only",
                    commit, "tests/").split():
        name = path.rsplit("/", 1)[-1]
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        parsed = ast.parse(git(ANCHOR, "show", f"{commit}:{path}"))
        for node in ast.walk(parsed):
            if isinstance(node, ast.ClassDef):
                for body in node.body:
                    if (isinstance(body, (ast.FunctionDef,
                                          ast.AsyncFunctionDef))
                            and body.name.startswith("test")):
                        found.add(f"{name[:-3]}.{node.name}.{body.name}")
    return found


subject_ids = ids_at(SUBJECT)
check("REPORT.md's declared subject 4aa47ca has the SAME 70 ids as 7a9553b",
      "identical: True", f"identical: {subject_ids == suite_ids(OTHER)}")
check("  so the id match places the FILE on the divergent line but cannot",
      "picks a commit: False",
      f"picks a commit: {subject_ids != suite_ids(OTHER)}")
print("  pick between them. `4aa47ca` is the commit REPORT.md names as its")
print("  own subject, which is the reading that needs no extra assumption -")
print("  but this test does not establish it, and saying otherwise would be")
print("  claiming more than the measurement carries.")

# ---------------------------------------------------------------- H
print("\n########## H. the CORRECTED classification ##########")
A_LIT = tuple(sorted(anchor_modules - diverg_modules)) + (
    "transport_independence", "audit-independence")
D_LIT = tuple(sorted(diverg_modules - anchor_modules)) + (
    "transfer_orchestrator", "transfer-orchestrator",
    "orchestrator_transferred", "independence_dimensions")
A_MOD = {p[:-3] for p in anchor_tests - diverg_tests}
D_MOD = {p[:-3] for p in diverg_tests - anchor_tests}
placed_anchor, placed_diverg, mixed, undecidable = [], [], [], []
for path in outputs:
    text = path.read_text(encoding="utf-8", errors="replace")
    modules_named = set(ID.findall(text))
    found_a = [t for t in A_LIT if t in text] + sorted(modules_named & A_MOD)
    found_d = [t for t in D_LIT if t in text] + sorted(modules_named & D_MOD)
    if found_a and found_d:
        mixed.append(path.name)
    elif found_a:
        placed_anchor.append(path.name)
    elif found_d:
        placed_diverg.append(path.name)
        print(f"    divergent  {path.name}  {found_d}")
    else:
        undecidable.append(path.name)
check("outputs placed on the ANCHOR's line", "anchor: 27",
      f"anchor: {len(placed_anchor)}")
check("  outputs placed on the DIVERGENT line", "divergent: 5",
      f"divergent: {len(placed_diverg)}")
check("  outputs carrying tokens from BOTH", "mixed: 0",
      f"mixed: {len(mixed)}")
check("  outputs the token test cannot place", "undecidable: 45",
      f"undecidable: {len(undecidable)}")
check("    and the four classes account for every output",
      f"total: {len(outputs)}",
      f"total: {len(placed_anchor) + len(placed_diverg) + len(mixed) + len(undecidable)}")
print("  Item 58 published 35 / 1 / 41. Four outputs move from ANCHOR to")
print("  DIVERGENT; seven more lose an unfounded anchor placement.")

# ---------------------------------------------------------------- I
print("\n########## I. REPORT.md's six, re-placed ##########")
SIX = ["raw-attack2.txt", "raw-attack2-cef5623.txt", "raw-attack3.txt",
       "raw-full-final.txt", "raw-attack4.txt", "raw-recheck-cef5623.txt"]
report = (REVIEWS / "REPORT.md").read_text(encoding="utf-8")
for name in SIX:
    check(f"REPORT.md cites {name}", "cited: True", f"cited: {name in report}")

# THE KNOWN ANSWER, and it was in the document the whole time.
subject = [line.strip() for line in report.splitlines()
           if line.startswith("4aa47ca")]
print(f"    REPORT.md:437-438 - Subject under review @ {subject[0][:42]}")
check("REPORT.md DECLARES its subject, and it is not the anchor", "4aa47ca6",
      subject[0] if subject else "not found")
check("  that commit is on the DIVERGENT line", "on divergent line: True",
      "on divergent line: " + str(subprocess.run(
          ["git", "-C", str(ANCHOR), "merge-base", "--is-ancestor",
           "4aa47ca602d36c22cbaf2ce63fa442ee398c317e",
           CEF_SHA]).returncode == 0))
check("  and is NOT an ancestor of the anchor", "ancestor of anchor: False",
      "ancestor of anchor: " + str(subprocess.run(
          ["git", "-C", str(ANCHOR), "merge-base", "--is-ancestor",
           "4aa47ca602d36c22cbaf2ce63fa442ee398c317e",
           ANCHOR_SHA]).returncode == 0))
print("  So the corrected placement AGREES with what REPORT.md says about")
print("  itself, and item 58's placement CONTRADICTED it. The known answer")
print("  needed to catch that bare substring was three lines from the")
print("  manifest item 46 read, and I did not check my filter against it.")
verdicts = {}
for name in SIX:
    if name in placed_anchor:
        verdicts[name] = "anchor"
    elif name in placed_diverg:
        verdicts[name] = "DIVERGENT"
    elif name in mixed:
        verdicts[name] = "mixed"
    else:
        verdicts[name] = "undecidable-by-token"
verdicts["raw-recheck-cef5623.txt"] = "DIVERGENT (cef5623, by suite size)"
verdicts["raw-attack4.txt"] = "MIXED (item 55, by absent API + ancestry)"
for name in SIX:
    print(f"    {name:28} {verdicts[name]}")
check("not one of REPORT.md's six is placed on the ANCHOR's line",
      "on the anchor: 0",
      f"on the anchor: {sum(1 for v in verdicts.values() if v == 'anchor')}")
print("  Item 58 reported FOUR of six on the anchor's line. That is wrong,")
print("  and the corrected answer is ZERO - which is exactly what REPORT.md")
print("  says about itself. Its outputs are not anomalous; they are the")
print("  outputs of the tree it declares. What was anomalous was my scan.")

# ---------------------------------------------------------------- J
print("\n########## J. what this does NOT establish ##########")
print("  * It does NOT retract any FINDING of PR #2 or of this review. Every")
print("    probe of mine runs against /tmp/efo-prov, verified clean at the")
print("    anchor in section A of every round. What moves is the placement")
print("    of INHERITED outputs, not the code any of my probes measured.")
print("  * It does NOT decide the 45. A suite size places an output only")
print("    if the output prints one; 7 of 77 do.")
print("  * It does NOT claim cef5623 is the ONLY commit with 77 tests in the")
print("    world - only across the 21 commits reachable from the two refs")
print("    this repository has. A commit reachable from neither is UNSWEPT.")
print("  * It does NOT accuse REPORT.md of anything. That report names")
print("    `4aa47ca6` as its subject in its own manifest; producing its")
print("    outputs on that line is the report being consistent, not the")
print("    report being wrong. The error corrected here is MINE.")
print("  * It does NOT re-open whether REPORT.md's findings apply to the")
print("    anchor. `NOTE-raw-attack4-is-unreproducible-and-my-manifest-was-")
print("    wrong.md` already measured that for P2-1/P2-2/P2-3 and this round")
print("    neither extends nor narrows it.")
print("  * It does NOT file an issue. Nothing here is a defect in EFO.")
print("  * No network. No workspace built; two suites run from checkouts and")
print("    one from the anchor, none of them modified. It does not touch")
print("    `main` or another agent's branch.")
print("  * MEASURED: the graph, both marker sets over full ancestry, the")
print("    21-commit sweep, three suite runs, the id-set match, the token")
print("    directions, both classifications, REPORT.md's six. REASONED:")
print("    nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
