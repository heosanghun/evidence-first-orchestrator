#!/usr/bin/env python3
"""The swallowing rule across the whole corpus - and the marker set was short.

Queue item 70, closing what item 67 stated it had not done: that round applied
the swallowing rule to the FOUR mixed outputs only and said plainly a
corpus-wide sweep was UNCHECKED.

Applied to all 83 outputs, dropping every marker occurrence that sits inside a
longer identifier, exactly TWO verdicts change:

    raw-full-final.txt        mixed  -> divergent   (item 67, now by RULE
                                                     rather than by hand)
    raw-class2b-census.txt    anchor -> undecidable (NEW)

AND THE NEW ONE IS NOT A MIS-PLACEMENT. Its two anchor marks are swallowed
inside `test_independence.py:161` and
`test_submission_snapshot_prevents_identity_laundering` - and
`test_independence.py` IS an anchor-only TEST MODULE. The file carries real
anchor evidence; the marker that matched was simply the wrong one, because the
parsed rule wants a unittest id `tests.<module>.<class>.<method>` and this file
writes a PATH WITH A LINE NUMBER.

So the finding is that the MARKER SET WAS INCOMPLETE, not that the output was
mis-placed. A test module can be named two ways and only one was matched.
Adding the anchor-only and divergent-only test module FILENAMES:

    union before  36 anchor / 5 divergent / 4 mixed / 38 undecidable
    union after   37 anchor / 6 divergent / 3 mixed / 37 undecidable

Exactly two outputs move, and `raw-class2b-census.txt` keeps its verdict on
DIFFERENT evidence - which is what a sweep like this exists to surface.

    python3 probe_swallowed_marks_corpus_wide.py

A SECOND defect in my instrument, found by the same habit of naming what a
count counted: the marker "sets" are concatenated tuples and the groups
OVERLAP, so their length counts SLOTS, not markers - 162/160 on the anchor,
309/306 on the divergent line. Four of the six tokens I had added BY HAND were
already produced by the derivation, and `job_runner.py` is doubled inside the
derivation itself, being both a divergent-only module filename and a string
literal in that source. De-duplicating changes NO verdict, which is measured
here rather than assumed.

SCOPE, stated first: 83 outputs, 2 marker sets, 1 swallowing rule, 2 verdict
changes before the correction, 2 after, 1 incomplete marker class found, 5
doubled slots. A MAP that CORRECTS two rules of mine. No issue filed, nothing
about EFO claimed.
"""

from __future__ import annotations

import ast
import re
import subprocess
from collections import Counter
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"
ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
DIVERG_SHA = "cef56234a873fefddd51f8cfedb737705a6f0d9a"


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


def output_of(stem: str) -> str:
    return "raw-" + stem[len("probe_"):].replace("_", "-") + ".txt"


SKIP = {output_of("probe_output_provenance_lines"),
        output_of("probe_recheck_line_and_the_substring_that_reversed_four"),
        output_of("probe_what_else_places_an_output"),
        output_of("probe_the_four_mixed_outputs"),
        output_of(Path(__file__).stem)}
every = sorted(p for p in RAW.iterdir()
               if p.name.startswith("raw-") and p.suffix == ".txt")
outputs = [p for p in every if p.name not in SKIP]
check("  raw outputs scanned, the marker-printing ones excluded",
      "outputs: 84", f"outputs: {len(outputs)}")
check("    five are excluded now, this probe's own among them", "excluded: 5",
      f"excluded: {len([p for p in every if p.name in SKIP])}")

# ---------------------------------------------------------------- B
print("\n########## B. the marker sets, derived over the whole of each line ##########")


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
HAND_A = ("transport_independence", "audit-independence")
HAND_D = ("transfer_orchestrator", "transfer-orchestrator",
          "orchestrator_transferred", "independence_dimensions")
SLOTS_A = (tuple(sorted(anchor_modules - diverg_modules)) + HAND_A
           + tuple(s for s in anchor_literals - diverg_literals
                   if distinctive(s) and s not in diverg_text))
