#!/usr/bin/env python3
"""21 clean verdicts, and the cheap way to census them is PROVABLY WRONG.

Queue item 50. Item 47 narrowed `util.py is clean` by asking what input class
its 46 checks fed. The item asked the same question of every clean verdict, and
said to SCOPE FIRST and, if the population is too large, take the subset whose
component carries an open issue.

    21  clean rows in SYNTHESIS
    24  distinct notes they cite  (four rows cite two apiece)
    22  whose probe file can be located
     4  of those are STATIC CENSUSES - they never execute the component, so
        "which input class did it feed" is not a question about them
    18  actually drive the component

Adjudicating 18 notes by hand is more than one round. So this tried the cheap
proxy: does the probe file contain a call passing None, an int, an empty list
or an empty dict?

THE PROXY IS WRONG, AND THERE IS A KNOWN ANSWER THAT PROVES IT.
`probe_util_and_lock.py` scores 5 by that measure - and item 47 MEASURED, by
reading its 46 checks one at a time, that not one of them feeds a non-string to
a util function. The `None`s it counts are `re.search(..., None)` and default
arguments: the probe's OWN plumbing, not input to the component under test.

So the answer to item 50 is that the cheap census cannot answer it, and saying
so is better than shipping 18 verdicts derived from a filter I can show to be
wrong on the one case I have already checked by hand. The subset with an open
issue is named for the next round instead.

A LEAD, not a verdict. No issue filed, no clean verdict retracted.

    python3 probe_clean_verdict_census.py

SCOPE, stated first: 21 clean rows, 22 locatable probes, 1 known answer.
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


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {subprocess.run(['git', '-C', str(ANCHOR), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()!r}")

rows = [line for line in (REVIEWS / "SYNTHESIS.md").read_text(
    encoding="utf-8").splitlines()
    if line.startswith("| ") and "clean" in line.split("|")[2]]
probes: dict[str, str] = {}
notes: set[str] = set()
for row in rows:
    component = row.split("|")[1].strip()
    for name in re.findall(r"`((?:NOTE|ADDENDUM)-[A-Za-z0-9._-]+\.md)`", row):
        if not (REVIEWS / name).is_file():
            continue
        notes.add(name)
        found = re.search(r"`raw/(probe_[a-z0-9_]+\.py)`",
                          (REVIEWS / name).read_text(encoding="utf-8"))
        if found and (RAW / found.group(1)).is_file():
            probes[found.group(1)] = component
check("clean rows in SYNTHESIS", "clean rows: 21", f"clean rows: {len(rows)}")
check("  distinct notes they cite", "notes: 27", f"notes: {len(notes)}")
check("    whose probe can be located", "probes: 25", f"probes: {len(probes)}")
print("  Twenty-two is more than one round of hand adjudication, which is what")
print("  the item anticipated. Section B tries the cheap way; section C shows")
print("  the cheap way does not work.")

# THIS note goes into SYNTHESIS too, and its own row must not join the census -
# a census that counted itself would be the self-reference defect all over
# again. It does not, because its verdict is a LEAD and not `clean`. That is a
# fact about the row, so ASSERT it rather than rely on it.
SELF_NOTE = "NOTE-the-cheap-way-to-census-my-clean-verdicts-is-refuted.md"
self_rows = [line for line in (REVIEWS / "SYNTHESIS.md").read_text(
    encoding="utf-8").splitlines()
    if line.startswith("| ") and SELF_NOTE in line]
check("  this note has exactly one row in SYNTHESIS",
      "own rows: 1", f"own rows: {len(self_rows)}")
check("    and it is NOT counted as clean - its verdict is a lead",
      "self counted as clean: False",
      f"self counted as clean: {any(SELF_NOTE in r for r in rows)}")

# ---------------------------------------------------------------- B
print("\n########## B. the cheap proxy, built and measured ##########")


def executes(tree: ast.AST, source: str) -> str:
    """A REAL import node, not a mention in a comment or a docstring.

    A first version regex-matched `import evidence_orchestrator` anywhere and
    classified every probe as executing - including four pure AST censuses
    that only QUOTE that line. Parsed instead.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
                alias.name.startswith("evidence_orchestrator")
                for alias in node.names):
            return "imports"
        if (isinstance(node, ast.ImportFrom)
                and (node.module or "").startswith("evidence_orchestrator")):
            return "imports"
    if re.search(r'"-m",\s*"evidence_orchestrator"', source):
        return "subprocess"
    if re.search(r'"node"|/opt/node22/bin/node', source):
        return "node"
    return ""


def nonstring_arguments(tree: ast.AST) -> int:
    total = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for argument in list(node.args) + [k.value for k in node.keywords]:
            if isinstance(argument, ast.Constant) and (
                    argument.value is None
                    or (isinstance(argument.value, (int, float))
                        and not isinstance(argument.value, bool))):
                total += 1
            elif (isinstance(argument, (ast.List, ast.Dict))
                  and not (getattr(argument, "elts", None)
                           or getattr(argument, "keys", None))):
                total += 1
    return total


static, driving = [], {}
for probe, component in sorted(probes.items()):
    source = (RAW / probe).read_text(encoding="utf-8")
    tree = ast.parse(source)
    if executes(tree, source):
        driving[probe] = (component, nonstring_arguments(tree))
    else:
        static.append((probe, component))
