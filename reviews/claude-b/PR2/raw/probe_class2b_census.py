#!/usr/bin/env python3
"""For each issue that DOES have a test, what input does the test feed?

Queue item 36. Three instances of one pattern were already recorded - #13's
Korean-only gate, #13's asserted grounding placement, #14's `password`. This
turns the observation into a census.

`NOTE-what-the-test-suite-cannot-catch.md` measured that 10 of the 16 issues
have a defect token appearing in NO test source, so those cannot be asserted by
name. The population left is the SIX that do: #3, #8, #10, #11, #13, #19. #13
and #19 are already adjudicated. This reads the other four.

The result is uniform and, by this point, unsurprising: not one of the four has
a test that could fail on the defect. Two are token matches that turn out to be
about something else entirely - a lead, not a verdict, which is why the earlier
note said presence must be READ.

    python3 probe_class2b_census.py
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

FAIL = 0
SOURCE = Path("/tmp/efo-prov")
TESTS = SOURCE / "tests"


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


SOURCES = {p.name: p.read_text(encoding="utf-8")
           for p in sorted(TESTS.glob("*.py"))}


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
head = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(SOURCE), "status", "--porcelain"],
                       capture_output=True, text=True).stdout.strip()
check("probe source is main 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", head)
check("  with no working-tree modification", "dirty: ''", f"dirty: {dirty!r}")
check("  and no compiled bytecode is read as a source",
      "pycache: False",
      f"pycache: {any('__pycache__' in n for n in SOURCES)}")

# ---------------------------------------------------------------- B
print("\n########## B. #3 - re-attestation IS tested, three times ##########")
print("  #3 is: re-attest the VERIFIER to a different control principal, then")
print("  replay a byte-identical verification, and it is accepted.")
attested: list[tuple[str, int, str, str]] = []
for name, text in SOURCES.items():
    tree = ast.parse(text)
    roles: dict[str, str] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_agent"):
            keywords = {k.arg: ast.unparse(k.value) for k in node.keywords}
            if "agent_id" in keywords:
                roles[keywords["agent_id"].strip("'\"")] = keywords.get(
                    "role", "?").strip("'\"")
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "attest_agent_identity"):
            keywords = {k.arg: ast.unparse(k.value) for k in node.keywords}
            agent = keywords.get("agent_id", "?").strip("'\"")
            attested.append((name, node.lineno, agent,
                             roles.get(agent, "declared elsewhere")))
for name, line, agent, role in attested:
    print(f"    {name}:{line}  attests {agent!r}   role: {role}")
check("  re-attestation call sites in the suite", "sites: 3",
      f"sites: {len(attested)}")
verifiers = [a for a in attested if a[3] == "verifier"]
check("  of which re-attest an agent whose declared role is VERIFIER",
      "verifiers: 0", f"verifiers: {len(verifiers)}")
print("  The two guarded shapes ARE tested and both refuse:")
print("    test_attested_alias_lineage_cannot_be_removed - re-attesting an")
print("      agent that carries an alias lineage")
print("    test_submission_snapshot_prevents_identity_laundering - re-attesting")
print("      the WORKER after submit; the snapshot preserves authorship")
print("  Neither is #3's shape. #3 re-attests the VERIFIER, before verifying,")
print("  on an agent with no alias lineage - the one combination the suite")
print("  never builds. Both existing tests pass with #3 present.")

# ---------------------------------------------------------------- C
print("\n########## C. #8 - the two paths are tested, and never crossed ##########")
print("  #8 is: a known-answer check whose expected AND observed are both")
print("  `[FILL]` satisfies require_known_answer_check.")
known_answer_values: list[str] = []
for name, text in SOURCES.items():
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Dict)):
            continue
        keys = [k.value for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
        if "expected" in keys and "observed" in keys:
            rendered = {k.value: ast.unparse(v) for k, v in
                        zip(node.keys, node.values)
                        if isinstance(k, ast.Constant)}
            known_answer_values.append(
                f"{name}:{node.lineno} expected={rendered.get('expected')} "
                f"observed={rendered.get('observed')}")
for entry in known_answer_values:
    print(f"    {entry}")
check("  known-answer fixtures visible as DICT LITERALS", "fixtures: 1",
      f"fixtures: {len(known_answer_values)}")
# There is a SECOND fixture, and a dict-literal census cannot see it:
# test_adapter.py writes a worker program with textwrap.dedent, and that
# program's `known_answer_checks` is source code inside a STRING. Same family
# of blind spot as the rename-across-a-return bound - the census sees syntax,
# not values. Checked by text instead, and said rather than glossed.
embedded = [name for name, text in SOURCES.items()
            if "known_answer_checks" in text
            and f"{name}:" not in " ".join(known_answer_values)]
print(f"    plus a fixture inside a generated worker script: {embedded}")
adapter = SOURCES["test_adapter.py"]
# Quote the fixture, not the file: a check whose `observed` is a whole module
# makes the raw output unreadable and hides what was actually compared.
window = [line.strip() for line in adapter.splitlines()
          if '"expected"' in line or '"observed"' in line]
check("  the embedded one compares two real values, not [FILL]",
      '"expected": "known-output",', " | ".join(window))
check("  and no known-answer expected/observed anywhere is [FILL]",
      "fill in a known answer: False",
      "fill in a known answer: "
      + str(any("FILL" in entry for entry in known_answer_values)
            or '"expected": "[FILL]"' in adapter))
fill_test = [name for name, text in SOURCES.items()
             if "exact value" in text and "FILL" in text]
print(f"    the one test that asserts on [FILL] is in {fill_test}")
print("    test_unmeasured_claim_requires_fill sets a CLAIM's value to 0.7 and")
print("    asserts validation REFUSES it - the opposite direction, on the")
print("    claims path. The suite tests known-answer checks with real values")
print("    (4 vs 4, and 4 vs 5 for the failing case) and tests `[FILL]` on")
print("    claims, and never crosses the two. #8 lives exactly in the cross.")

# ---------------------------------------------------------------- D
print("\n########## D. #10 and #11 - token matches that are about something else ##########")
patched_lines: list[int] = []
for node in ast.walk(ast.parse(SOURCES["test_proxy_status.py"])):
    if (isinstance(node, ast.Call)
            and (getattr(node.func, "id", "") == "patch"
                 or getattr(node.func, "attr", "") == "patch")
            and node.args and isinstance(node.args[0], ast.Constant)
            and "archive_evidence_bundle" in str(node.args[0].value)):
        patched_lines.append(node.lineno)
mentions = sum(text.count("archive_evidence_bundle")
               for text in SOURCES.values())
check("#10: mentions of archive_evidence_bundle in the suite", "mentions: 1",
      f"mentions: {mentions}")
check("  and that mention is a patch() target, i.e. the function is MOCKED OUT",
      "patched at: [260]", f"patched at: {patched_lines}")
print("  #10 is `archived evidence is never re-verified`. The suite's only")
print("  reference to the archiver REPLACES it with a stub returning")
print("  {'retained': 0, 'external': 0}. There is no test of the archiver.")

collector = ast.parse(SOURCES["test_monitor_collector.py"])
imports = [ast.unparse(n) for n in ast.walk(collector)
           if isinstance(n, (ast.Import, ast.ImportFrom))]
check("#11: does the file mentioning events.jsonl import the adapter?",
      "adapter imported: False",
      "adapter imported: " + str(any("adapter" in i for i in imports)))
print("  #11 is `the command adapter grants the child write access to")
print("  ledger/events.jsonl`. The two mentions of that filename are in")
print("  test_monitor_collector.py, building a ledger path for the COLLECTOR.")
print("  Unrelated to the adapter grant. A token match, and a lead that does")
print("  not survive reading - which is why the earlier note called presence a")
print("  lead and absence decisive.")

# ---------------------------------------------------------------- E
print("\n########## E. the census ##########")
CENSUS = {
    "#3":  "test exists, feeds a shape the guard already refuses",
    "#8":  "both paths tested, never crossed",
    "#10": "the function is MOCKED OUT in its only appearance",
    "#11": "token match, unrelated file",
    "#13": "Korean-only input; and the second finding is ASSERTED by the test",
    "#14": "feeds `password`, a key the set contains",
    "#19": "the one repair test asserts state, not the dropped key",
}
for issue, verdict in CENSUS.items():
    print(f"    {issue:<5} {verdict}")
check("issues examined for the pattern", "examined: 7",
      f"examined: {len(CENSUS)}")
print("  Of the 16 issues this review filed, 10 have no test that names them")
print("  and 6 do - plus #14, whose test lives in web_tests. Every one of the")
print("  seven examined has a test that CANNOT fail on the defect, for one of")
print("  four reasons: it feeds a covered input, it asserts the behaviour the")
print("  issue objects to, it mocks the component out, or the match was")
print("  spurious.")
print("  That is a statement about COVERAGE SHAPE, not about test quality.")
print("  Every one of these tests asserts something true.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does not run the suite. CI does that; the counts this review")
print("    quotes are CI's, bound to job ids.")
print("  * `#3 has no verifier re-attestation` is measured from the AST by")
print("    matching add_agent(role=...) to attest_agent_identity(agent_id=...)")
print("    IN THE SAME FILE. Two of the three attested agents are declared in")
print("    a shared fixture, so their role is reported as `declared elsewhere`")
print("    rather than guessed - and neither is a verifier, which was checked")
print("    by reading those two tests.")
print("  * The known-answer census matches DICT LITERALS carrying both")
print("    `expected` and `observed`, and it found ONE. The second fixture is")
print("    source code inside a textwrap.dedent string and is invisible to it;")
print("    that one is checked by text. A census over syntax cannot see a")
print("    fixture that is a program, which is the same family of blind spot")
print("    as the rename-across-a-return bound.")
print("  * MEASURED: every count and call site above. REASONED: that a test")
print("    which exercises only a guarded shape cannot fail on an unguarded")
print("    one - which for #3 rests on reading the two tests, and is stated")
print("    as such.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static analysis of the test sources only; nothing was executed. No")
print("issue filed - a suite that does not test a defect is not itself a")
print("defect, and all seven issues are already open. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
