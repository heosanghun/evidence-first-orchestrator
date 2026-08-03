#!/usr/bin/env python3
"""Which raw outputs came from WHICH line - and the cheap test is ONE-WAY.

Queue item 58, from item 55. `raw-attack4.txt` mixes two lines of history: its
W1/W2/W2b compare against `f827f29`, the anchor's ancestor, while W4-W6b drive
`transfer_orchestrator`, which exists only at `7a9553b` - a commit that is NOT
an ancestor of the anchor. Item 46 catalogued `REPORT.md`'s six cited outputs
and re-ran two; none of that asked WHICH v2 produced them.

The markers are DERIVED, not named - the module-set difference between the two
trees:

    only at 7a9553b : identity.py, job_runner.py  (+ transfer_orchestrator,
                      transfer-orchestrator, orchestrator_transferred)
    only at anchor  : independence.py             (+ audit-independence)

A TWO-WAY discriminator, which is better than the one-way test the item
proposed. Scanned across every `raw-*.txt`:

    35  carry an ANCHOR-only token  -> positively placed on the anchor's line
     1  carries 7a9553b-only tokens -> `raw-w4-replay.txt`, my own item-55
        probe, which names both refs by design
    40  carry NEITHER              -> UNDECIDABLE by this test

AND THE TEST HAS A PROVEN FALSE NEGATIVE. `raw-attack4.txt` is in the
undecidable set - yet item 55 established, by the ABSENT API rather than by any
token, that its W4-W6b drive `7a9553b`'s line. So "no marker" does NOT mean
"the anchor's line". The test narrows; it does not decide.

Of `REPORT.md`'s six cited outputs, FOUR are positively placed on the anchor's
line and TWO are undecidable - `raw-attack4.txt`, known to be mixed, and
`raw-recheck-cef5623.txt`.

Two further discriminators were considered and MEASURED rather than assumed:

    the CLI `status` JSON shape   IDENTICAL on both lines (['status','tasks'])
                                  - ruled out, not a discriminator
    the CLI subcommand list       IS a discriminator (`workspace` and `audit`
                                  exist only at 7a9553b) but appears in only
                                  2 of 76 outputs, neither of them attack4

    python3 probe_output_provenance_lines.py

SCOPE, stated first: 76 outputs, 6 cited by REPORT.md, 2 derived marker sets,
3 candidate discriminators, 1 known answer. A MAP with a NEGATIVE result.
No issue filed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
OTHER = Path("/tmp/efo-7a9553b")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item58-")).resolve()


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


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      git(ANCHOR, "rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git(ANCHOR, 'status', '--porcelain')!r}")
check("  the second checkout is still 7a9553b", "7a9553b",
      git(OTHER, "rev-parse", "--short=7", "HEAD"))

# THIS probe's own output lives inside the corpus it scans, and it PRINTS the
# 7a9553b-only tokens, so an unexcluded run classifies itself as coming from
# the other line - a self-reference with no fixpoint, the same shape as
# probe_inventory_selfcheck.py's tally. Excluded STRUCTURALLY, from this
# script's own name rather than a hardcoded string, and the exclusion is
# COUNTED so a second one cannot appear unnoticed.
SELF = "raw-" + Path(__file__).stem[len("probe_"):].replace("_", "-") + ".txt"
every = sorted(p for p in RAW.iterdir()
               if p.name.startswith("raw-") and p.suffix == ".txt")
outputs = [p for p in every if p.name != SELF]
# These two counts are PINNED on purpose, not because they cannot be derived:
# the population is the thing under discussion, so a corpus that grows must
# force this note to be re-read rather than silently re-measured. Item 59's
# output pushed 75 -> 76 and 39 -> 40, and the pin is what said so.
check("  raw outputs in the corpus, this probe's own excluded",
      "outputs: 76", f"outputs: {len(outputs)}")
check("    exactly one output is excluded, and it is this one",
      f"excluded: ['{SELF}']",
      f"excluded: {[p.name for p in every if p.name == SELF]}")
print("  This probe's OWN classification is therefore the one number here")
print("  that is not machine-checked; it is read off the section below.")

# ---------------------------------------------------------------- B
print("\n########## B. the markers, DERIVED from the two trees ##########")


def modules(ref: str, repository: Path) -> set:
    listing = git(repository, "ls-tree", "-r", "--name-only", ref,
                  "src/evidence_orchestrator/").split()
    return {path.rsplit("/", 1)[-1] for path in listing
            if path.endswith(".py")}


anchor_modules = modules("5694ab45", ANCHOR)
other_modules = modules("7a9553b", OTHER)
only_other = sorted(other_modules - anchor_modules)
only_anchor = sorted(anchor_modules - other_modules)
print(f"    only at 7a9553b : {only_other}")
print(f"    only at anchor  : {only_anchor}")
check("modules present only on 7a9553b's line",
      "only other: ['identity.py', 'job_runner.py']",
      f"only other: {only_other}")
check("  and present only on the anchor's",
      "only anchor: ['independence.py']", f"only anchor: {only_anchor}")
print("  A TWO-WAY discriminator, which is stronger than the one-way test the")
print("  item proposed: an output can be placed on EITHER line, not just")
print("  flagged as belonging to the other one.")

OTHER_TOKENS = tuple(only_other) + (
    "transfer_orchestrator", "transfer-orchestrator",
    "orchestrator_transferred")
ANCHOR_TOKENS = tuple(only_anchor) + ("audit-independence", "independence")

# ---------------------------------------------------------------- C
print("\n########## C. the scan ##########")
placed_anchor, placed_other, undecidable = [], [], []
for path in outputs:
    text = path.read_text(encoding="utf-8", errors="replace")
    found_other = [token for token in OTHER_TOKENS if token in text]
    found_anchor = [token for token in ANCHOR_TOKENS if token in text]
    if found_other:
        placed_other.append(path.name)
        print(f"    7a9553b-only tokens  {path.name}  {found_other}")
    elif found_anchor:
        placed_anchor.append(path.name)
    else:
        undecidable.append(path.name)
check("outputs positively placed on the ANCHOR's line", "anchor: 35",
      f"anchor: {len(placed_anchor)}")
check("  outputs carrying a 7a9553b-only token", "other: 1",
      f"other: {len(placed_other)}")
check("    and it is my OWN item-55 probe, which names both refs",
      "other: ['raw-w4-replay.txt']", f"other: {placed_other}")
check("  outputs the test cannot place", "undecidable: 40",
      f"undecidable: {len(undecidable)}")
check("    and the three classes account for every output",
      f"total: {len(outputs)}",
      f"total: {len(placed_anchor) + len(placed_other) + len(undecidable)}")

# ---------------------------------------------------------------- D
print("\n########## D. the KNOWN ANSWER that shows the test is ONE-WAY ##########")
check("raw-attack4.txt is in the UNDECIDABLE set",
      "attack4 undecidable: True",
      f"attack4 undecidable: {'raw-attack4.txt' in undecidable}")
item55 = (REVIEWS / "NOTE-w4-needs-a-ref-the-anchor-never-took.md").read_text(
    encoding="utf-8").replace("\n", " ")
check("  yet item 55 placed its W4-W6b on 7a9553b's line",
      "W4, W5, W6 and W6b drive a v2 that only exists on the other line",
      item55)
check("    by the ABSENT API and the ancestry, not by any token in the output",
      "git merge-base --is-ancestor 7a9553b 5694ab45", item55)
print("  So \"no marker\" does NOT mean \"the anchor's line\". The test NARROWS")
print("  the population and cannot decide it. Saying so is the result; a")
print("  filter checked in only one direction is what item 50 refuted.")

# ---------------------------------------------------------------- E
print("\n########## E. REPORT.md's six cited outputs ##########")
item46 = (REVIEWS /
          "NOTE-two-of-REPORTs-outputs-were-re-run-not-merely-catalogued.md"
          ).read_text(encoding="utf-8")
cited = sorted({name for name in
                __import__("re").findall(r"raw-[a-z0-9-]+\.txt", item46)
                if (RAW / name).is_file()
                and not (RAW / ("probe_" + name[4:-4].replace("-", "_")
                                + ".py")).is_file()})
for name in cited:
    where = ("ANCHOR" if name in placed_anchor
             else "7a9553b" if name in placed_other else "undecidable")
    print(f"    {name:<30}{where}")
check("REPORT.md cites six outputs with no probe of mine beside them",
      "cited: 6", f"cited: {len(cited)}")
check("  four are positively placed on the anchor's line",
      "on anchor: 4",
      f"on anchor: {sum(1 for n in cited if n in placed_anchor)}")
check("    and two are undecidable",
      "undecidable: ['raw-attack4.txt', 'raw-recheck-cef5623.txt']",
      f"undecidable: {[n for n in cited if n in undecidable]}")
print("  One of those two is the file item 55 already showed to be MIXED.")
print("  The other, raw-recheck-cef5623.txt, is left open - item 46 re-ran its")
print("  suite section (77/77, OK) without asking which v2 produced it, and")
print("  this round does not answer that either.")

# ---------------------------------------------------------------- F
print("\n########## F. two more discriminators, MEASURED not assumed ##########")
shapes = {}
try:
    for label, source in (("anchor", ANCHOR / "src"),
                          ("7a9553b", OTHER / "src")):
        workspace = ROOT / label
        subprocess.run(
            ["python3", "-m", "evidence_orchestrator", "init", str(workspace),
             "--name", "x", "--preset", "antigravity-codex-claude"],
            capture_output=True, text=True, timeout=120,
            env={"PYTHONPATH": str(source), "PATH": "/usr/bin:/bin",
                 "HOME": "/tmp", "LC_ALL": "C.UTF-8"})
        done = subprocess.run(
            ["python3", "-m", "evidence_orchestrator", "status",
             str(workspace)],
            capture_output=True, text=True, timeout=120,
            env={"PYTHONPATH": str(source), "PATH": "/usr/bin:/bin",
                 "HOME": "/tmp", "LC_ALL": "C.UTF-8"})
        shapes[label] = sorted(json.loads(done.stdout))
finally:
    shutil.rmtree(ROOT, ignore_errors=True)
print(f"    CLI status keys, anchor  : {shapes['anchor']}")
print(f"    CLI status keys, 7a9553b : {shapes['7a9553b']}")
check("the status shape is IDENTICAL on both lines - NOT a discriminator",
      "identical: True", f"identical: {shapes['anchor'] == shapes['7a9553b']}")
usage = [path.name for path in outputs
         if "usage: efo" in path.read_text(encoding="utf-8", errors="replace")]
print(f"    outputs containing a CLI usage line: {usage}")
check("  the subcommand list IS a discriminator, but appears in only two",
      "with usage: 2", f"with usage: {len(usage)}")
check("    and neither of them is raw-attack4.txt",
      "attack4 among them: False",
      f"attack4 among them: {'raw-attack4.txt' in usage}")
print("  `workspace` and `audit` are subcommands only 7a9553b has, so a usage")
print("  line would settle it - but the corpus almost never records one.")

print("\n########## G. what this does NOT do ##########")
print("  * It does not decide the 39. It says which 35 are placed, which one")
print("    is mine, and that the remaining 39 are OPEN - including one already")
print("    known to be mixed.")
print("  * It does not re-run any catalogued output, and does not retract")
print("    item 46's catalogue or its two re-runs.")
print("  * It does not claim the token sets are the only possible markers.")
print("    Two more were considered; one was ruled out by measurement and one")
print("    is real but almost never present.")
print("  * It does not file an issue: nothing here is a defect in EFO. It is")
print("    a fact about the PROVENANCE of evidence this review inherited.")
print("  * No network. Two local checkouts and one tempfile workspace pair,")
print("    removed above. The anchor's working tree is untouched.")
print("  * MEASURED: both module sets, the three-way scan of all 75 outputs,")
print("    REPORT.md's six, both status shapes, the usage-line census, item")
print("    55's two quoted sentences. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Two refs read and named. No `main` write, no issue filed, nothing")
print("retracted. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
