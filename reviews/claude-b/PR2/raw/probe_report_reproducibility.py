#!/usr/bin/env python3
"""Two of REPORT.md's outputs are not unreproducible - they were RE-RUN here.

Queue item 46. Item 43 established that `raw-attack4.txt` is unreproducible and
that REPORT.md's provenance sentence about it was false, and asked which OTHER
REPORT.md claims cite raw outputs whose inputs are absent at the anchor.

The answer is better than the question expected:

  * BOTH refs REPORT.md names - 4aa47ca6 and cef56234 - EXIST in this
    repository. The item's framing ("neither the anchor nor any ref the other
    write-ups assert") is true but does not mean unreachable.
  * THREE of six cited outputs have no producer script in raw/ - attack4,
    full-final, recheck-cef5623 - but only ONE of those is actually
    unreproducible.
  * `raw-full-final.txt` and the suite section of `raw-recheck-cef5623.txt`
    were RE-RUN in this container. unittest is stdlib, so the absence of
    pytest never mattered. 70/70 and 77/77, both OK, both exit 0, both
    matching the committed numbers.

So the honest verdict is narrower than "REPORT.md rests on unreproducible
evidence": one output is unreproducible (the wheel fixture is gone), two were
reproduced today, and three have their scripts on the branch.

    python3 probe_report_reproducibility.py

SCOPE, stated first: 6 cited outputs, 4 cited scripts, 6 `*measured.*` claim
lines, 2 named refs. Small enough to adjudicate each, and each is adjudicated.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"
REFS = {"4aa47ca602d36c22cbaf2ce63fa442ee398c317e": Path("/tmp/efo-4aa47ca"),
        "cef56234a873fefddd51f8cfedb737705a6f0d9a": Path("/tmp/efo-cef5623")}
RERUN = {"raw-full-final.txt": "4aa47ca602d36c22cbaf2ce63fa442ee398c317e",
         "raw-recheck-cef5623.txt": "cef56234a873fefddd51f8cfedb737705a6f0d9a"}


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True).stdout


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      git(ANCHOR, "rev-parse", "HEAD").strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git(ANCHOR, 'status', '--porcelain').strip()!r}")

report = (REVIEWS / "REPORT.md").read_text(encoding="utf-8")
outputs = sorted(set(re.findall(r"`raw/(raw-[a-z0-9._-]+\.txt)`", report)))
scripts = sorted(set(re.findall(r"`raw/([a-z0-9._-]+\.(?:sh|py))`", report)))
claims = [line for line in report.splitlines() if "*measured.*" in line]
named = sorted(set(re.findall(r"`([0-9a-f]{40})`", report)))
check("raw outputs REPORT.md cites", "outputs: 6", f"outputs: {len(outputs)}")
check("  scripts it cites", "scripts: 4", f"scripts: {len(scripts)}")
check("  `*measured.*` claim lines", "claims: 6", f"claims: {len(claims)}")
check("  and refs it names as its subject", "refs: 2", f"refs: {len(named)}")
print(f"    {outputs}")
print("  Small enough to adjudicate each, and each is adjudicated below.")

# ---------------------------------------------------------------- B
print("\n########## B. both named refs EXIST - the item implied otherwise ##########")
for ref in named:
    present = subprocess.run(["git", "-C", str(ANCHOR), "cat-file", "-e",
                              f"{ref}^{{commit}}"]).returncode == 0
    subject = git(ANCHOR, "log", "-1", "--format=%ad %s", "--date=short",
                  ref).strip()[:62]
    print(f"    {ref[:8]}  exists={present}  {subject}")
check("REPORT.md's subject refs are reachable in this repository",
      "missing refs: []",
      "missing refs: "
      + str([r[:8] for r in named
             if subprocess.run(["git", "-C", str(ANCHOR), "cat-file", "-e",
                                f"{r}^{{commit}}"]).returncode != 0]))
print("  Neither is the review's anchor, and no other write-up asserts them -")
print("  that part of item 46 holds. But `not the anchor` is not `unreachable`,")
print("  and the difference is the whole result.")

# ---------------------------------------------------------------- C
print("\n########## C. which cited outputs have no producer on the branch ##########")
have = sorted(p.name for p in RAW.iterdir()
              if p.suffix in (".sh", ".py") and not p.name.startswith("probe_"))
orphans = []
for output in outputs:
    stem = output[len("raw-"):-len(".txt")]
    producers = [s for s in have if s.rsplit(".", 1)[0].replace("_", "-")
                 in stem or stem.split("-")[0] in s]
    print(f"    {output:<26} producers: {producers or 'NONE'}")
    if not producers:
        orphans.append(output)
check("cited outputs with no producer script in raw/", "orphans: 3",
      f"orphans: {len(orphans)}   {orphans}")
print("  Item 43 covered attack4. The other two are this item's subject, and")
print("  the next section stops guessing about them.")

# ---------------------------------------------------------------- D
print("\n########## D. EXECUTED - two of the three were RE-RUN here ##########")
print("  unittest is STDLIB, so `no pytest` never blocked these. Saying they")
print("  could not be reproduced without trying would have been the error.")
for output, ref in RERUN.items():
    tree = REFS[ref]
    if not (tree / "src").is_dir():
        check(f"{output}: checkout present", "checkout: True",
              f"checkout: {tree.is_dir()}")
        continue
    head = git(tree, "rev-parse", "HEAD").strip()
    committed = re.search(r"Ran (\d+) tests", (RAW / output).read_text(
        encoding="utf-8", errors="replace"))
    result = subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=tree, capture_output=True, text=True,
        env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"})
    fresh = re.search(r"Ran (\d+) tests", result.stderr)
    print(f"    {output}")
    print(f"      ref under test   {head[:8]}  (named by REPORT.md)")
    print(f"      committed output says   Ran {committed.group(1)} tests")
    print(f"      this run says           Ran {fresh.group(1)} tests, "
          f"exit {result.returncode}")
    # KNOWN ANSWER: the committed number is the expectation, the fresh run the
    # observation. Neither side is typed in by me.
    check(f"  {output}: the re-run matches the committed count",
          f"tests: {committed.group(1)}", f"tests: {fresh.group(1)}")
    check("    and the suite passes", "OK", result.stderr.strip().splitlines()[-1])
    check("    with exit 0", "exit: 0", f"exit: {result.returncode}")
    check("    and NO skips - `OK` carries no (skipped=N) suffix",
          "skipped: 0",
          f"skipped: {len(re.findall(r'skipped=', result.stderr))}")

# ---------------------------------------------------------------- E
print("\n########## E. what is still unreproducible, and why ##########")
wheel = "tests/fixtures/evidence_first_orchestrator-0.1.0-py3-none-any.whl"
check("the v0.1 wheel fixture at the anchor", "present: False",
      f"present: {(ANCHOR / wheel).is_file()}")
recheck = (RAW / "raw-recheck-cef5623.txt").read_text(encoding="utf-8")
sections = re.findall(r"#{5,} (.+?) #{5,}", recheck)
print(f"    raw-recheck-cef5623.txt has {len(sections)} sections: {sections}")
check("  of which the SUITE section is the one re-run above",
      "suite sections: 1",
      f"suite sections: {sum('suite' in s for s in sections)}")
print("  The P2-1 and P2-2 sections drive the v0.1 CLIENT, which comes from")
print("  the wheel that is absent at the anchor - the same reason item 43 gave")
print("  for raw-attack4.txt. So `raw-recheck-cef5623.txt` is PARTLY")
print("  reproducible: its suite section was re-run, its two recheck sections")
print("  cannot be. That distinction did not exist before this pass.")
print("  attack2.sh and attack3.sh ship on the branch but declare the")
print("  branch's own unpinned tree - item 40 - so they run, but not against")
print("  the ref REPORT.md names.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not re-run the attack scripts. Item 40 measured that two of")
print("    them target an unpinned tree; re-running them now would measure")
print("    today's branch, not the ref under review.")
print("  * It does not retract or re-confirm P2-1, P2-2, P2-3 or P2-4. Two")
print("    SUITE runs were reproduced; the FINDINGS rest on the recheck and")
print("    attack sections, which is a different question.")
print("  * It does not touch main or any other agent's branch. The two")
print("    checkouts are local clones under /tmp and nothing was written to")
print("    either working tree.")
print("  * MEASURED: every count, both ref lookups, the producer census, both")
print("    re-runs and their exit codes, the wheel's absence, the section")
print("    split. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static reads plus two unittest runs against local checkouts of refs")
print("REPORT.md names. No network, no workspace mutation, no issue filed.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED.")
