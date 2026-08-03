#!/usr/bin/env python3
"""Which raw outputs came from WHICH line - and the cheap test is ONE-WAY.

CORRECTED 2026-08-03 BY QUEUE ITEM 61. The first version of this probe ended
its ANCHOR_TOKENS with a bare `"independence"` - a SUBSTRING, sitting next to
the precise `independence.py`. It matches `independence_dimensions`, which
appears in NO commit of the anchor's ancestry and is introduced by `7a9553b`
itself; and it matches `test_known_independence_cases`, a method in
`test_meta_orchestration.py`, a module only the divergent line ever had.
Eleven of the 35 outputs this probe placed on the anchor rested on that bare
token alone, and FOUR were placed BACKWARDS - among them four of `REPORT.md`'s
six cited outputs.

    published   35 anchor / 1 other / 41 undecidable
    corrected   27 anchor / 5 other / 45 undecidable

The known answer that would have caught it was inside the document being
classified: `REPORT.md:437-438` names `4aa47ca6` as its subject, a commit on
the divergent line and no ancestor of the anchor. The corrected placement
AGREES with that declaration; the published one contradicted it.

Two things changed here. Markers are derived over the WHOLE of each line
rather than from a two-commit diff, and test modules are matched by PARSING
the unittest id `tests.<module>.<class>.<method>` instead of by substring -
because `test_proxy_submission` is a prefix of
`test_proxy_submission_records_author_proxy_and_git_commit`, which lives in
the divergent module and would otherwise make a pure-divergent output look
MIXED. Sections D and F stand as published: the test still has the proven
false negative, and both extra discriminators were measured, not assumed.

`NOTE-the-suite-size-decided-it-and-a-substring-reversed-four.md` and
`raw/probe_recheck_line_and_the_substring_that_reversed_four.py` carry the
measurement. This probe is corrected, not superseded.

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

    27  carry an ANCHOR-only token  -> positively placed on the anchor's line
     5  carry divergent-only tokens -> `raw-w4-replay.txt`, my own item-55
        probe, which names both refs by design, plus the four this probe
        first placed backwards
    45  carry NEITHER              -> UNDECIDABLE by this test

AND THE TEST HAS A PROVEN FALSE NEGATIVE. `raw-attack4.txt` is in the
undecidable set - yet item 55 established, by the ABSENT API rather than by any
token, that its W4-W6b drive `7a9553b`'s line. So "no marker" does NOT mean
"the anchor's line". The test narrows; it does not decide.

Of `REPORT.md`'s six cited outputs, FOUR are positively placed on the
DIVERGENT line and TWO are undecidable by this test - `raw-attack4.txt`, known
from item 55 to be mixed, and `raw-recheck-cef5623.txt`, which item 61 places
on `cef5623` by its suite size. NOT ONE is on the anchor's line, which is what
`REPORT.md` says about itself.

Two further discriminators were considered and MEASURED rather than assumed:

    the CLI `status` JSON shape   IDENTICAL on both lines (['status','tasks'])
                                  - ruled out, not a discriminator
    the CLI subcommand list       IS a discriminator (`workspace` and `audit`
                                  exist only at 7a9553b) but appears in only
                                  2 of 77 outputs, neither of them attack4

    python3 probe_output_provenance_lines.py

SCOPE, stated first: 77 outputs, 6 cited by REPORT.md, 2 derived marker sets,
3 candidate discriminators, 1 known answer. A MAP with a NEGATIVE result.
No issue filed.
"""

from __future__ import annotations

import json
import re
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
def output_of(stem: str) -> str:
    return "raw-" + stem[len("probe_"):].replace("_", "-") + ".txt"


SELF = output_of(Path(__file__).stem)
# Item 61's probe prints both marker sets too, so it is excluded for exactly
# the reason this one is - derived from its filename, not typed as a string,
# and the exclusion is COUNTED so a third cannot appear unnoticed.
ITEM61 = output_of("probe_recheck_line_and_the_substring_that_reversed_four")
SKIP = (SELF, ITEM61)
every = sorted(p for p in RAW.iterdir()
               if p.name.startswith("raw-") and p.suffix == ".txt")