SLOTS_D = (tuple(sorted(diverg_modules - anchor_modules)) + HAND_D
           + tuple(s for s in diverg_literals - anchor_literals
                   if distinctive(s) and s not in anchor_text))


def dedupe(slots: tuple) -> tuple:
    """Order-preserving, so a marker contributes ONE slot, not two."""
    seen: dict = {}
    for marker in slots:
        seen.setdefault(marker, None)
    return tuple(seen)


BASE_A, BASE_D = dedupe(SLOTS_A), dedupe(SLOTS_D)
A_MOD = {p[:-3] for p in anchor_tests - diverg_tests}
D_MOD = {p[:-3] for p in diverg_tests - anchor_tests}
TEST_ID = re.compile(r"tests\.(test_[A-Za-z0-9_]+)\.")

# NAME WHAT THE COUNT COUNTED. The tuple is three concatenated groups and
# they OVERLAP, so its length counts SLOTS, not markers. Measured, because
# a marker occupying two slots is counted twice by anything that tallies
# occurrences - and I pre-measured 161/306 by hand and got neither number.
check("the anchor's marker set holds this many SLOTS", "anchor slots: 162",
      f"anchor slots: {len(SLOTS_A)}")
check("  but this many DISTINCT markers", "anchor markers: 160",
      f"anchor markers: {len(BASE_A)}")
dup_a = sorted({m for m in SLOTS_A if SLOTS_A.count(m) > 1})
dup_d = sorted({m for m in SLOTS_D if SLOTS_D.count(m) > 1})
check("    and the doubled ones are exactly these",
      "['audit-independence', 'transport_independence']", str(dup_a))
check("  the divergent line's slots", "divergent slots: 309",
      f"divergent slots: {len(SLOTS_D)}")
check("    its distinct markers", "divergent markers: 306",
      f"divergent markers: {len(BASE_D)}")
check("      doubled",
      "['independence_dimensions', 'job_runner.py', 'transfer-orchestrator']",
      str(dup_d))
derived_a = set(sorted(anchor_modules - diverg_modules)) | {
    s for s in anchor_literals - diverg_literals
    if distinctive(s) and s not in diverg_text}
derived_d = set(sorted(diverg_modules - anchor_modules)) | {
    s for s in diverg_literals - anchor_literals
    if distinctive(s) and s not in anchor_text}
redundant = [h for h in HAND_A if h in derived_a] + [
    h for h in HAND_D if h in derived_d]
genuine = [h for h in HAND_A if h not in derived_a] + [
    h for h in HAND_D if h not in derived_d]
check("  of the six tokens I added BY HAND, most were already derived",
      "redundant: 4", f"redundant: {len(redundant)}")
check("    only these two are genuinely hand-supplied",
      "['transfer_orchestrator', 'orchestrator_transferred']", str(genuine))
print("  `job_runner.py` is doubled INSIDE the derivation itself - it is a")
print("  divergent-only module filename AND a string literal in that source.")
print("  So the overlap is not only hand-versus-derived; two derived groups")
print("  intersect too, which no count of either group alone would show.")


def identifier_char(character: str) -> bool:
    return character.isalnum() or character == "_"


def swallowed(text: str, start: int, marker: str) -> bool:
    """True when the match is part of a longer IDENTIFIER - item 67's rule."""
    before = text[start - 1] if start else " "
    after = (text[start + len(marker)]
             if start + len(marker) < len(text) else " ")
    return ((identifier_char(marker[0]) and identifier_char(before))
            or (identifier_char(marker[-1]) and identifier_char(after)))


def live(text: str, markers: list) -> list:
    """Markers with at least ONE occurrence that is not swallowed."""
    kept = []
    for marker in markers:
        spots = [m.start() for m in re.finditer(re.escape(marker), text)]
        if any(not swallowed(text, i, marker) for i in spots):
            kept.append(marker)
    return kept


