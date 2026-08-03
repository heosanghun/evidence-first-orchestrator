#!/usr/bin/env python3
"""What the dashboard checks fed - and the allow_remote class they never did.

Queue item 68, from items 50/53. `NOTE-dashboard-and-errors-hold.md` drove the
bind guard with fourteen host spellings and found it a STRICT ALLOW-LIST. This
asks the item-47 question of it: WHAT INPUT CLASS did those 28 checks feed?

`dashboard.serve` has three typed keyword parameters:

    host: str = "127.0.0.1"    port: int = 8765    allow_remote: bool = False

Classified from the published probe's OWN source: `host` takes fourteen
strings, `port` is ALWAYS `0`, and `allow_remote` is passed only through a
helper annotated `allow_remote: bool = False` - so only real booleans reach it.
The un-fed class is a NON-BOOL `allow_remote`. And the guard, quoted from the
file, is a TRUTHINESS test:

    if host not in {"127.0.0.1", "::1", "localhost"} and not allow_remote:

So `allow_remote="no"` is truthy and BYPASSES the refusal. Driven: of ten
non-bool values, FIVE bypass the documented guard - including the three
strings that a reader would take to MEAN false, `"no"`, `"false"` and `"0"`.

REACHABILITY IS MEASURED, NOT ASSUMED. `cli.build_parser()` is called and the
`--allow-remote` action inspected: it is `store_true`, so the CLI hands
`serve()` a real bool and cannot reach this. The exposure is the LIBRARY API -
the same class as issue #15, where an annotation is not a check.

No socket is bound anywhere in this probe: `serve()` is pointed at a path that
is not a workspace, so `Workspace(root)` raises immediately AFTER the guard.
Which error comes back is therefore the measurement of whether the guard
fired - the same discipline the published note used.

    python3 probe_dashboard_allow_remote_class.py

SCOPE, stated first: 28 published checks classified, 3 typed parameters, 1
un-fed class, 10 driven values, 3 controls, 1 reachability measurement. A
NARROWED SCOPE on a clean verdict - not retracted, nothing filed.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import cli, dashboard  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SOURCE = ANCHOR / "src" / "evidence_orchestrator"
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"
# A path that is deliberately NOT a workspace. serve() reaches Workspace(root)
# only if the bind guard let it through, so the error identifies the branch.
NOT_A_WORKSPACE = Path("/tmp/efo-item68-not-a-workspace")


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
                          capture_output=True, text=True).stdout.strip()


def verdict(host: str, allow_remote: Any) -> str:
    """What happened BEFORE any socket was created."""
    try:
        dashboard.serve(NOT_A_WORKSPACE, host=host, port=0,
                        allow_remote=allow_remote)
        return "BOUND - which must not happen here"
    except Exception as exc:  # noqa: BLE001 - the message IS the measurement
        message = str(exc)
        if "Remote dashboard binding requires" in message:
            return "REFUSED by the bind guard"
        if "Not an Evidence First Orchestrator workspace" in message:
            return "PAST THE GUARD - stopped at the workspace load"
        return f"{type(exc).__name__}: {message[:48]}"


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROLS, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", git("rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain')!r}")
check("  and the path used below is NOT a workspace", "exists: False",
      f"exists: {NOT_A_WORKSPACE.exists()}")

print(f"    127.0.0.1 / False : {verdict('127.0.0.1', False)}")
print(f"    0.0.0.0   / False : {verdict('0.0.0.0', False)}")
print(f"    0.0.0.0   / True  : {verdict('0.0.0.0', True)}")
check("a loopback host passes the guard - CONTROL", "PAST THE GUARD",
      verdict("127.0.0.1", False))
check("  a remote host without the flag is REFUSED - CONTROL",
      "REFUSED by the bind guard", verdict("0.0.0.0", False))
check("  and a remote host WITH the flag passes - CONTROL", "PAST THE GUARD",
      verdict("0.0.0.0", True))
print("  So the two outcomes are distinguishable without binding a socket,")
print("  which is what makes the drive below readable.")

# ---------------------------------------------------------------- B
print("\n########## B. what the PUBLISHED checks fed, classified by AST ##########")
published = (RAW / "probe_dashboard_and_errors.py").read_text(encoding="utf-8")
tree = ast.parse(published)
fed: dict = {}
for node in ast.walk(tree):
    if isinstance(node, ast.keyword) and node.arg in ("host", "port",
                                                      "allow_remote"):
        try:
            fed.setdefault(node.arg, []).append(
                type(ast.literal_eval(node.value)).__name__)
        except (ValueError, TypeError):
            fed.setdefault(node.arg, []).append("non-literal")
for argument in sorted(fed):
    print(f"    {argument:14} {dict(Counter(fed[argument]))}")
check("`port` is fed as a literal, and always the same one", "int",
      str(fed.get("port")))
# `host` and `allow_remote` arrive through a helper, so the AST sees a
# variable. The helper's ANNOTATION is what bounds them - read it directly.
helper = [node for node in ast.walk(tree)
          if isinstance(node, ast.FunctionDef) and node.name == "bind_verdict"]
check("  host and allow_remote arrive through one helper", "helpers: 1",
      f"helpers: {len(helper)}")
annotated = {a.arg: ast.unparse(a.annotation) if a.annotation else None
             for a in helper[0].args.args}
print(f"    bind_verdict signature: {annotated}")
check("    whose allow_remote parameter is annotated `bool`", "bool",
      str(annotated.get("allow_remote")))
note = (REVIEWS / "NOTE-dashboard-and-errors-hold.md").read_text(
    encoding="utf-8")
check("  the note claims 28 checks, which is what is being narrowed",
      "**28 checks, 0 unexpected.**", note)
print("  So `host` was driven hard - fourteen spellings - and `allow_remote`")
print("  was never driven at all beyond the two booleans. That is the un-fed")
print("  class.")

# ---------------------------------------------------------------- C
print("\n########## C. the guard is a TRUTHINESS test, quoted from the file ##########")
lines = SOURCE.joinpath("dashboard.py").read_text(
    encoding="utf-8").splitlines()
guard = [n for n, line in enumerate(lines, start=1)
         if "allow_remote" in line and line.strip().startswith("if ")]
print(f"    dashboard.py:{guard[0]}  {lines[guard[0] - 1].strip()}")
check("the guard tests `not allow_remote`, not its type",
      "and not allow_remote:", lines[guard[0] - 1])
check("  the host side IS an exact set membership", 'host not in {"127.0.0.1"',
      lines[guard[0] - 1])
print("  Strict on the host, loose on the flag - in one expression.")

# ---------------------------------------------------------------- D
print("\n########## D. the un-fed class, DRIVEN ##########")
results = []
for value in ("no", "false", "0", 1, ["x"], 0, "", [], None, 0.0):
    outcome = verdict("0.0.0.0", value)
    results.append((value, outcome))
    print(f"    allow_remote={value!r:8} -> {outcome}")
bypass = [v for v, o in results if "PAST THE GUARD" in o]
refused = [v for v, o in results if "REFUSED" in o]
check("non-bool values that BYPASS the documented guard", "bypass: 5",
      f"bypass: {len(bypass)}")
check("  and they are the truthy ones", "['no', 'false', '0', 1, ['x']]",
      str(bypass))
check("  the falsy ones are refused", "refused: 5", f"refused: {len(refused)}")
check("    and the two classes account for every driven value",
      "total: 10", f"total: {len(bypass) + len(refused)}")
print("  The three sharpest are the STRINGS a reader would take to mean")
print("  false: 'no', 'false' and '0' each turn the refusal off.")

# ---------------------------------------------------------------- E
print("\n########## E. is it REACHABLE? the CLI is asked, not assumed ##########")
parser = cli.build_parser()
actions = [a for a in parser._actions if "--allow-remote" in (a.option_strings
                                                              or [])]
# argparse nests subcommands: only a subparsers action has `choices`, and
# on other actions it is None rather than absent - `getattr(..., {})` returns
# that None and `.values()` raises. Guarded rather than assumed.
subparser_actions: list = []
for action in parser._actions:
    choices = getattr(action, "choices", None)
    if not isinstance(choices, dict):
        continue
    for sub in choices.values():
        for candidate in getattr(sub, "_actions", []):
            if "--allow-remote" in (candidate.option_strings or []):
                subparser_actions.append(candidate)
found = actions + subparser_actions
check("`--allow-remote` is declared exactly once in the parser", "found: 1",
      f"found: {len(found)}")
print(f"    action class: {type(found[0]).__name__}   "
      f"nargs={found[0].nargs}   const={found[0].const!r}")
check("  and it is a store_true action", "_StoreTrueAction",
      type(found[0]).__name__)
check("    so the CLI can only hand serve() a real bool", "const: True",
      f"const: {found[0].const}")
print("  So this is NOT reachable from the CLI. The exposure is the LIBRARY")
print("  API, and it is the same class as issue #15 - an annotation is not a")
print("  check. Recorded here rather than appended there.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT retract `NOTE-dashboard-and-errors-hold.md`. Its 28")
print("    checks stand, and the host guard IS the strict allow-list it")
print("    reported. What is added is that the same expression is LOOSE on")
print("    the flag beside it.")
print("  * It does NOT file an issue. The CLI cannot reach it, and the class")
print("    - an annotation that is not enforced - is #15's, already open.")
print("  * It does NOT drive `port`. The published probe feeds it as 0 every")
print("    time, and any port validation lives in the socket layer AFTER the")
print("    workspace load, which this probe deliberately never reaches. So")
print("    `port` is UNCHECKED here, not shown safe.")
print("  * It does NOT bind a socket or serve a request. Every verdict is")
print("    read from which exception comes back, and the three controls in")
print("    section A are what make that reading sound.")
print("  * It does NOT claim a caller would pass `allow_remote='no'`. What is")
print("    measured is that the guard would not stop them.")
print("  * No network, no GPU, no workspace built. The anchor's working tree")
print("    is untouched, and it does not touch `main` or another agent's")
print("    branch.")
print("  * MEASURED: the AST classification, the helper's annotation, the")
print("    guard line quoted from the file, all ten driven values, the three")
print("    controls, the parser action. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