outputs = [p for p in every if p.name not in SKIP]
# These two counts are PINNED on purpose, not because they cannot be derived:
# the population is the thing under discussion, so a corpus that grows must
# force this note to be re-read rather than silently re-measured. Item 59's
# output pushed 75 -> 76 and 39 -> 40, and the pin is what said so. Item 61's
# output is excluded rather than counted, so the population stays 77.
check("  raw outputs in the corpus, the two marker-printing ones excluded",
      "outputs: 77", f"outputs: {len(outputs)}")
check("    exactly two outputs are excluded, and they are those two",
      f"excluded: ['{SELF}', '{ITEM61}']",
      f"excluded: {sorted(p.name for p in every if p.name in SKIP)}")
print("  This probe's OWN classification is therefore the one number here")
print("  that is not machine-checked; it is read off the section below.")

# ---------------------------------------------------------------- B
print("\n########## B. the markers, DERIVED from the two trees ##########")


ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
DIVERG_SHA = "cef56234a873fefddd51f8cfedb737705a6f0d9a"


def ever(ref: str, prefix: str) -> set:
    """Every .py basename that EVER exists under `prefix` on `ref`'s line.

    Corrected by item 61: the published version diffed TWO commits, which
    cannot see a file that was added and removed, and did not know that
    `cef5623` - a descendant of `7a9553b` - carries the tree that produced
    `raw-recheck-cef5623.txt`.
    """
    names = set()
    for commit in git(ANCHOR, "rev-list", ref).split():
        for path in git(ANCHOR, "ls-tree", "-r", "--name-only",
                        commit, prefix).split():
            if path.endswith(".py"):
                names.add(path.rsplit("/", 1)[-1])
    return names


anchor_modules = ever(ANCHOR_SHA, "src/evidence_orchestrator/")
other_modules = ever(DIVERG_SHA, "src/evidence_orchestrator/")
anchor_tests = ever(ANCHOR_SHA, "tests/")
other_tests = ever(DIVERG_SHA, "tests/")
only_other = sorted(other_modules - anchor_modules)
only_anchor = sorted(anchor_modules - other_modules)
print(f"    modules only on the divergent line : {only_other}")
print(f"    modules only on the anchor's       : {only_anchor}")
print(f"    test modules only on the divergent : "
      f"{sorted(other_tests - anchor_tests)}")
print(f"    test modules only on the anchor's  : "
      f"{sorted(anchor_tests - other_tests)}")
check("modules present only on the divergent line",
      "only other: ['fingerprint.py', 'identity.py', 'job_runner.py']",
      f"only other: {only_other}")
check("  and present only on the anchor's",
      "only anchor: ['independence.py']", f"only anchor: {only_anchor}")
print("  A TWO-WAY discriminator, which is stronger than the one-way test the")
print("  item proposed: an output can be placed on EITHER line, not just")
print("  flagged as belonging to the other one.")

OTHER_TOKENS = tuple(only_other) + (
    "transfer_orchestrator", "transfer-orchestrator",
    "orchestrator_transferred", "independence_dimensions")
# NO bare "independence" here. Item 61 measured why: it matches
# `independence_dimensions`, which is a DIVERGENT-line token, and
# `test_known_independence_cases`, a divergent-line test method.
ANCHOR_TOKENS = tuple(only_anchor) + ("audit-independence",
                                      "transport_independence")
ANCHOR_TEST_MODULES = {p[:-3] for p in anchor_tests - other_tests}
OTHER_TEST_MODULES = {p[:-3] for p in other_tests - anchor_tests}
# PARSED, not substring-matched: `test_proxy_submission` is a prefix of a
# method name inside the divergent `test_meta_orchestration`.
TEST_ID = re.compile(r"tests\.(test_[A-Za-z0-9_]+)\.")
check("  the bare substring is gone from the anchor token set",
      "bare present: False",
      f"bare present: {'independence' in ANCHOR_TOKENS}")

# ---------------------------------------------------------------- C
print("\n########## C. the scan ##########")
placed_anchor, placed_other, undecidable = [], [], []
mixed = []
for path in outputs:
    text = path.read_text(encoding="utf-8", errors="replace")
    named = set(TEST_ID.findall(text))
    found_other = ([token for token in OTHER_TOKENS if token in text]
                   + sorted(named & OTHER_TEST_MODULES))
    found_anchor = ([token for token in ANCHOR_TOKENS if token in text]
                    + sorted(named & ANCHOR_TEST_MODULES))
    if found_other and found_anchor:
        mixed.append(path.name)
        print(f"    BOTH lines' tokens   {path.name}  "
              f"{found_anchor} / {found_other}")
    elif found_other:
        placed_other.append(path.name)
        print(f"    divergent-only tokens  {path.name}  {found_other}")
    elif found_anchor:
        placed_anchor.append(path.name)
    else:
        undecidable.append(path.name)
