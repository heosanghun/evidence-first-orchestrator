#!/usr/bin/env python3
"""What the proxy-grant checks fed - and the duration class they never did.

Queue item 65, from items 50/53. `NOTE-proxy-grant-holds.md` drove every
authorization gate and none of them moved the verdict. This asks the item-47
question of it: WHAT INPUT CLASS did those 27 checks actually feed?

Classified from the published probe's OWN source by AST: `duration_seconds` is
fed exactly twice, as `300` and `10` - both ints, both at or above the floor.
The un-fed class is therefore a duration OUTSIDE that range: zero, negative,
enormous, or not an int at all.

AND MY FIRST HYPOTHESIS WAS WRONG, WHICH IS WHY IT IS RECORDED. Reading

    duration = duration_seconds or int(self.config["defaults"]["lease_seconds"])

at workspace.py:735-737 with no validation call beside it, I expected the
10-second floor to be MISSING on this path - an asymmetry with the lease path.
It is not. The floor lives INSIDE `lease_expiry` (model.py:138-139), which
BOTH paths call. Asking what the guard actually covers, before concluding it
does not cover this path, is the rule; here it does cover it.

What the drive does find is narrower and real:

    duration_seconds=0   -> falsy, silently becomes the 1800s default
    duration_seconds=10**9 -> accepted; expiry in the year 33-ish. No ceiling.
    duration_seconds=10.5  -> a FLOAT is accepted and shortens nothing
    duration_seconds="300" -> raw TypeError, not an EFOError

The falsy-zero is a SECOND instance of the shape item 56 measured at
workspace.py:876 for `--lease-seconds`, in a different method. The missing
ceiling is issue #7's claim on a SECOND surface.

    python3 probe_proxy_grant_duration_class.py

SCOPE, stated first: 27 published checks classified, 1 un-fed class, 1 wrong
hypothesis recorded, 7 durations driven, 2 known answers, 1 open issue
quantified. A NARROWED SCOPE on a clean verdict - not retracted, nothing
filed.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
SOURCE = ANCHOR / "src" / "evidence_orchestrator"
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
RAW = REVIEWS / "raw"
ROOT = Path(tempfile.mkdtemp(prefix="efo-item65-"))


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


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", git("rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain')!r}")

INDEX = [0]


def workspace(tag: str) -> Workspace:
    """A fresh workspace per drive, keyed by INDEX.

    Items 57 and 60 both collided when two drives derived a directory name
    from the tamper's first word; a grant is also one-per-task, so a shared
    workspace would make the second drive fail on state rather than input.
    """
    INDEX[0] += 1
    ws = Workspace.initialize(ROOT / f"{INDEX[0]:02d}-{tag[:8]}", name="i65",
                              orchestrator="antigravity",
                              preset="antigravity-codex-claude")
    for agent in ("antigravity", "claude"):
        ws.attest_agent_identity(actor="antigravity", agent_id=agent,
                                 control_principal="p-" + agent,
                                 model_family="f-" + agent)
    ws.create_task(actor="antigravity", task_id="C1", title="t",
                   description="d", owner="claude")
    return ws


def authorize(ws: Workspace, duration: Any) -> dict:
    arguments: dict[str, Any] = {
        "actor": "antigravity", "task_id": "C1",
        "transport_actor": "antigravity",
        "remote_url": "https://example.com/x.git",
        "branch": "delivery", "commit": "a" * 40,
    }
    if duration is not ...:
        arguments["duration_seconds"] = duration
    ws.authorize_proxy_submission(**arguments)
    return ws.get_task("C1")["proxy_grant"]


control = authorize(workspace("control"), 300)
check("an honest grant is issued - the CONTROL", "consumed_at: None",
      f"consumed_at: {control['consumed_at']}")
check("  and it carries an expiry", "expires: True",
      f"expires: {bool(control['expires_at'])}")

# ---------------------------------------------------------------- B
print("\n########## B. what the PUBLISHED checks fed, classified by AST ##########")
published = (RAW / "probe_proxy_grant.py").read_text(encoding="utf-8")
tree = ast.parse(published)
# The option is supplied in TWO syntactic forms - as a keyword argument and
# as a dict entry in the probe's own default-kwargs mapping. A scan of
# ast.keyword alone sees one of them and reports "fed: 1", which is how this
# was caught: parse BOTH forms, or the population is undercounted.
fed: list = []
for node in ast.walk(tree):
    values = []
    if isinstance(node, ast.keyword) and node.arg == "duration_seconds":
        values = [node.value]
    elif isinstance(node, ast.Dict):
        values = [v for k, v in zip(node.keys, node.values)
                  if isinstance(k, ast.Constant) and k.value == "duration_seconds"]
    for value in values:
        try:
            fed.append(ast.literal_eval(value))
        except (ValueError, TypeError):
            fed.append("non-literal")
print(f"    duration_seconds values fed: {sorted(fed)}")
check("the published probe feeds duration_seconds exactly twice", "fed: 2",
      f"fed: {len(fed)}")
check("  both are ints", "kinds: ['int']",
      f"kinds: {sorted({type(v).__name__ for v in fed})}")
check("  and both are at or above the 10-second floor", "below floor: 0",
      f"below floor: {sum(1 for v in fed if isinstance(v, int) and v < 10)}")
note = (REVIEWS / "NOTE-proxy-grant-holds.md").read_text(encoding="utf-8")
check("  the note claims 27 checks, which is what is being narrowed",
      "**27 checks, 0 unexpected.**", note)
print("  So the un-fed class is a duration OUTSIDE [10, 300]: zero, negative,")
print("  enormous, or not an int at all.")

# ---------------------------------------------------------------- C
print("\n########## C. a hypothesis of mine, and why it is WRONG ##########")
lines = SOURCE.joinpath("workspace.py").read_text(
    encoding="utf-8").splitlines()
print(f"    workspace.py:735  {lines[734].strip()}")
print(f"    workspace.py:736  {lines[735].strip()}")
check("the grant derives its duration with the same falsy-or shape",
      "duration_seconds or int(", lines[734].strip())
model = SOURCE.joinpath("model.py").read_text(encoding="utf-8").splitlines()
print(f"    model.py:138      {model[137].strip()}")
print(f"    model.py:139      {model[138].strip()}")
check("  and the 10-second floor lives inside lease_expiry, not the caller",
      "Lease duration must be at least 10 seconds", model[138])
calls = [n for n, line in enumerate(lines, start=1)
         if "lease_expiry(duration" in line]
print(f"    lease_expiry(duration, now) is called at lines: {calls}")
check("  which the GRANT path calls - line 771, inside the grant it builds",
      "771", str(calls))
check("    and the LEASE path calls too - line 889, so there is NO asymmetry",
      "889", str(calls))
check("      both call sites are the same expression", "sites: 2",
      f"sites: {len(calls)}")
print("  I expected the floor to be MISSING here, because the derivation line")
print("  has no validation beside it. Asking what the guard actually COVERS")
print("  before concluding it does not cover this path is the rule, and here")
print("  the answer is that it does. Recorded rather than quietly dropped.")

# ---------------------------------------------------------------- D
print("\n########## D. the un-fed class, DRIVEN ##########")
default_seconds = int(
    authorize(workspace("default"), ...)["expires_at"] is not None)
baseline = workspace("baseline")
grant_default = authorize(baseline, ...)
grant_zero = authorize(workspace("zero"), 0)


def span(grant: dict) -> str:
    from datetime import datetime
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    return str(int((parse(grant["expires_at"])
                    - parse(grant["issued_at"])).total_seconds()))


print(f"    duration_seconds absent : {span(grant_default)}s")
print(f"    duration_seconds = 0    : {span(grant_zero)}s")
check("omitting the option gives the configured default", "1800",
      span(grant_default))
check("  and ZERO gives the SAME - falsy, silently replaced", "1800",
      span(grant_zero))
check("    so a caller asking for no window gets the longest one",
      "identical: True",
      f"identical: {span(grant_zero) == span(grant_default)}")

results = []
for label, value in (("5 (below the floor)", 5), ("-5 (negative)", -5),
                     ("10**9 (enormous)", 10 ** 9), ("10.5 (a float)", 10.5),
                     ("'300' (a string)", "300"), ("True (a bool)", True)):
    try:
        observed = f"{span(authorize(workspace(label), value))}s"
    except Exception as exc:  # noqa: BLE001 - the type IS the measurement
        observed = f"{type(exc).__name__}: {exc}"
    results.append((label, observed))
    print(f"    duration_seconds = {label:<20} {observed}")
check("below the floor is refused", "ConfigurationError",
      dict(results)["5 (below the floor)"])
check("  and so is a negative", "ConfigurationError",
      dict(results)["-5 (negative)"])
check("  a string raises a RAW TypeError, not an EFOError", "TypeError",
      dict(results)["'300' (a string)"])
check("  a FLOAT is accepted - the annotation says int", "10",
      dict(results)["10.5 (a float)"])
check("  True is truthy and below the floor, so it is refused",
      "ConfigurationError", dict(results)["True (a bool)"])
check("  and an ENORMOUS duration is accepted - no ceiling",
      "1000000000", dict(results)["10**9 (enormous)"])

# ---------------------------------------------------------------- E
print("\n########## E. what that is, in terms of issues already open ##########")
print("  * The falsy zero is a SECOND instance of the shape item 56 measured")
print("    at workspace.py:876 for `--lease-seconds`. Same expression, other")
print("    method. Not a new issue - the same defect on another surface.")
print("  * The absent ceiling is issue #7's claim ('the floor is enforced,")
print("    the ceiling does not exist') on a SECOND surface. QUANTIFYING an")
print("    open issue, not filing another.")
print("  * The float and the TypeError are the model.py:15 shape: an")
print("    annotation is not a check. #15 already says permissions and gates")
print("    are never type-checked; this is the same class on a third field,")
print("    and it is recorded here rather than appended there.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT retract `NOTE-proxy-grant-holds.md`. Its 27 checks")
print("    stand; what is added is the input class they did not feed.")
print("  * It does NOT file an issue. Every finding here maps onto #7, #15 or")
print("    item 56's measurement.")
print("  * It does NOT drive proxy_submit itself, only the GRANT. The")
print("    delivery path needs a real git repository and the published probe")
print("    already exercises it end to end.")
print("  * It does NOT claim the floor is missing here - section C measured")
print("    the opposite of what I expected and says so.")
print("  * No network, no GPU. Nine tempfile workspaces, removed before the")
print("    results print. The anchor's working tree is untouched, and it does")
print("    not touch `main` or another agent's branch.")
print("  * MEASURED: the AST classification, both quoted source regions, the")
print("    default and zero spans, all six driven durations, the control.")
print("    REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
