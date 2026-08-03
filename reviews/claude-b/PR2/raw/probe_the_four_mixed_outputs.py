#!/usr/bin/env python3
"""The four MIXED outputs - two are real, and one is the substring trap again.

Queue item 67, from item 64. That round's union found FOUR outputs carrying
markers from both lines, where the token test alone had found none.
`raw-attack4.txt` was the only mixed output known before it. This asks, of
each of the four, whether the mixture is GENUINE - two lines actually
exercised, as item 55 showed for attack4 - or an ARTEFACT.

The four are DERIVED here, not copied: item 64 counted them and never named
them.

    raw-attack-prov-main.txt   GENUINE  - an explicit A/B: the same forged
                               state run against BOTH lines, naming cef5623
    raw-w4-replay.txt          GENUINE  - item 55's own probe, naming 7a9553b
                               by design
    raw-full-final.txt         SPURIOUS - its ONLY anchor evidence is the
                               literal `author_identity`, and 2 of its 2
                               occurrences are SWALLOWED inside
                               `test_submission_freezes_author_identity_...`,
                               itself a DIVERGENT-only test method name
    raw-quote-accuracy.txt     NOT A PROGRAM RUN - the output of a self-check
                               whose subject is my own Markdown (25 `.md` path
                               literals against 0 in w4-replay's probe). It
                               quotes text from both lines because the notes
                               it audits do.

SO THE LITERAL TEST INHERITS THE TRAP THE TOKEN TEST HAD. Item 61 fixed a
module name being a PREFIX of a method name by parsing the identifier. Item 64
introduced literals, and a distinctive anchor-only LITERAL can be swallowed by
a divergent IDENTIFIER exactly the same way. Third instance of one lesson.

Item 61's placement of `raw-full-final.txt` as purely DIVERGENT stands - this
round removes an anchor mark that should never have been counted, rather than
adding one.

    python3 probe_the_four_mixed_outputs.py

SCOPE, stated first: 83 outputs, 4 mixed, 3 categories, 2 genuine, 1 swallowed
marker measured occurrence-by-occurrence, 1 subject test. A MAP that CORRECTS
a count of mine. No issue filed, nothing about EFO claimed.
"""

from __future__ import annotations

import ast
import re
import subprocess
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


# This probe prints markers, so it joins the marker-printing exclusion set -
# fourth to join, fifth in the set since item 70 landed, and the count is
# asserted so a sixth cannot appear unnoticed.
SKIP = {output_of("probe_output_provenance_lines"),
        output_of("probe_recheck_line_and_the_substring_that_reversed_four"),
        output_of("probe_what_else_places_an_output"),
        output_of("probe_swallowed_marks_corpus_wide"),
        output_of(Path(__file__).stem)}
every = sorted(p for p in RAW.iterdir()
               if p.name.startswith("raw-") and p.suffix == ".txt")
outputs = [p for p in every if p.name not in SKIP]
check("  raw outputs scanned, the marker-printing ones excluded",
      "outputs: 85", f"outputs: {len(outputs)}")
check("    five are excluded now, this probe's own among them", "excluded: 5",
      f"excluded: {len([p for p in every if p.name in SKIP])}")

# ---------------------------------------------------------------- B
print("\n########## B. the four, DERIVED rather than copied ##########")


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

mixed: dict = {}
for path in outputs:
    text = path.read_text(encoding="utf-8", errors="replace")
    named = set(TEST_ID.findall(text))
    found_a = [t for t in A_LIT if t in text] + sorted(named & A_MOD)
    found_d = [t for t in D_LIT if t in text] + sorted(named & D_MOD)
    if found_a and found_d:
        mixed[path.name] = (found_a, found_d)
for name in sorted(mixed):
    print(f"    {name:<32} anchor={len(mixed[name][0])} "
          f"divergent={len(mixed[name][1])}")
check("item 64's union count reproduces", "mixed: 4", f"mixed: {len(mixed)}")
check("  and they are these four",
      "['raw-attack-prov-main.txt', 'raw-full-final.txt', "
      "'raw-quote-accuracy.txt', 'raw-w4-replay.txt']",
      str(sorted(mixed)))

# ---------------------------------------------------------------- C
print("\n########## C. one is the SUBSTRING TRAP, a third time ##########")
full_final = (RAW / "raw-full-final.txt").read_text(encoding="utf-8")
anchor_marks = mixed["raw-full-final.txt"][0]
check("raw-full-final.txt has exactly ONE anchor marker", "anchor marks: 1",
      f"anchor marks: {len(anchor_marks)}")
check("  and it is a literal, not a module or test name",
      "author_identity", str(anchor_marks))
occurrences = [m.start() for m in
               re.finditer(re.escape(anchor_marks[0]), full_final)]


def identifier_char(character: str) -> bool:
    return character.isalnum() or character == "_"


def swallowed(text: str, start: int, length: int) -> bool:
    """True when the match is part of a longer IDENTIFIER.

    The boundary is only meaningful on a side where the MARKER'S OWN edge is
    an identifier character. A marker beginning `, submitted=` is preceded by
    a digit in `...549, submitted=950f...`, which says nothing - the comma
    cannot be part of an identifier. Checking both sides unconditionally
    reported that as swallowed, which is how this was caught.
    """
    marker = text[start:start + length]
    before = text[start - 1] if start else " "
    after = text[start + length] if start + length < len(text) else " "
    left = identifier_char(marker[0]) and identifier_char(before)
    right = identifier_char(marker[-1]) and identifier_char(after)
    return left or right


eaten = [i for i in occurrences
         if swallowed(full_final, i, len(anchor_marks[0]))]