for probe, component in static:
    print(f"    STATIC   {probe:<42}{component[:30]}")
for probe, (component, count) in sorted(driving.items()):
    print(f"    drives   {probe:<42}{component[:22]:<24}{count} non-string args")
check("probes that never execute the component - a static census",
      "static: 4", f"static: {len(static)}")
check("  probes that drive it", "driving: 21", f"driving: {len(driving)}")
check("    of which the proxy says feed a non-string", "flagged: 21",
      f"flagged: {sum(1 for _, n in driving.values() if n)}")
print("  For a static census the question does not arise: it reads the AST and")
print("  never calls anything, so it has no input class to feed.")

# ---------------------------------------------------------------- C
print("\n########## C. the KNOWN ANSWER that refutes the proxy ##########")
util_probe = ast.parse((RAW / "probe_util_and_lock.py").read_text(
    encoding="utf-8"))
proxy_says = nonstring_arguments(util_probe)
check("the proxy's score for probe_util_and_lock.py",
      f"proxy: {driving['probe_util_and_lock.py'][1]}", f"proxy: {proxy_says}")
item47 = (REVIEWS / "NOTE-what-util-is-clean-rested-on-and-the-input-it-never-fed.md"
          ).read_text(encoding="utf-8")
# The note's own HEADING is the expectation, quoted from the file rather than
# retyped from the probe's docstring - a first version used the docstring's
# wording and failed on capitalisation.
check("  but item 47 MEASURED, check by check, that it feeds none",
      "Not one of the 46 checks fed a non-string",
      item47.replace("\n", " ").replace("#", "").replace("  ", " "))
print("  The None values the proxy counts are `re.search(..., None)` and")
print("  default arguments - the probe's OWN plumbing, not input handed to a")
print("  util function. One hand-checked case is enough to refute a filter,")
print("  and this is the case I had already hand-checked.")
check("  so the proxy is wrong on at least one of the 15", "refuted: True",
      f"refuted: {proxy_says > 0}")
print("  CHECKING A FILTER AGAINST GROUND TRUTH IN BOTH DIRECTIONS is the")
print("  rule; here ground truth existed because item 47 did the work by hand.")
print("  Shipping 15 verdicts from a filter refuted on its one checkable case")
print("  would be exactly the failure this review exists to prevent.")

# ---------------------------------------------------------------- D
print("\n########## D. so: the subset with an open issue, named not measured ##########")
ISSUES = {
    "`provenance.py` byte-exactness": "#4/#5/#18 (done - item 53)",
    "`monitor/collector.py` (redaction)": "#6 (done - item 59)",
    "`ledger.projected_tasks`": "#9 (done - item 62)",
    "`cli.py`": "#19 (done - item 56)",
    "`dashboard.py`, `errors.py`": "#19 (done - item 68)",
    "`workspace.py` implicit exceptions": "#19",
    "`proxy_submit` + grant": "#7 (done - item 65)",
    "`util.py`, `lock.py`": "(done - item 47)",
}
named = [(p, c, ISSUES[c]) for p, (c, _) in sorted(driving.items())
         if c in ISSUES]
for probe, component, issues in named:
    print(f"    {component[:34]:<36}{issues:<18}{probe}")
# NINE, not eight: `util.py`, `lock.py` is one component with TWO probes, so
# it appears twice in this listing. Corrected to the measurement; the remainder
# is still seven because both of its entries are already adjudicated.
check("driving probes whose component carries an open issue",
      "with an issue: 15", f"with an issue: {len(named)}")
check("  of which already adjudicated by hand - items 47, 53, 56, 59, 62",
      "already done: 14",
      f"already done: {sum(1 for _, _, i in named if 'done' in i)}")
check("    leaving the population for the next round",
      "remaining: 1",
      f"remaining: {len(named) - sum(1 for _, _, i in named if 'done' in i)}")
print("  ONE remains. That is the population the next round should take, one")
print("  at a time and BY HAND, which is the only method shown to work here.")
print("  Updated 2026-08-03: items 53, 56, 59 and 62 adjudicated `provenance.py`")
print("  byte-exactness, `cli.py`, the collector and `projected_tasks`, moving")
print("  7 -> 3, and the")
print("  clean-row set grew by the note that did it. Both are re-derived here")
print("  rather than left at the number this note first published.")

# ---------------------------------------------------------------- E
print("\n########## E. what this does NOT do ##########")
print("  * It does not retract ANY clean verdict. Nothing here measures a")
print("    component; it measures which of my probes could be censused")
print("    cheaply, and the answer is none of them.")
print("  * It does not claim the 15 fed only well-formed input, nor that they")
print("    did not. That is the question, and it is left open with the")
print("    population named.")
print("  * It does not file an issue.")
print("  * It did NOT execute any component - static reads of my own probe")
print("    sources and SYNTHESIS only.")
print("  * MEASURED: every count, the static/driving split, the proxy's score")
print("    for the known-answer case. REASONED: nothing - the refutation is")
print("    item 47's hand measurement, already published.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Static AST reads of my own probes. No component executed, no workspace,")
print("no issue filed. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
