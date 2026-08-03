#!/usr/bin/env python3
"""Every count this review states about ITSELF, checked against the files.

Queue item 34. `SYNTHESIS.md`'s inventory has been recounted BY HAND five
times, and each time the note said "not yet machine-checked" - which is honest
and useless. This makes it self-checking, the way `probe_citation_audit.py` §F
and `probe_quote_accuracy.py` §E already are.

It then goes further, because surveying the branch turned up a bigger gap:
**30 write-ups each state "N checks, M unexpected" in their opening paragraph,
and nothing has ever verified one of them.** Those numbers are the headline of
every document here. They are now compared against the raw output each
document names.

A stale count is indistinguishable from an invented one, which is the failure
this project exists to prevent. The run FAILS on any disagreement.

    python3 probe_inventory_selfcheck.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def tally(path: Path) -> tuple[int, int]:
    """(passing checks, unexpected results) in one raw output.

    Counted by POSITION, not by substring. This used `text.count("[ok]")` and
    `text.count("!! UNEXPECTED !!")`, which counted every occurrence anywhere -
    including inside a check's own NAME and inside explanatory prose. Two live
    examples, both found by this fix:

      * `raw-attack-provenance.txt` has a check literally named `none of the
        attack outputs uses the [ok] convention`, plus a prose line quoting the
        same token. Substring counting made a 10-check probe report 12.
      * `raw-attack-prov5-main.txt` has ONE finding (`G2b  !! UNEXPECTED !!`)
        and one legend line reading `Any '!! UNEXPECTED !!' above is a
        finding`. Substring counting made one failure look like two.

    Two result conventions exist in raw/ and both are recognised structurally:
    the `check()` convention prints the marker BRACKETED at the start of the
    line, and the older attack scripts print a bare `!! UNEXPECTED !!` at the
    END of a status line with no `[ok]` counterpart. A marker anywhere else on
    a line is prose and is not a result.

    A first attempt at this used `endswith` for BOTH markers - and matched 163
    ordinary sentences that happen to end in the letters `ok`, inflating the
    census from 740 to 922. The filter was checked against a known answer
    before it was believed, which is the only reason that is a footnote rather
    than a number in SYNTHESIS.
    """
    ok = bad = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith("[ok]"):
            ok += 1
        if (stripped.startswith("[!! UNEXPECTED !!]")
                or stripped.endswith("!! UNEXPECTED !!")):
            bad += 1
    return ok, bad


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(ANCHOR), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("the review's anchor is unmoved at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
print("  This probe audits the REVIEW, not EFO. The anchor is checked anyway")
print("  because every count below is a count of work done against it.")

# ---------------------------------------------------------------- B
print("\n########## B. raw/ recounted, and the classification checked ##########")
files = sorted(p.name for p in RAW.iterdir() if p.is_file())
probes = [f for f in files if f.startswith("probe_")]
outputs = [f for f in files if f.startswith("raw-")]
attacks = [f for f in files if not f.startswith(("probe_", "raw-"))]
# The classification must be exhaustive. A file matching none of the three
# prefixes would otherwise vanish from the inventory silently - the same shape
# as the module list that missed errors.py and the grep that read __pycache__.
check("every file in raw/ is classified", f"total: {len(files)}",
      f"total: {len(probes) + len(outputs) + len(attacks)}")
print(f"    {len(probes)} probe scripts, {len(outputs)} raw outputs, "
      f"{len(attacks)} provenance-attack scripts")
print(f"    the attack scripts, named rather than lumped in: {attacks}")

# THIS PROBE'S OWN OUTPUT IS EXCLUDED FROM THE TALLIES, and the exclusion is
# structural rather than convenient. `raw-inventory-selfcheck.txt` is the
# report of the run now executing: at the moment the tally is computed it still
# holds the PREVIOUS run's text, so counting it makes the probe measure its own
# stale self and no fixpoint exists. Observed directly - iterating the copy-and-
# recount loop five times never converged, because each failing run wrote
# UNEXPECTED lines that then broke the next run's tally.
# Stated here and in SYNTHESIS's inventory paragraph, so nothing is hidden.
SELF = "raw-inventory-selfcheck.txt"
counted = [f for f in outputs if f != SELF]
passing = sum(tally(RAW / f)[0] for f in counted)
unexpected = sum(tally(RAW / f)[1] for f in counted)
instrumented = [f for f in counted if tally(RAW / f)[0] > 0]
print(f"    {passing} passing checks across {len(instrumented)} instrumented "
      f"outputs; {unexpected} UNEXPECTED lines")
print(f"    (excluding {SELF}, this run's own report - see the comment above)")
flagged = {f: tally(RAW / f)[1] for f in counted if tally(RAW / f)[1]}
print(f"    the UNEXPECTED lines, by file: {flagged}")

# ---------------------------------------------------------------- C
print("\n########## C. SYNTHESIS.md's own inventory, against the files ##########")
synthesis = (REVIEWS / "SYNTHESIS.md").read_text(encoding="utf-8")
STATED = re.compile(
    r"\*\*(\d+) passing checks across (\d+) instrumented raw outputs\*\*.*?"
    r"holds (\d+) files: \*\*(\d+) probe scripts, (\d+) raw outputs, (\d+)\n"
    r"provenance-attack scripts\*\*", re.S)
match = STATED.search(synthesis)
check("SYNTHESIS states a machine-readable inventory", "found: True",
      f"found: {match is not None}")
if match:
    stated = [int(g) for g in match.groups()]
    measured = [passing, len(instrumented), len(files), len(probes),
                len(outputs), len(attacks)]
    labels = ["passing checks", "instrumented outputs", "files in raw/",
              "probe scripts", "raw outputs", "attack scripts"]
    for label, want, got in zip(labels, stated, measured):
        check(f"  {label}", f"{label}: {got}", f"{label}: {want}")

# Both sides DERIVED. This block used to pin `unexpected: 13` and to hard-code
# the word `Thirteen` into the regex that finds the sentence - so the day the
# tally changed, the check did not fail, it stopped matching. SYNTHESIS spells
# the total as a WORD and lists the files with digits; both are read out of the
# paragraph and compared against the measurement.
WORDS = {w: n for n, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
    .split())}
banner = re.search(r"(\w+) `UNEXPECTED` lines survive, in (\w+) files", synthesis)
check("SYNTHESIS states an UNEXPECTED tally", "found: True",
      f"found: {banner is not None}")
if banner:
    stated_total = WORDS.get(banner.group(1).lower(), -1)
    stated_files = WORDS.get(banner.group(2).lower(), -1)
    per_file = dict(
        (name, int(n)) for name, n in re.findall(
            r"`(raw-[a-z0-9-]+\.txt)` \((\d+)\)",
            synthesis[banner.start():banner.start() + 400]))
    check("  the number of flagged files it names", f"files: {len(flagged)}",
          f"files: {stated_files}")
    check("    the total it spells out", f"unexpected: {unexpected}",
          f"unexpected: {stated_total}")
    check("    and the per-file breakdown, file by file",
          f"per-file: {dict(sorted(flagged.items()))}",
          f"per-file: {dict(sorted(per_file.items()))}")
    check("      which is also the sum it spells",
          f"sum: {stated_total}", f"sum: {sum(per_file.values())}")

# ---------------------------------------------------------------- D
print("\n########## D. every write-up's OWN headline count ##########")
print("  Write-ups open with `N checks, M unexpected`. Nothing has ever")
print("  checked one. Each is now compared against the raw output it names.")
HEADER = re.compile(
    r"`raw/(raw-[a-z0-9-]+\.txt)`\.\s*\*\*(\d+) checks, (\d+) unexpected\.\*\*")
claims: list[tuple[str, str, int, int]] = []
for document in sorted(REVIEWS.glob("*.md")):
    text = document.read_text(encoding="utf-8")
    for found in HEADER.finditer(text):
        claims.append((document.name, found.group(1),
                       int(found.group(2)), int(found.group(3))))
# NOT a magic number. Pinning "claims: 29" would drift the moment a write-up
# is added - the exact defect this probe exists to catch, reintroduced inside
# the probe itself. Instead the strict census is checked against a LOOSE one:
# every `**N checks, M unexpected.**` anywhere must also be matched by the
# strict pattern that pairs it with a raw filename. Anything the strict pattern
# cannot see is reported, so a document that states a count without naming its
# evidence fails the run rather than silently leaving the census.
LOOSE = re.compile(r"\*\*(\d+) checks, (\d+) unexpected\.\*\*")
loose_total = sum(len(LOOSE.findall(d.read_text(encoding="utf-8")))
                  for d in sorted(REVIEWS.glob("*.md")))
check("every stated check-count is paired with a raw output",
      f"strict: {loose_total}", f"strict: {len(claims)}")
print(f"    {len(claims)} checkable headline claims across the write-ups")
print("    (An earlier draft pinned this at 30, from `grep -l` counting FILES")
print("     rather than occurrences. The census said 29 and was right. The")
print("     number is now derived on both sides, so neither can go stale.)")

# SYNTHESIS states this census TWICE, in two different phrasings, and both were
# stale (32 and 30 against a measured 35) until this check existed. Section F
# used to name them as hand-maintained; they are hand-maintained no longer.
for label, pattern in (
        ("the write-up count in its opening paragraph",
         r"headline `N checks, M unexpected` of all \*\*(\d+)\*\* write-ups"),
        ("  and the one in its own-counts row",
         r"machine-checked . inventory, (\d+) headline claims")):
    stated = re.search(pattern, synthesis)
    check(f"SYNTHESIS states {label}", f"claims: {len(claims)}",
          f"claims: {stated.group(1) if stated else 'sentence not found'}")

mismatched: list[str] = []
missing: list[str] = []
# The SAME self-reference as the tally, one level up: this note's headline
# claims "N checks, 0 unexpected" ABOUT THIS RUN, and the file it names is the
# report this run is about to write. Comparing them compares a claim against
# the PREVIOUS run, and when they disagree the mismatch is itself recorded in
# the new file - a stable failure that no amount of re-running clears. Observed:
# the loop settled at 17 ok / 1 unexpected and stayed there.
# So the one self-referential pair is skipped, and the skip is COUNTED, so a
# second one cannot appear unnoticed. This probe's own headline is therefore
# NOT machine-checked - it is the single number in this review that is not, and
# the write-up says so.
self_pairs = [c for c in claims if c[1] == SELF]
for document_name, output_name, stated_ok, stated_bad in claims:
    if output_name == SELF:
        continue
    target = RAW / output_name
    if not target.is_file():
        missing.append(f"{document_name} -> {output_name}")
        continue
    actual_ok, actual_bad = tally(target)
    if (actual_ok, actual_bad) != (stated_ok, stated_bad):
        mismatched.append(
            f"{document_name}: says {stated_ok}/{stated_bad}, "
            f"{output_name} has {actual_ok}/{actual_bad}")
check("  every named raw output exists", "missing: []", f"missing: {missing}")
for entry in mismatched:
    print(f"    !! {entry}")
check("  and every headline count matches its raw output",
      "mismatched: []", f"mismatched: {mismatched}")
check("  with exactly one self-referential claim skipped, and named",
      "skipped: 1", f"skipped: {len(self_pairs)} "
      + str([f"{d} -> {o}" for d, o, _, _ in self_pairs]))
print("  A document whose headline disagrees with its own evidence is the")
print("  exact failure this project exists to prevent, and until this probe")
print("  existed nothing would have caught one.")

# ---------------------------------------------------------------- E
print("\n########## E. SYNTHESIS's prose counts, derived from its own tables ##########")
print("  Item 34 named these as the population it did NOT cover. This is that")
print("  population, and measuring it found three stale numbers - one of them")
print("  in the very section that describes the pattern.")
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
lines = synthesis.splitlines()

# 1. "N components were probed and found sound" vs rows whose verdict is clean
clean_rows = [line for line in lines
              if line.startswith("|") and line.split("|")[2].strip().startswith("clean")]
stated_clean = next((WORDS.get(line.split()[0].lower()) for line in lines
                     if "components were probed and found sound" in line), None)
check("  components stated sound == rows whose verdict is `clean`",
      f"clean rows: {len(clean_rows)}", f"clean rows: {stated_clean}")

# 2. the class-2b instance count vs the census table in that section
try:
    start = next(i for i, line in enumerate(lines) if line.startswith("### 2b."))
    stop = next(i for i, line in enumerate(lines[start + 1:], start + 1)
                if line.startswith("### "))
except StopIteration:
    start, stop = 0, 0
census_rows = [line for line in lines[start:stop]
               if line.startswith("| #")]
stated_2b = next((WORDS.get(word.lower()) for line in lines[start:stop]
                  for word in line.split()[:1]
                  if word.lower() in WORDS), None)
check("  class 2b's stated instance count == its own table",
      f"instances: {len(census_rows)}", f"instances: {stated_2b}")

# 3. "Four classes that repeat" vs the ### headings beneath it
headings = [line for line in lines if line.startswith("### ")]
classes_heading = next((line for line in lines
                        if "classes that repeat" in line), "")
# The heading spells its number as a WORD. A first version searched for the
# DIGIT and could never match - a checker bug, not a document bug, and the
# third of that shape in this review. Resolve the word instead.
stated_classes = next((WORDS.get(word.strip("#").lower())
                       for word in classes_heading.split()
                       if word.strip("#").lower() in WORDS), None)
check("  the classes heading names the number of subsections it has",
      f"subsections: {len(headings)}", f"subsections: {stated_classes}")
print(f"    heading: {classes_heading!r}")
print("    The b-suffixed sections (2b, 3b) were sub-cases of 2 and 3 when")
print("    written, which is how the heading came to say `Four`. They have")
print("    since grown into their own classes - 2b is a seven-instance census -")
print("    so the heading now counts them.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT cover ##########")
print("  * It checks that a stated number matches the file it names. It does")
print("    NOT check that the raw output was produced by the probe beside it -")
print("    that is what the SHA-256 bindings in each write-up are for, and")
print("    they are verified by hand at commit time, not here.")
print("  * Documents that state a count WITHOUT naming a raw output in the")
print("    same sentence are not matched by the pattern. That is why section D")
print("    asserts the claim COUNT: if a document changes shape and drops out")
print("    of the census, the count falls and the run fails.")
print("  * Counts in prose that are not headline check-counts - issue numbers,")
print("    'Fifteen components', per-note tallies inside tables - are still")
print("    hand-maintained. Named as a gap rather than papered over; the")
print("    citation and quote counts are covered by the other two probes.")
print("  * MEASURED: everything above. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("This audits MY OWN write-ups, not EFO. Static file reads only; nothing")
print("was executed against a workspace. Pre-registered permissions unchanged")
print("- gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