check("outputs positively placed on the ANCHOR's line", "anchor: 27",
      f"anchor: {len(placed_anchor)}")
check("  outputs carrying a divergent-only token", "other: 5",
      f"other: {len(placed_other)}")
check("    my own item-55 probe among them, which names both refs by design",
      "raw-w4-replay.txt", f"other: {placed_other}")
check("    and the four this probe first placed BACKWARDS",
      "['raw-attack2-cef5623.txt', 'raw-attack2.txt', 'raw-attack3.txt', "
      "'raw-full-final.txt', 'raw-w4-replay.txt']",
      f"other: {sorted(placed_other)}")
check("  outputs carrying tokens from BOTH lines", "mixed: 0",
      f"mixed: {len(mixed)}")
check("  outputs the test cannot place", "undecidable: 45",
      f"undecidable: {len(undecidable)}")
check("    and the four classes account for every output",
      f"total: {len(outputs)}",
      f"total: {len(placed_anchor) + len(placed_other) + len(mixed) + len(undecidable)}")

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
             else "DIVERGENT" if name in placed_other
             else "mixed" if name in mixed else "undecidable")
    print(f"    {name:<30}{where}")
check("REPORT.md cites six outputs with no probe of mine beside them",
      "cited: 6", f"cited: {len(cited)}")
check("  NOT ONE is positively placed on the anchor's line", "on anchor: 0",
      f"on anchor: {sum(1 for n in cited if n in placed_anchor)}")
check("    four are positively placed on the DIVERGENT line",
      "on divergent: 4",
      f"on divergent: {sum(1 for n in cited if n in placed_other)}")
check("    and two are undecidable BY THIS TEST",
      "undecidable: ['raw-attack4.txt', 'raw-recheck-cef5623.txt']",
      f"undecidable: {[n for n in cited if n in undecidable]}")
report = (REVIEWS / "REPORT.md").read_text(encoding="utf-8")
subject = [line.strip() for line in report.splitlines()
           if line.startswith("4aa47ca")]
check("  and REPORT.md names its own subject on the DIVERGENT line",
      "4aa47ca6", subject[0] if subject else "not found")
print("  So the corrected placement AGREES with what REPORT.md declares.")
print("  The published version said FOUR were on the anchor's line, which")
print("  contradicted that declaration - the known answer was three lines")
print("  from the manifest item 46 read, and this probe did not check")
print("  against it. Item 61 does.")
print("  Of the two left undecidable here: raw-attack4.txt is the file item")
print("  55 showed to be MIXED, and raw-recheck-cef5623.txt is placed on")
print("  cef5623 by item 61, using its SUITE SIZE - a discriminator this")
print("  token scan is structurally unable to see.")

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
print("  * It does not decide the 45. It says which 27 sit on the anchor's")
print("    line and which 5 on the divergent one, and that the remaining 45")
print("    are OPEN - including one already known to be mixed.")
print("  * Its first published answer, 35 / 1 / 41, was WRONG - a bare")
print("    substring in the anchor token set. Item 61 measured that; this")
print("    probe is the corrected version, not a second opinion.")
print("  * It does not re-run any catalogued output, and does not retract")
print("    item 46's catalogue or its two re-runs.")
print("  * It does not claim the token sets are the only possible markers.")
print("    Two more were considered; one was ruled out by measurement and one")
print("    is real but almost never present.")
print("  * It does not file an issue: nothing here is a defect in EFO. It is")
print("    a fact about the PROVENANCE of evidence this review inherited.")
print("  * No network. Two local checkouts and one tempfile workspace pair,")
print("    removed above. The anchor's working tree is untouched.")
print("  * MEASURED: both marker sets over the whole of each line, the")
print("    four-way scan of all 77 outputs, REPORT.md's six and its declared")
print("    subject, both status shapes, the usage-line census, item 55's two")
print("    quoted sentences. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Two refs read and named. No `main` write, no issue filed, nothing")
print("retracted. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