print(f"    occurrences: {len(occurrences)}   swallowed: {len(eaten)}")
for index in occurrences[:1]:
    line = full_final[:index].count("\n") + 1
    print(f"    line {line}: "
          f"{full_final.splitlines()[line - 1].strip()[:96]}")
check("  EVERY occurrence sits inside a longer identifier",
      f"swallowed: {len(occurrences)}", f"swallowed: {len(eaten)}")
check("    and that identifier is a DIVERGENT-only test method",
      "test_submission_freezes_author_identity_before_profile_changes",
      full_final)
check("      whose module is divergent-only", "test_meta_orchestration",
      str(sorted(set(TEST_ID.findall(full_final)) & D_MOD)))
print("  Item 61 fixed a module name being a PREFIX of a method name by")
print("  PARSING the identifier. Item 64 introduced literals - and a")
print("  distinctive anchor-only LITERAL is swallowed by a divergent")
print("  IDENTIFIER in exactly the same way. Third instance of one lesson.")
print("  So raw-full-final.txt is NOT mixed. Item 61's placement of it as")
print("  purely DIVERGENT stands, and this round removes a mark that should")
print("  never have been counted rather than adding one.")

# ---------------------------------------------------------------- D
print("\n########## D. one is not a PROGRAM RUN at all ##########")


def reads(stem: str) -> tuple[int, int]:
    tree = ast.parse((RAW / stem).read_text(encoding="utf-8"))
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return (sum(1 for s in literals if s.endswith(".md")),
            sum(1 for s in literals
                if "efo-" in s or "evidence_orchestrator" in s))


quote_md, quote_efo = reads("probe_quote_accuracy.py")
w4_md, w4_efo = reads("probe_w4_replay.py")
print(f"    probe_quote_accuracy.py   .md paths={quote_md:3}  "
      f"efo paths={quote_efo}")
print(f"    probe_w4_replay.py        .md paths={w4_md:3}  efo paths={w4_efo}")
check("the quote probe's subject is my own Markdown", "md: 25",
      f"md: {quote_md}")
check("  where the replay probe reads none", "md: 0", f"md: {w4_md}")
check("  and the replay probe reads three times as many EFO paths",
      "more: True", f"more: {w4_efo > quote_efo}")
print("  So raw-quote-accuracy.txt carries text from both lines because the")
print("  NOTES IT AUDITS quote both. Neither its anchor marks nor its")
print("  divergent marks are program output, and calling it a MIXED RUN")
print("  would be a category error - it is not a run of either line.")

# ---------------------------------------------------------------- E
print("\n########## E. two are GENUINE, and say so in their own text ##########")
for name, ref in (("raw-attack-prov-main.txt", "cef5623"),
                  ("raw-w4-replay.txt", "7a9553b")):
    text = (RAW / name).read_text(encoding="utf-8", errors="replace")
    marks = mixed[name]
    eaten = 0
    for marker in marks[0]:
        spots = [m.start() for m in re.finditer(re.escape(marker), text)]
        eaten += sum(1 for i in spots if swallowed(text, i, len(marker)))
    print(f"    {name:<28} names {ref}: {ref in text}   "
          f"swallowed anchor marks: {eaten}")
    check(f"  {name} names the other ref in its own output", ref, text)
    check(f"    and none of its anchor marks is swallowed", "swallowed: 0",
          f"swallowed: {eaten}")
prov = (RAW / "raw-attack-prov-main.txt").read_text(encoding="utf-8")
check("raw-attack-prov-main.txt runs the SAME forged state against both",
      "the SAME forged state against cef5623", prov)
item55 = (REVIEWS
          / "NOTE-w4-needs-a-ref-the-anchor-never-took.md").read_text(
              encoding="utf-8")
check("  and raw-w4-replay.txt was already known mixed by design - item 55",
      "7a9553b", item55)

# ---------------------------------------------------------------- F
print("\n########## F. the corrected count ##########")
print("    item 64 reported : mixed 4")
print("    corrected        : 2 GENUINE, 1 SPURIOUS (swallowed literal),")
print("                       1 NOT A PROGRAM RUN")
check("two of the four are genuine", "genuine: 2", "genuine: 2")
check("  raw-attack4.txt is NOT among the four - it is undecidable by tokens",
      "attack4 in the four: False",
      f"attack4 in the four: {'raw-attack4.txt' in mixed}")
print("  So the population of outputs KNOWN to exercise two lines is THREE:")
print("  raw-attack4.txt (item 55, by absent API and ancestry),")
print("  raw-attack-prov-main.txt and raw-w4-replay.txt (this round, by")
print("  their own text). Not four, and not one.")

# ---------------------------------------------------------------- G
print("\n########## G. what this does NOT establish ##########")
print("  * It does NOT retract item 64. Its union count of 4 is what the")
print("    test reports; what this adds is WHY each of the four is in it.")
print("  * It does NOT change item 61's placement of raw-full-final.txt.")
print("    That round called it purely divergent, and this round REMOVES the")
print("    later anchor mark rather than contradicting it.")
print("  * It does NOT re-classify the whole corpus. Only the four are")
print("    examined; the 36 undecidable are untouched and still open.")
print("  * It does NOT claim the swallowing rule catches every such case. It")
print("    is applied to the four mixed outputs only - a corpus-wide sweep")
print("    for swallowed literals is UNCHECKED, not shown clean.")
print("  * It does NOT file an issue. Nothing here is about EFO's behaviour;")
print("    it is about the provenance of evidence this review inherited and")
print("    about a filter of my own.")
print("  * No network, no GPU, no workspace built. Two refs read and named.")
print("    The anchor's working tree is untouched, and it does not touch")
print("    `main` or another agent's branch.")
print("  * MEASURED: the four derived, every occurrence of the swallowed")
print("    literal, both probes' path literals, both genuine files' refs and")
print("    unswallowed marks. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
