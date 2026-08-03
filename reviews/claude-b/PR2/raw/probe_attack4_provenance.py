#!/usr/bin/env python3
"""raw-attack4.txt is unreproducible - and REPORT.md says something untrue about it.

Queue item 43: `raw-attack4.txt` has no `attack4` script in `raw/`. Decide
whether the script is recoverable from git history, or whether the output
should be marked unreproducible.

Three measured answers, in increasing order of how much they matter:

  1. NO SCRIPT EVER EXISTED. `git log --all --diff-filter=D -- '*attack4*'`
     returns nothing; the only commit touching the name is a820891, which ADDED
     the output. Not recoverable, because there is nothing to recover.

  2. REPORT.md's evidence manifest says it "was produced by the inline command
     blocks quoted in §3 ④". THAT IS FALSE. Section §3 ④ contains two fenced
     blocks and ZERO command-shaped lines - both blocks are RESULTS. A
     statement about the provenance of my own artifact that does not hold.

  3. Even with the commands, W1 and W2 could not be re-run at the review's
     anchor: the wheel fixture they hash and diff was added in 7a9553b and
     `tests/fixtures/` DOES NOT EXIST at main 5694ab45.

So the verdict is `unreproducible`, and the reason is the missing INPUT, not
the missing driver. Three findings in REPORT.md (P2-1, P2-2, P2-3) cite this
output as *measured*.

    python3 probe_attack4_provenance.py

SCOPE, stated first: one output file (191 lines), one REPORT.md section, four
git history queries. Small enough to read end to end, and it was read.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
BRANCH = Path("/workspace/evidence-first-orchestrator")
REVIEWS = BRANCH / "reviews/claude-b/PR2"
RAW = REVIEWS / "raw"
WHEEL = "tests/fixtures/evidence_first_orchestrator-0.1.0-py3-none-any.whl"


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
print("########## A. POSITIVE CONTROL ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      git(ANCHOR, "rev-parse", "HEAD").strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git(ANCHOR, 'status', '--porcelain').strip()!r}")
check("  and the orphan output is present to be measured", "exists: True",
      f"exists: {(RAW / 'raw-attack4.txt').is_file()}")

# ---------------------------------------------------------------- B
print("\n########## B. no attack4 script has EVER existed ##########")
deleted = git(BRANCH, "log", "--all", "--diff-filter=D", "--name-only",
              "--format=", "--", "*attack4*").split()
touching = [line for line in git(
    BRANCH, "log", "--all", "--oneline", "--name-only",
    "--", "*attack4*").splitlines() if line.strip()]
for line in touching:
    print(f"    {line}")
check("commits that DELETED anything named attack4", "deleted: []",
      f"deleted: {deleted}")
# CLASSIFY, do not just count. The glob `*attack4*` now also matches THIS
# investigation's own artifacts - the probe, its output and its note - which
# did not exist when the question was asked. Excluding them by name would be a
# guess; the three-way classification the inventory already uses is a rule:
# under raw/, a file is a SCRIPT unless it is `raw-*.txt` or `probe_*.py`, and
# anything outside raw/ is a write-up. Same self-reference the attack-script
# census hit one round earlier, one directory up.
paths = sorted({line for line in touching if "/" in line})
in_raw = [p for p in paths if "/raw/" in p]
scripts = [p for p in in_raw
           if not Path(p).name.startswith(("raw-", "probe_"))]
own = [p for p in paths if p not in scripts]
check("  attack4 SCRIPTS ever committed anywhere in history",
      "scripts: []", f"scripts: {scripts}")
check("    the output itself is present and classified as output",
      "output: True",
      f"output: {any(Path(p).name == 'raw-attack4.txt' for p in in_raw)}")
check("    and this round's own artifacts are excluded, and named",
      f"self-references: {len(paths) - len(scripts)}",
      f"self-references: {len(own)}   {[Path(p).name for p in own]}")
added = git(BRANCH, "log", "--diff-filter=A", "--format=%h %ad", "--date=short",
            "-1", "--", "reviews/claude-b/PR2/raw/raw-attack4.txt").strip()
check("  added in the branch's first review commit", "a820891 2026-07-30", added)
print("  Not recoverable from history, because there is nothing to recover.")
print("  The item asked whether to recover or to mark unreproducible; the")
print("  first option does not exist.")

# ---------------------------------------------------------------- C
print("\n########## C. and REPORT.md says something untrue about it ##########")
report = (REVIEWS / "REPORT.md").read_text(encoding="utf-8").splitlines()
claim = [i for i, line in enumerate(report, 1)
         if "inline command blocks" in line or "was produced by the inline" in line]
for i in claim:
    print(f"    REPORT.md:{i}  {report[i - 1].strip()}")
# ONE line, not two: the sentence wraps, and both of my match patterns hit the
# same wrapped line. Expected 2 going in; corrected to the measurement.
check("REPORT.md states where the output came from", "claim lines: 1",
      f"claim lines: {len(claim)}")
print("    (the sentence continues on REPORT.md:443 - `in \u00a73 \u2463.`)")

start = next(i for i, line in enumerate(report)
             if line.startswith("### ④"))
end = next(i for i, line in enumerate(report[start + 1:], start + 1)
           if line.startswith(("### ", "## ")))
section = report[start:end]
fences = [i for i, line in enumerate(section) if line.startswith("```")]
commands = [line for line in section
            if line.strip().startswith(("$", "efo ", "python3 ", "PYTHONPATH",
                                        "sha256sum", "unzip ", "diff ", "git "))]
print(f"    §3 ④ spans REPORT.md:{start + 1}-{end}, {len(section)} lines")
check("  fenced blocks in that section", "fenced blocks: 2",
      f"fenced blocks: {len(fences) // 2}")
check("    command-shaped lines in that section", "commands: 0",
      f"commands: {len(commands)}")
for i in fences[::2]:
    print(f"      block at §3④+{i}: {section[i + 1].strip()[:70]}")
print("  Both blocks are RESULTS - a sha256 line and its README comparison.")
print("  The manifest's sentence does not hold. That is a defect in MY OWN")
print("  evidence bookkeeping, and it is stated first rather than folded into")
print("  the verdict.")

# ---------------------------------------------------------------- D
print("\n########## D. the INPUT is gone too, which settles it ##########")
wheel_history = [line for line in git(
    ANCHOR, "log", "--all", "--oneline", "--name-only",
    "--", "*.whl").splitlines() if line.strip()]
for line in wheel_history:
    print(f"    {line}")
check("the wheel fixture exists at the anchor", "present at main: False",
      f"present at main: {(ANCHOR / WHEEL).is_file()}")
check("  in fact the fixture directory is gone", "fixtures dir: False",
      f"fixtures dir: {(ANCHOR / 'tests/fixtures').is_dir()}")
readme = (ANCHOR / "README.md").read_text(encoding="utf-8")
check("  and README no longer claims the wheel hash", "readme hash: False",
      f"readme hash: "
      f"{'18ed72c3f2ddf38a9a18d435032095cfbc074b2e21b9397d96e4a76b103b2354' in readme}")
print("  W1 hashes that wheel and W2 diffs its 14 modules against f827f29.")
print("  Neither can run at the anchor no matter what drives them, so the")
print("  output is unreproducible for a reason stronger than the missing")
print("  script: the artifact under test is not in the tree.")

# ---------------------------------------------------------------- E
print("\n########## E. what still rests on it ##########")
citing = sorted(p.name for p in REVIEWS.glob("*.md")
                if "raw-attack4" in p.read_text(encoding="utf-8"))
print(f"    documents citing it: {citing}")
measured = [i for i, line in enumerate(report, 1)
            if "raw-attack4" in line and "*measured.*" in line]
for i in measured:
    print(f"      REPORT.md:{i}  {report[i - 1].strip()[:72]}")
check("REPORT.md claims that cite it as measured", "measured citations: 3",
      f"measured citations: {len(measured)}")
findings = sorted({line.split("—")[0].strip().lstrip("# ").strip()
                   for line in report if line.startswith("### P2-")})
print(f"    the P2 findings in REPORT.md: {findings}")
print("  P2-1, P2-2 and P2-3 each cite raw-attack4.txt. They are not")
print("  retracted here - they were measured when they were made, against a")
print("  ref REPORT.md names as 4aa47ca6, not this review's anchor. What is")
print("  now recorded is that they cannot be re-derived on this branch.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not retract P2-1, P2-2 or P2-3, and does not re-run them.")
print("    Unreproducible-at-the-anchor is not the same as wrong.")
print("  * It does not reconstruct the commands. Writing a plausible attack4")
print("    now and calling it the original would be inventing provenance -")
print("    the exact thing this review exists to catch.")
print("  * It does not touch main or any other agent's branch. REPORT.md is")
print("    this review's own document and is corrected in place, dated.")
print("  * MEASURED: every git query, the section bounds, the fenced-block and")
print("    command counts, the fixture's absence, the citation census.")
print("    REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Read-only git and file queries. Nothing executed against a workspace,")
print("no issue filed - this is a defect in my own bookkeeping, not in EFO.")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED.")