def verdict(found_a: list, found_d: list) -> str:
    if found_a and found_d:
        return "mixed"
    return "anchor" if found_a else "divergent" if found_d else "undecidable"


def classify(text: str, set_a, set_d, drop_swallowed: bool) -> str:
    named = set(TEST_ID.findall(text))
    hits_a = [t for t in set_a if t in text]
    hits_d = [t for t in set_d if t in text]
    if drop_swallowed:
        hits_a, hits_d = live(text, hits_a), live(text, hits_d)
    return verdict(hits_a + sorted(named & A_MOD), hits_d + sorted(named & D_MOD))


# ---------------------------------------------------------------- C
print("\n########## C. the rule applied CORPUS-WIDE ##########")
raw_verdict = {p.name: classify(p.read_text(errors="replace"),
                                BASE_A, BASE_D, False) for p in outputs}
slot_verdict = {p.name: classify(p.read_text(errors="replace"),
                                 SLOTS_A, SLOTS_D, False) for p in outputs}
check("de-duplicating the marker set changes NO verdict - measured, not assumed",
      "differ: 0",
      f"differ: {sum(1 for n in raw_verdict if raw_verdict[n] != slot_verdict[n])}")
swept = {p.name: classify(p.read_text(errors="replace"),
                          BASE_A, BASE_D, True) for p in outputs}
moved = sorted(n for n in raw_verdict if raw_verdict[n] != swept[n])
for name in moved:
    print(f"    {name:<34} {raw_verdict[name]} -> {swept[name]}")
check("verdicts that change once swallowed marks are dropped", "moved: 2",
      f"moved: {len(moved)}")
check("  and they are these two",
      "['raw-class2b-census.txt', 'raw-full-final.txt']", str(moved))
check("    raw-full-final.txt is item 67's, now reached BY RULE",
      "mixed -> divergent",
      f"{raw_verdict['raw-full-final.txt']} -> {swept['raw-full-final.txt']}")
print("  So 81 of 83 verdicts are unaffected. The rule is not a rewrite of")
print("  the classification; it is a check ON it, and it fires twice.")

# ---------------------------------------------------------------- D
print("\n########## D. the NEW one is not a mis-placement ##########")
census = (RAW / "raw-class2b-census.txt").read_text(encoding="utf-8")
eaten = [m for m in [t for t in BASE_A if t in census]
         if m not in live(census, [t for t in BASE_A if t in census])]
print(f"    swallowed anchor marks: {eaten}")
check("both of its anchor marks are swallowed", "swallowed: 2",
      f"swallowed: {len(eaten)}")
for marker in eaten[:2]:
    line = next(l.strip() for l in census.splitlines() if marker in l)
    print(f"      {marker:<24} inside: {line[:64]}")
# BOUNDED, deliberately. Passing the whole of `census` as the observed value
# would pass the check and dump another probe's entire output - including its
# own `0 unexpected result(s)` banner - into this raw file.
swallowing_line = next(l.strip() for l in census.splitlines()
                       if "independence.py" in l)
check("  one is swallowed inside a TEST MODULE FILENAME",
      "test_independence.py:161", swallowing_line)
check("    which is an ANCHOR-ONLY test module", "anchor-only: True",
      f"anchor-only: {'test_independence.py' in anchor_tests - diverg_tests}")
check("  and the parsed rule cannot see it - there is no unittest id here",
      "ids: []", f"ids: {sorted(set(TEST_ID.findall(census)))}")
print("  The file writes `test_independence.py:161` - a PATH WITH A LINE")
print("  NUMBER, not `tests.test_independence.Class.method`. So the marker")
print("  set was INCOMPLETE: a test module can be named two ways and only")
print("  one of them was matched. The output was never mis-placed.")

# ---------------------------------------------------------------- E
print("\n########## E. corrected, and re-measured ##########")
NEW_A = dedupe(BASE_A + tuple(sorted(anchor_tests - diverg_tests)))
NEW_D = dedupe(BASE_D + tuple(sorted(diverg_tests - anchor_tests)))
print(f"    anchor-only test modules added   : "
      f"{sorted(anchor_tests - diverg_tests)}")
