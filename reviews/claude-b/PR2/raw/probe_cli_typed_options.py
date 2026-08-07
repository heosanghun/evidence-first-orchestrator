#!/usr/bin/env python3
"""What "`cli.py` is clean" fed - and the eight TYPED options it never did.

Queue item 56, first of the six item 53 left. Item 47's question, asked by hand
of `NOTE-cli-surface-holds.md`: WHAT INPUT CLASS did its 25 checks feed?

    10  a well-formed CLI invocation - the controls
     5  a TAMPERED task projection (section C's audit/repair)
     4  an AUTHORIZATION violation with well-formed string arguments
     2  a STATIC census of the parser, driving nothing
     2  a value that is malformed but still a STRING (`--id UPPER`)
     2  a path that is not a workspace
    --
    25

Every argument in all of them is a STRING, because argparse hands strings. So
item 47's question - "did it feed a non-string?" - cannot even be asked of this
surface the same way. The equivalent question is: WHICH ARGUMENTS ARE TYPED?

    8 options declare `type=int` or `type=float`, derived from the parser
    0 of the 25 checks drives one

Driven here, and the un-fed class answers in three different ways:

    --lease-seconds abc         argparse SystemExit(2) - never reaches EFO
    --lease-seconds -5          ConfigurationError - the floor fires
    --lease-seconds 0           ACCEPTED, and duration_seconds becomes 1800
    --lease-seconds 999999999   ACCEPTED - that is issue #7's ceiling

THE ZERO IS THE NEW FACT. `workspace.py:876` reads

    duration = lease_seconds or int(self.config["defaults"]["lease_seconds"])

so an explicit `0` is FALSY and indistinguishable from "not supplied". The
floor at `model.py:139` never sees it, and the operator silently gets the
workspace default instead of what they asked for.

RECORDED, NOT FILED: the input is an operator's own argument, not a tampered
document, and 1800 is the default rather than a weakening - the same standard
items 38, 45, 47, 53 and 54 applied. It is also NOT issue #7, which is about
the missing ceiling; this is the floor being skipped from below.

    python3 probe_cli_typed_options.py

SCOPE, stated first: 1 note, 25 checks, 8 typed options, 13 driven inputs.
A MAP with a near miss recorded. `cli.py is clean` is NOT retracted.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import cli  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
COMMITTED = REVIEWS / "raw" / "raw-cli-surface.txt"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item56-")).resolve()


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

labels = [line.split("] ", 1)[1].strip()
          for line in COMMITTED.read_text(encoding="utf-8").splitlines()
          if line.startswith("  [ok]")]
check("  checks in the committed cli-surface output", "checks: 25",
      f"checks: {len(labels)}")
note = (REVIEWS / "NOTE-cli-surface-holds.md").read_text(encoding="utf-8")
stated = re.search(r"\*\*(\d+) checks, (\d+) unexpected", note)
check("    and the note's headline agrees with the file",
      "stated: 25 / 0", f"stated: {stated.group(1)} / {stated.group(2)}")

# ---------------------------------------------------------------- B
print("\n########## B. the twenty-five, classified BY HAND ##########")
# Hand adjudication, one label at a time against the probe source. A lookup
# table IS a filter, so exhaustiveness is asserted below.
CLASS_OF = {
    "efo init": "well-formed invocation",
    "and the ledger opens with its own events": "well-formed invocation",
    "efo agent add": "well-formed invocation",
    "efo task add": "well-formed invocation",
    "emits the task as JSON": "well-formed invocation",
    "with everything denied by default": "well-formed invocation",
    "efo status": "well-formed invocation",
    "and reading did not append": "well-formed invocation",
    "every subcommand is adjudicated": "static census",
    "and the map has no stale entries": "static census",
    "audit-projections notices the edit": "tampered projection",
    "and names it": "tampered projection",
    "repair-projections succeeds": "tampered projection",
    "it rewrote the projection": "tampered projection",
    "and appended NOTHING to the ledger": "tampered projection",
    "a worker claiming to be the orchestrator": "authorization violation",
    "is refused by the same check as the API": "authorization violation",
    "the orchestrator claiming a worker's task": "authorization violation",
    "an invalid agent id from the command line": "malformed string value",
    "same validator as the API": "malformed string value",
    "a --path that is not a workspace": "path that is not a workspace",
    "refuses rather than creating one": "path that is not a workspace",
    "it accepts a path outside the workspace": "authorization violation",
    "and fails on the CONTENT, not on ownership": "well-formed invocation",
    "having appended nothing": "well-formed invocation",
}
unclassified = [label for label in labels if label not in CLASS_OF]
check("every one of the twenty-five is classified - the table is exhaustive",
      "unclassified: []", f"unclassified: {unclassified}")
tally: dict[str, int] = {}
for label in labels:
    tally[CLASS_OF[label]] = tally.get(CLASS_OF[label], 0) + 1
for kind, count in sorted(tally.items(), key=lambda kv: -kv[1]):
    print(f"    {count:>3}  {kind}")
check("  and the classes sum to the whole population",
      f"sum: {len(labels)}", f"sum: {sum(tally.values())}")
print("  EVERY argument in all twenty-five is a STRING, because argparse")
print("  hands strings. Item 47's question cannot be asked of this surface in")
print("  the same words; the equivalent is WHICH ARGUMENTS ARE TYPED.")

# ---------------------------------------------------------------- C
print("\n########## C. the class the twenty-five never fed: TYPED options ##########")


def typed_options(parser: argparse.ArgumentParser, prefix: str = "") -> list:
    found = []
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                found.extend(typed_options(sub, f"{prefix}{name} "))
        elif action.type in (int, float):
            found.append((prefix.strip(), action.option_strings[0],
                          action.type.__name__))
    return found


typed = sorted(set(typed_options(cli.build_parser())))
for command, option, kind in typed:
    print(f"    {command:<14}{option:<24}{kind}")
check("options the parser declares as int or float", "typed: 8",
      f"typed: {len(typed)}")
check("  all of them numeric - no other coercion is declared",
      "kinds: ['float', 'int']", f"kinds: {sorted({k for _, _, k in typed})}")
print("  Not one of the twenty-five checks drives one of these eight.")

# ---------------------------------------------------------------- D
print("\n########## D. DRIVEN - the un-fed class, three different answers ##########")


def run(*argv: str) -> tuple[object, str]:
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(argv))
    except SystemExit as exc:
        return "argparse", f"SystemExit({exc.code})"
    except Exception as exc:  # noqa: BLE001 - an ESCAPE would be the finding
        return "escaped", f"{type(exc).__name__}: {exc}"
    return code, (out.getvalue() or err.getvalue())


workspace = str(ROOT / "ws")
outcomes: dict[str, str] = {}
durations: dict[str, object] = {}
try:
    run("init", workspace, "--name", "item56",
        "--preset", "antigravity-codex-claude")
    for index, value in enumerate(("600", "abc", "-5", "0", "999999999")):
        task_id = f"T{index}"
        run("task", "add", workspace, "--actor", "antigravity", "--id", task_id,
            "--title", "t", "--description", "d", "--owner", "claude")
        code, text = run("task", "claim", workspace, "--actor", "claude",
                         "--id", task_id, "--lease-seconds", value)
        if code == "argparse":
            outcomes[value] = f"argparse {text}"
        elif code == 0:
            durations[value] = json.loads(text)["task"]["lease"][
                "duration_seconds"]
            outcomes[value] = f"ACCEPTED, duration_seconds={durations[value]}"
        else:
            outcomes[value] = text.strip().replace("error: ", "")[:56]
    # Every typed option is also driven at PARSE level, where no workspace
    # state can mask the coercion - the domain drives above needed a fresh
    # pending task each time, and a first version reused one, which made all
    # three lease values return the same state error. The control said so.
    parse_failures = 0
    for command, option, _ in typed:
        argv = command.split() + [workspace, option, "not-a-number"]
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                cli.build_parser().parse_args(argv)
        except SystemExit:
            parse_failures += 1
    default_lease = json.loads(
        (Path(workspace) / ".efo" / "workspace.json").read_text(
            encoding="utf-8"))["defaults"]["lease_seconds"]
finally:
    shutil.rmtree(ROOT, ignore_errors=True)

for value, outcome in outcomes.items():
    print(f"    --lease-seconds {value:<12}{outcome}")
check("the control is accepted at the value asked for",
      "ACCEPTED, duration_seconds=600", outcomes["600"])
check("  a non-numeric value never reaches EFO - argparse rejects it",
      "argparse SystemExit(2)", outcomes["abc"])
check("    and all EIGHT typed options reject one at parse time",
      "rejected: 8", f"rejected: {parse_failures}")
check("  a NEGATIVE value reaches the domain and the floor fires",
      "Lease duration must be at least 10 seconds", outcomes["-5"])
check("    which is a ConfigurationError, model.py:139",
      "at least 10 seconds",
      (ANCHOR / "src" / "evidence_orchestrator" / "model.py"
       ).read_text(encoding="utf-8").splitlines()[138])

# ---------------------------------------------------------------- E
print("\n########## E. the zero, which is the new fact ##########")
print(f"    --lease-seconds 0        {outcomes['0']}")
print(f"    workspace default        lease_seconds={default_lease}")
source = (ANCHOR / "src" / "evidence_orchestrator" / "workspace.py"
          ).read_text(encoding="utf-8").splitlines()
print(f"    workspace.py:876         {source[875].strip()}")
check("zero is ACCEPTED where -5 is refused", "ACCEPTED", outcomes["0"])
check("  and the duration becomes the workspace DEFAULT, not zero",
      f"duration: {default_lease}", f"duration: {durations.get('0')}")
check("    because the line uses `or`, and 0 is falsy",
      "lease_seconds or int(", source[875])
print("  An explicit `0` is indistinguishable from `not supplied`. The floor")
print("  at model.py:139 never sees it, and the operator silently gets 1800")
print("  instead of what they asked for.")
print("  RECORDED, NOT FILED. The input is the operator's own argument, not a")
print("  tampered document, and 1800 is the default rather than a weakening -")
print("  items 38, 45, 47, 53 and 54 applied the same standard.")
check("  and the huge value is ACCEPTED - but that is issue #7, already filed",
      "ACCEPTED", outcomes["999999999"])
print("  #7 is the missing CEILING. This is the FLOOR being skipped from")
print("  below, which is a different line and a different mechanism.")

print("\n########## F. what this does NOT do ##########")
print("  * It does not retract `cli.py is clean`. All 25 checks still pass.")
print("  * It does not file an issue, and nothing was accepted that weakens")
print("    a gate - 1800 is the workspace's own default.")
print("  * It drives ONE of the eight typed options to the domain. The other")
print("    seven are driven only at PARSE level, because five of them start a")
print("    worker loop or a server. That is stated, not implied.")
print("  * It does not adjudicate the other five notes item 53 named. FIVE")
print("    remain after this one.")
print("  * No network. The workspace is a tempfile directory, removed above.")
print("  * MEASURED: the 25-label classification and its exhaustiveness, the")
print("    eight typed options derived from the parser, all five domain")
print("    drives, all eight parse drives, the resulting durations, the two")
print("    source lines. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("One clean note re-examined by hand and its un-fed input class driven.")
print("Anchor untouched, no `main` write, no issue filed, no verdict")
print("retracted. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
