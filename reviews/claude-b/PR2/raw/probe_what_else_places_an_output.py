#!/usr/bin/env python3
"""What ELSE can place an output - and the filter bug the ground truth caught.

Queue item 64, from item 61. That round left 47 of 79 outputs undecidable and
noted only 7 print a suite size. This asks what OTHER content class could
place them.

Rather than guessing classes one at a time - a ledger action set, an error
message, a CLI option - all of them are subsumed by ONE derivation: the
STRING LITERALS each line's source contains, taken over the WHOLE of each
line and differenced. An action name, an error wording and a JSON key are all
literals.

AND THE GROUND TRUTH CAUGHT A FILTER BUG BEFORE THE RESULT SHIPPED. The raw
literal difference CONTRADICTED item 61's placements on 5 of the 20 outputs
already decided. The cause is measured, not guessed: `proxy_submit` is a
literal on the divergent line and an IDENTIFIER on the anchor's, so a census
of LITERALS sees it as divergent-only. ABSENCE AS A LITERAL IS NOT ABSENCE
FROM THE CODE. Corrected by subtracting any literal that appears anywhere in
the other line's source TEXT - after which:

    contradictions   5 -> 0
    agreements       19 of 19 decidable-by-both

Applied to the 47, the corrected class places 12 and leaves 35. That is the
publishable result: the corpus is mostly unplaceable, and now by a test whose
false-positive rate against known answers is measured at zero rather than
assumed.

    python3 probe_what_else_places_an_output.py

SCOPE, stated first: 79 outputs, 47 undecidable, 3 candidate classes measured
for coverage, 2 literal sets derived over full ancestry, 1 filter bug caught
by ground truth, 12 newly placed, 35 left open. A MAP. No issue filed,
nothing retracted.
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

# This probe PRINTS marker literals, so its own output would classify itself.
# Excluded structurally along with the two earlier provenance probes' outputs,
# and the exclusions are COUNTED - item 58's treatment, now three deep.
def output_of(stem: str) -> str:
    return "raw-" + stem[len("probe_"):].replace("_", "-") + ".txt"


SELF = output_of(Path(__file__).stem)
SKIP = {output_of("probe_output_provenance_lines"),
        output_of("probe_recheck_line_and_the_substring_that_reversed_four"),
        SELF}
every = sorted(p for p in RAW.iterdir()
               if p.name.startswith("raw-") and p.suffix == ".txt")
outputs = [p for p in every if p.name not in SKIP]
check("  raw outputs scanned, the marker-printing ones excluded",
      "outputs: 79", f"outputs: {len(outputs)}")
check("    exactly three are excluded, and the third is this probe's own",
      "excluded: 3",
      f"excluded: {len([p for p in every if p.name in SKIP])}")

# ---------------------------------------------------------------- B
print("\n########## B. the classification item 61 left ##########")


def ever(ref: str, prefix: str) -> set:
    names = set()
    for commit in git("rev-list", ref).split():
        for path in git("ls-tree", "-r", "--name-only", commit,
                        prefix).split():
            if path.endswith(".py"):
                names.add(path.rsplit("/", 1)[-1])
    return names


anchor_modules = ever(ANCHOR_SHA, "src/evidence_orchestrator/")
diverg_modules = ever(DIVERG_SHA, "src/evidence_orchestrator/")
anchor_tests = ever(ANCHOR_SHA, "tests/")
diverg_tests = ever(DIVERG_SHA, "tests/")
A_TOK = tuple(sorted(anchor_modules - diverg_modules)) + (
    "transport_independence", "audit-independence")
D_TOK = tuple(sorted(diverg_modules - anchor_modules)) + (
    "transfer_orchestrator", "transfer-orchestrator",
    "orchestrator_transferred", "independence_dimensions")
A_MOD = {p[:-3] for p in anchor_tests - diverg_tests}
D_MOD = {p[:-3] for p in diverg_tests - anchor_tests}
TEST_ID = re.compile(r"tests\.(test_[A-Za-z0-9_]+)\.")


def by_token(text: str) -> tuple[list, list]:
    named = set(TEST_ID.findall(text))
    return ([t for t in A_TOK if t in text] + sorted(named & A_MOD),
            [t for t in D_TOK if t in text] + sorted(named & D_MOD))


def verdict(found_a, found_d) -> str:
    if found_a and found_d:
        return "mixed"
    return "anchor" if found_a else "divergent" if found_d else "undecidable"


token = {p.name: verdict(*by_token(p.read_text(errors="replace")))
         for p in outputs}
print(f"    {Counter(token.values())}")
check("the module/test-id test leaves this many undecidable",
      "undecidable: 47",
      f"undecidable: {sum(1 for v in token.values() if v == 'undecidable')}")

# ---------------------------------------------------------------- C
print("\n########## C. the two classes already measured, re-measured on the 47 ##########")
open_set = [p for p in outputs if token[p.name] == "undecidable"]
suite = [p.name for p in open_set
         if re.search(r"Ran \d+ tests", p.read_text(errors="replace"))]
usage = [p.name for p in open_set
         if "usage: efo" in p.read_text(errors="replace")]
print(f"    print a suite size   : {len(suite)} of {len(open_set)}  {suite}")
print(f"    print a CLI usage line: {len(usage)} of {len(open_set)}  {usage}")
# I predicted 2 and 0. Corrected to the measurement: five and one.
check("a suite size covers five of the open set", "suite: 5",
      f"suite: {len(suite)}")
check("  and a usage line exactly one", "usage: 1", f"usage: {len(usage)}")
check("    six of 47 between them, with no overlap", "covered: 6",
      f"covered: {len(set(suite) | set(usage))}")
print("  So neither named class carries a round on its own - 6 of 47 between")
print("  them. Both are SUBSUMED by the derivation below: an action name, an")
print("  error wording and a CLI option are all STRING LITERALS.")

# ---------------------------------------------------------------- D
print("\n########## D. the literal difference, derived over the WHOLE of each line ##########")


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


anchor_literals, anchor_text = source_corpus(ANCHOR_SHA)
diverg_literals, diverg_text = source_corpus(DIVERG_SHA)


def distinctive(value: str) -> bool:
    """A literal specific enough to be evidence.

    The rule is stated rather than tuned: at least 12 characters, containing
    a space, underscore or hyphen, and single-line. A bare English word would
    match any prose and is exactly what item 61's bare `"independence"` was.
    """
    return (len(value) >= 12 and any(c in value for c in " _-")
            and "\n" not in value)


raw_anchor = {s for s in anchor_literals - diverg_literals if distinctive(s)}
raw_diverg = {s for s in diverg_literals - anchor_literals if distinctive(s)}
print(f"    literals on the anchor's line : {len(anchor_literals)}")
print(f"    literals on the divergent line: {len(diverg_literals)}")
print(f"    distinctive, anchor-only      : {len(raw_anchor)}")
print(f"    distinctive, divergent-only   : {len(raw_diverg)}")
check("both difference sets are non-trivial", "anchor-only: 159",
      f"anchor-only: {len(raw_anchor)}")
check("  and the divergent line has more of them", "divergent-only: 309",
      f"divergent-only: {len(raw_diverg)}")

# ---------------------------------------------------------------- E
print("\n########## E. THE GROUND TRUTH CAUGHT IT - 5 contradictions ##########")


def classify(text: str, set_a: set, set_d: set) -> str:
    return verdict([s for s in set_a if s in text],
                   [s for s in set_d if s in text])


def contradictions(set_a: set, set_d: set) -> list:
    out = []
    for path in outputs:
        was = token[path.name]
        if was not in ("anchor", "divergent"):
            continue
        now = classify(path.read_text(errors="replace"), set_a, set_d)
        if now in ("anchor", "divergent") and now != was:
            out.append((path.name, was, now))
    return out


before = contradictions(raw_anchor, raw_diverg)
for name, was, now in before:
    print(f"    {name:<34} item 61: {was:<10} raw literals: {now}")
check("the RAW literal difference contradicts known placements",
      "contradictions: 5", f"contradictions: {len(before)}")
offender = sorted({s for s in raw_diverg
                   if s in (RAW / "raw-module-exercise.txt").read_text(
                       errors="replace")})
check("  and the culprit in four of the five is one literal",
      "culprit: ['proxy_submit']", f"culprit: {offender}")
check("    which exists on the ANCHOR's line as source text",
      "on anchor as text: True",
      f"on anchor as text: {'proxy_submit' in anchor_text}")
check("      but NOT as a string literal there",
      "as a literal on anchor: False",
      f"as a literal on anchor: {'proxy_submit' in anchor_literals}")
print("  ABSENCE AS A LITERAL IS NOT ABSENCE FROM THE CODE. On the anchor's")
print("  line `proxy_submit` is an IDENTIFIER - a method name - so a census")
print("  of literals cannot see it and calls it divergent-only.")

# ---------------------------------------------------------------- F
print("\n########## F. corrected, and re-checked in BOTH directions ##########")
DA = {s for s in raw_anchor if s not in diverg_text}
DD = {s for s in raw_diverg if s not in anchor_text}
print(f"    anchor-only    {len(raw_anchor)} -> {len(DA)}")
print(f"    divergent-only {len(raw_diverg)} -> {len(DD)}")
after = contradictions(DA, DD)
check("no contradiction survives the correction", "contradictions: 0",
      f"contradictions: {len(after)}")
agree = sum(1 for p in outputs
            if token[p.name] in ("anchor", "divergent")
            and classify(p.read_text(errors="replace"), DA, DD)
            == token[p.name])
check("  and it AGREES with this many known placements", "agreements: 19",
      f"agreements: {agree}")
check("    the two offenders are gone from the divergent set",
      "removed: True",
      f"removed: {'proxy_submit' not in DD and ' must be a JSON array' not in DD}")
print("  A filter checked in only one direction is what item 50 refuted. The")
print("  ground truth here is item 61's own placements, and the raw filter")
print("  FAILED it - which is why this round has a correction section rather")
print("  than a result section.")

# ---------------------------------------------------------------- G
print("\n########## G. what the corrected class places ##########")
placed = Counter(classify(p.read_text(errors="replace"), DA, DD)
                 for p in open_set)
print(f"    the {len(open_set)} previously undecidable: {dict(placed)}")
check("outputs newly placed on the anchor's line", "anchor: 9",
      f"anchor: {placed['anchor']}")
check("  newly placed on the divergent line", "divergent: 2",
      f"divergent: {placed['divergent']}")
check("  carrying literals from BOTH", "mixed: 1", f"mixed: {placed['mixed']}")
check("  and STILL undecidable", "undecidable: 35",
      f"undecidable: {placed['undecidable']}")

union = {}
for path in outputs:
    text = path.read_text(errors="replace")
    found_a, found_d = by_token(text)
    found_a = found_a + [s for s in DA if s in text]
    found_d = found_d + [s for s in DD if s in text]
    union[path.name] = verdict(found_a, found_d)
print(f"    UNION of both tests: {dict(Counter(union.values()))}")
# I predicted 36/7 by adding the parts. That is wrong arithmetic: an output
# already placed by one test can pick up the OTHER line's marker from the
# second, becoming MIXED rather than staying put. Corrected to the measured
# union, and the mixed class is asserted rather than absorbed.
check("the union places this many on the anchor's line", "anchor: 35",
      f"anchor: {sum(1 for v in union.values() if v == 'anchor')}")
check("  on the divergent line", "divergent: 5",
      f"divergent: {sum(1 for v in union.values() if v == 'divergent')}")
check("  and this many carry markers from BOTH - none by the token test alone",
      "mixed: 4", f"mixed: {sum(1 for v in union.values() if v == 'mixed')}")
check("  and leaves this many OPEN", "undecidable: 35",
      f"undecidable: {sum(1 for v in union.values() if v == 'undecidable')}")
check("    the classes account for every output", f"total: {len(outputs)}",
      f"total: {sum(Counter(union.values()).values())}")

# ---------------------------------------------------------------- H
print("\n########## H. what this does NOT establish ##########")
print("  * The headline is a NEGATIVE: 35 of 79 outputs carry no marker of")
print("    any class measured here. The corpus is mostly unplaceable, and")
print("    that is the answer to item 64 rather than a shortfall in it.")
print("  * It does NOT claim the 35 are on the anchor's line. `undecidable`")
print("    means undecidable - item 61 proved the test one-way, and")
print("    raw-attack4.txt is still in this set while being KNOWN mixed.")
print("  * It does NOT claim literals are the only remaining class. Output")
print("    formatting, timestamps and file layout were NOT examined.")
print("  * The `distinctive` rule (>=12 chars, contains a space/underscore/")
print("    hyphen, single line) is a JUDGEMENT stated in the source, not a")
print("    derived threshold. A different rule would place a different")
print("    number; what is measured is that THIS rule contradicts zero known")
print("    answers.")
print("  * It does NOT retract item 61 or any placement. It ADDS to them, and")
print("    the union is reported beside the parts.")
print("  * It does NOT file an issue. Nothing here is a defect in EFO - it is")
print("    a fact about the provenance of evidence this review inherited.")
print("  * No network, no GPU, no workspace built. Two refs read and named.")
print("    The anchor's working tree is untouched, and it does not touch")
print("    `main` or another agent's branch.")
print("  * MEASURED: both literal corpora over full ancestry, the three")
print("    candidate classes' coverage, the five contradictions and their")
print("    cause, the corrected sets, the agreement count, the 47, the union.")
print("    REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