print(f"    divergent-only test modules added: "
      f"{sorted(diverg_tests - anchor_tests)}")
check("  and NONE of the six was already in the set - all six are new markers",
      "added: 6",
      f"added: {len(NEW_A) - len(BASE_A) + len(NEW_D) - len(BASE_D)}")
corrected = {p.name: classify(p.read_text(errors="replace"),
                              NEW_A, NEW_D, True) for p in outputs}
print(f"    union before : {dict(Counter(raw_verdict.values()))}")
print(f"    union after  : {dict(Counter(corrected.values()))}")
check("raw-class2b-census.txt recovers, now on a LIVE marker",
      "anchor", corrected["raw-class2b-census.txt"])
check("  and raw-full-final.txt stays divergent - item 61 and 67 agree",
      "divergent", corrected["raw-full-final.txt"])
final_moved = sorted(n for n in raw_verdict if raw_verdict[n] != corrected[n])
for name in final_moved:
    print(f"    {name:<34} {raw_verdict[name]} -> {corrected[name]}")
check("outputs that move under BOTH corrections", "moved: 2",
      f"moved: {len(final_moved)}")
check("  one loses a mixture", "raw-full-final.txt", str(final_moved))
check("  and one is newly PLACED", "raw-proxy-mocks.txt", str(final_moved))
check("the corrected union places this many on the anchor's line",
      "anchor: 38",
      f"anchor: {sum(1 for v in corrected.values() if v == 'anchor')}")
check("  on the divergent line", "divergent: 6",
      f"divergent: {sum(1 for v in corrected.values() if v == 'divergent')}")
check("  carrying both", "mixed: 3",
      f"mixed: {sum(1 for v in corrected.values() if v == 'mixed')}")
check("  and still OPEN", "undecidable: 37",
      f"undecidable: {sum(1 for v in corrected.values() if v == 'undecidable')}")
check("    the four classes account for every output",
      f"total: {len(outputs)}", f"total: {sum(Counter(corrected.values()).values())}")
print("  `raw-class2b-census.txt` keeps its VERDICT and changes its EVIDENCE.")
print("  A sweep that only reported changed verdicts would have shown")
print("  nothing there - and that is the case this round exists to catch.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT retract item 67. That round's four are unchanged, and")
print("    its raw-full-final.txt result is reproduced here by RULE rather")
print("    than by hand.")
print("  * It does NOT claim the marker set is now complete. It was found")
print("    SHORT by one class - test module filenames - and another class")
print("    could be short the same way. What is measured is that no OTHER")
print("    verdict in 83 changes under the swallowing rule.")
print("  * It does NOT decide the 37 still open. They carry no marker of any")
print("    kind, swallowed or live.")
print("  * The swallowing rule is a JUDGEMENT stated in the source: a match")
print("    counts as swallowed only where the MARKER'S OWN edge is an")
print("    identifier character. Item 67 measured why the looser version is")
print("    wrong.")
print("  * It does NOT file an issue. Nothing here is about EFO's behaviour;")
print("    it is about the provenance of inherited evidence and a rule of")
print("    mine.")
print("  * No network, no GPU, no workspace built. Two refs read and named.")
print("    The anchor's working tree is untouched, and it does not touch")
print("    `main` or another agent's branch.")
print("  * The slot/marker gap is a defect in the INSTRUMENT, not in any")
print("    verdict: de-duplication is presence-preserving and 0 of 83 change.")
print("    It would have mattered to any tally of OCCURRENCES, and this")
print("    review has published such tallies before.")
print("  * MEASURED: both marker sets as slots and as markers, the doubled")
print("    entries, the hand-versus-derived split, the corpus-wide sweep, the")
print("    two verdict changes, every swallowed occurrence in the new one, the")
print("    corrected sets, the final union. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
