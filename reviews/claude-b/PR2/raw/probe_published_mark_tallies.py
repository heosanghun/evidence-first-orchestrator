#!/usr/bin/env python3
"""Every published mark tally, re-derived against the DE-DUPLICATED sets.

Queue item 73, closing what item 70 stated it had not done. That round found
the marker "sets" are concatenated tuples whose groups OVERLAP - 162 slots for
160 anchor markers, 309 for 306 divergent - and measured that de-duplicating
changes no VERDICT, because presence is presence. It then said plainly:

    It would have mattered to any tally of OCCURRENCES, and this review has
    published such tallies.

This is that pass. The published tallies are READ OUT OF THE MARKDOWN rather
than typed here - the table rows are parsed from the note that carries them -
and each is re-derived twice, once with the slotted tuple the original used
and once de-duplicated.

    ONE of the published numbers double-counted.

`raw-w4-replay.txt` was published with FIVE divergent marks. Four: the token
`transfer-orchestrator` occupies TWO slots, because I hand-added it AND the
literal derivation produces it from the divergent source. Its verdict does not
move - the file names both refs by design and is GENUINE mixed either way - so
this corrects a count, not a conclusion.

    python3 probe_published_mark_tallies.py

SCOPE, stated first: 2 marker sets, 5 doubled slots, 4 published table rows
parsed from the note, 8 numbers in them, 5 further published counts, 1 that
moves, 0 verdicts that move. A MAP that corrects a count of mine. No issue
filed, nothing about EFO claimed.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
DIVERG_SHA = "cef56234a873fefddd51f8cfedb737705a6f0d9a"
REVIEWS = Path(__file__).resolve().parent.parent
RAW = REVIEWS / "raw"
ITEM67 = REVIEWS / "NOTE-the-four-mixed-outputs-two-are-real.md"
ITEM70 = REVIEWS / ("NOTE-the-swallowing-rule-corpus-wide-"
                    "and-the-marker-set-was-short.md")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def git(*arguments: str) -> str:
    return subprocess.run(["git", "-C", str(ANCHOR), *arguments],
                          capture_output=True, text=True).stdout


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45", ANCHOR_SHA,
      git("rev-parse", "HEAD").strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain').strip()!r}")
check("  and the divergent ref this round also reads is NAMED",
      DIVERG_SHA, DIVERG_SHA)


def ever(ref: str, prefix: str) -> set:
    names = set()
    for commit in git("rev-list", ref).split():
        for path in git("ls-tree", "-r", "--name-only", commit, prefix).split():
            if path.endswith(".py"):
                names.add(path.rsplit("/", 1)[-1])
    return names


def source_corpus(ref: str) -> tuple[set, str]:
    literals: set = set()
    text: list = []
    for commit in git("rev-list", ref).split():
        for path in git("ls-tree", "-r", "--name-only", commit, "src/").split():
            if not path.endswith(".py"):
                continue
            source = git("show", f"{commit}:{path}")
            text.append(source)
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(
                        node.value, str):
                    literals.add(node.value)
    return literals, "\n".join(text)


anchor_modules = ever(ANCHOR_SHA, "src/evidence_orchestrator/")
diverg_modules = ever(DIVERG_SHA, "src/evidence_orchestrator/")
anchor_tests = ever(ANCHOR_SHA, "tests/")
diverg_tests = ever(DIVERG_SHA, "tests/")
anchor_literals, anchor_text = source_corpus(ANCHOR_SHA)
diverg_literals, diverg_text = source_corpus(DIVERG_SHA)
distinctive = (lambda v: len(v) >= 12 and any(c in v for c in " _-")
               and "\n" not in v)
# The SLOTTED tuples, exactly as item 67 built them - this probe has to
# reproduce the original instrument before it can say what it got wrong.
A_LIT = (tuple(sorted(anchor_modules - diverg_modules))
         + ("transport_independence", "audit-independence")
         + tuple(s for s in anchor_literals - diverg_literals
                 if distinctive(s) and s not in diverg_text))
D_LIT = (tuple(sorted(diverg_modules - anchor_modules))
         + ("transfer_orchestrator", "transfer-orchestrator",
            "orchestrator_transferred", "independence_dimensions")
         + tuple(s for s in diverg_literals - anchor_literals
                 if distinctive(s) and s not in anchor_text))
A_MOD = {p[:-3] for p in anchor_tests - diverg_tests}
D_MOD = {p[:-3] for p in diverg_tests - anchor_tests}
TEST_ID = re.compile(r"tests\.(test_[A-Za-z0-9_]+)\.")


def dedupe(slots: tuple) -> tuple:
    seen: dict = {}
    for marker in slots:
        seen.setdefault(marker, None)
    return tuple(seen)


A_SET, D_SET = dedupe(A_LIT), dedupe(D_LIT)
doubled = sorted({m for m in A_LIT if A_LIT.count(m) > 1}
                 | {m for m in D_LIT if D_LIT.count(m) > 1})
check("item 70's premise, re-derived: the tuples hold doubled slots",
      "slots 162/309, markers 160/306",
      f"slots {len(A_LIT)}/{len(D_LIT)}, markers {len(A_SET)}/{len(D_SET)}")
check("  and these are the five doubled tokens",
      "['audit-independence', 'independence_dimensions', 'job_runner.py', "
      "'transfer-orchestrator', 'transport_independence']", str(doubled))

# ---------------------------------------------------------------- B
print("\n########## B. the published tallies, PARSED from the note ##########")
rows = re.findall(
    r"^\| `(raw-[a-z0-9.\-]+\.txt)` \| (\d+) \| (\d+) \| \*\*([A-Za-z ]+)\*\*",
    ITEM67.read_text(encoding="utf-8"), re.MULTILINE)
for name, published_a, published_d, verdict in rows:
    print(f"    {name:<28} published anchor={published_a} "
          f"divergent={published_d}  {verdict}")
check("the mixed-outputs table publishes this many rows", "rows: 4",
      f"rows: {len(rows)}")
check("  which is 8 numbers, not 4", "numbers: 8", f"numbers: {len(rows) * 2}")
check("    and every named output still exists", "missing: []",
      "missing: " + str([n for n, _, _, _ in rows
                         if not (RAW / n).is_file()]))
print("  The rows are READ OUT OF THE DOCUMENT. If I edit the note and forget")
print("  this probe, the parse moves with it - a tally typed in here would")
print("  quietly go on agreeing with a number the note no longer states.")


def tally(name: str, markers_a, markers_d) -> tuple[int, int]:
    text = (RAW / name).read_text(encoding="utf-8", errors="replace")
    named = set(TEST_ID.findall(text))
    found_a = [t for t in markers_a if t in text] + sorted(named & A_MOD)
    found_d = [t for t in markers_d if t in text] + sorted(named & D_MOD)
    return len(found_a), len(found_d)


# ---------------------------------------------------------------- C
print("\n########## C. re-derived, slotted and de-duplicated ##########")
moved = []
for name, published_a, published_d, verdict in rows:
    slot_a, slot_d = tally(name, A_LIT, D_LIT)
    set_a, set_d = tally(name, A_SET, D_SET)
    flag = "" if (slot_a, slot_d) == (set_a, set_d) else "  <-- DOUBLE-COUNTED"
    print(f"    {name:<28} published {published_a}/{published_d} | "
          f"slots {slot_a}/{slot_d} | markers {set_a}/{set_d}{flag}")
    # The note now states the DE-DUPLICATED number, so that is what the
    # published value must equal. The slotted column records what the old
    # instrument produced, which is the thing being corrected.
    check(f"      {name} as published equals the DE-DUPLICATED tally",
          f"{published_a}/{published_d}", f"{set_a}/{set_d}")
    if (slot_a, slot_d) != (set_a, set_d):
        moved.append(name)
check("published tallies the slotted instrument DOUBLE-COUNTED", "moved: 1",
      f"moved: {len(moved)} {moved}")
check("  and it is w4-replay", "raw-w4-replay.txt", str(moved))

# ---------------------------------------------------------------- D
print("\n########## D. the one that moved, and why ##########")
w4 = (RAW / "raw-w4-replay.txt").read_text(encoding="utf-8", errors="replace")
present_d = [t for t in D_LIT if t in w4]
twice = sorted({t for t in present_d if present_d.count(t) > 1})
check("the slotted instrument gave its divergent marks as five",
      "divergent: 5", f"divergent: {tally('raw-w4-replay.txt', A_LIT, D_LIT)[1]}")
check("  de-duplicated they are four", "divergent: 4",
      f"divergent: {tally('raw-w4-replay.txt', A_SET, D_SET)[1]}")
check("    and the CORRECTED note now states four, read from the document",
      "4", next(d for n, _, d, _ in rows if n == "raw-w4-replay.txt"))
check("    because exactly one token occupies two slots", "twice: 1",
      f"twice: {len(twice)}")
check("      and it is transfer-orchestrator", "['transfer-orchestrator']",
      str(twice))
hand = "transfer-orchestrator" in ("transfer_orchestrator",
                                   "transfer-orchestrator",
                                   "orchestrator_transferred",
                                   "independence_dimensions")
derived = "transfer-orchestrator" in {s for s in diverg_literals - anchor_literals
                                      if distinctive(s)
                                      and s not in anchor_text}
check("        hand-added AND derived - which is what doubles it",
      "hand: True derived: True", f"hand: {hand} derived: {derived}")
verdict = next(v for n, _, _, v in rows if n == "raw-w4-replay.txt")
check("  the VERDICT does not move - four marks is still both lines",
      "GENUINE", verdict)
print("  So a published number was wrong and the conclusion it supported was")
print("  not. That is the whole result: the double-count was real, and it was")
print("  never load-bearing.")

# ---------------------------------------------------------------- E
print("\n########## E. the tallies that CANNOT move, and why ##########")
full_final = (RAW / "raw-full-final.txt").read_text(encoding="utf-8",
                                                    errors="replace")
occurrences = len(re.findall(re.escape("author_identity"), full_final))
check("item 67's `author_identity` occurs twice - a SINGLE marker's count",
      "occurrences: 2", f"occurrences: {occurrences}")
check("  and that token occupies one slot, so no set can double it",
      "slots: 1", f"slots: {D_LIT.count('author_identity') + A_LIT.count('author_identity')}")
census = (RAW / "raw-class2b-census.txt").read_text(encoding="utf-8",
                                                    errors="replace")
census_a = [t for t in A_LIT if t in census]
check("item 70's two anchor marks on the class-2b census reproduce",
      "anchor: 2", f"anchor: {len(census_a)}")
check("  and neither of them is a doubled token", "doubled here: []",
      "doubled here: " + str(sorted(set(census_a) & set(doubled))))
stated = re.search(r"carries exactly (\w+) anchor marks", ITEM70.read_text(
    encoding="utf-8"))
check("    which is what item 70's note states, read from the document",
      "two", stated.group(1) if stated else "NOT FOUND")
print("  A count of ONE named token's occurrences cannot be inflated by a")
print("  set that lists it twice - the inflation needs a count OVER the set.")
print("  Both surviving tallies are of that first kind, which is why the")
print("  sweep finds one mover and not five.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT retract item 67. Three of its four rows reproduce")
print("    exactly, the fourth moves by ONE, and no verdict in it changes.")
print("  * It does NOT re-open the classification. Item 70 already measured")
print("    that de-duplication changes 0 of 83 verdicts; this round is about")
print("    the COUNTS printed beside them.")
print("  * The population is the tallies this review PUBLISHED in Markdown -")
print("    parsed from the note for the table, named for the rest. A tally")
print("    that exists only inside a raw output and was never quoted in a")
print("    write-up is out of scope, and that is a stated bound, not a claim")
print("    that none exists.")
print("  * It does NOT file an issue. Nothing here is about EFO's behaviour.")
print("  * No network, no GPU, no workspace built. Two refs read and BOTH")
print("    named. The anchor's working tree is untouched, and it does not")
print("    touch `main` or another agent's branch.")
print("  * MEASURED: both marker sets as slots and as markers, the five")
print("    doubled tokens, all four published rows re-derived twice, the one")
print("    that moved and its cause, the two single-token tallies that")
print("    cannot move. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
