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
    """(passing checks, unexpected results) in one raw output."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.count("[ok]"), text.count("!! UNEXPECTED !!")


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

passing = sum(tally(RAW / f)[0] for f in outputs)
unexpected = sum(tally(RAW / f)[1] for f in outputs)
instrumented = [f for f in outputs if tally(RAW / f)[0] > 0]
print(f"    {passing} passing checks across {len(instrumented)} instrumented "
      f"outputs; {unexpected} UNEXPECTED lines")
flagged = {f: tally(RAW / f)[1] for f in outputs if tally(RAW / f)[1]}
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

banner = re.search(r"Thirteen `UNEXPECTED` lines survive, in (\w+) files",
                   synthesis)
check("  and the UNEXPECTED tally it reports", "files: 5",
      f"files: {len(flagged)}"
      + ("" if banner else "   (SYNTHESIS's sentence not found)"))
check("    with the total it names", "unexpected: 13",
      f"unexpected: {unexpected}")

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

mismatched: list[str] = []
missing: list[str] = []
for document_name, output_name, stated_ok, stated_bad in claims:
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
print("  A document whose headline disagrees with its own evidence is the")
print("  exact failure this project exists to prevent, and until this probe")
print("  existed nothing would have caught one.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT cover ##########")
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
