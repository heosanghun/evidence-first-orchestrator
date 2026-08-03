#!/usr/bin/env python3
"""W4 cannot be replayed at the anchor - the feature is on a DIVERGENT history.

Queue item 55. Item 52 replayed W3 of `raw-attack4.txt` six-for-six at the
anchor and left W4-W8 un-run, saying their blocker was gone. For W4 that is
WRONG, and this says so first.

    `transfer_orchestrator` - the CLI command, the Workspace method and three
    test call sites, 7 occurrences across 3 files - exists at 7a9553b and is
    ABSENT EVERYWHERE at 5694ab45.
    `git merge-base --is-ancestor 7a9553b 5694ab45` says NO: 7a9553b is not an
    ancestor of the anchor. The anchor descends from f827f29 instead.

So `raw-attack4.txt` mixes two lines of history. W1/W2/W2b compare the v0.1
wheel against `git archive f827f29` - the anchor's ancestor - while W4, W5, W6
and W6b drive a v2 that only exists on the OTHER line. W3 reproduced at the
anchor because its property (the v0.1 client refusing an attested agent record)
is common to both.

W4 IS replayable - against 7a9553b, which this names explicitly rather than
letting the reader assume the anchor. Both refs are printed.

The item asked whether W4's two tracebacks are the ORIGINAL DRIVER's defects
rather than EFO's. Measured:

    FileNotFoundError on ws4/workspace.json   DRIVER DEFECT - reproduces
                                              exactly; the config is at
                                              .efo/workspace.json, and reading
                                              that gives `antigravity`
    KeyError: 'orchestrator'                  DRIVER DEFECT - the CLI `status`
                                              JSON has keys ['status','tasks'],
                                              so indexing 'orchestrator' on the
                                              WRAPPER raises. W6b's rerun with
                                              the nested key returns `codex`

And the divergence W6/W6b report is REAL AND BY DESIGN: at 7a9553b
`Workspace.orchestrator` seeds from `config["orchestrator"]` and then replays
every `workspace.orchestrator_transferred` event, so the config file keeps
`antigravity` while the effective orchestrator is `codex`.

    python3 probe_w4_replay.py

SCOPE, stated first: 2 refs, 1 of 7 remaining sections, 5 driven commands.
A MAP about a ref this review is NOT anchored to. No issue filed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
OTHER = Path("/tmp/efo-7a9553b")
COMMITTED = (Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
             / "raw" / "raw-attack4.txt")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *arguments],
                          capture_output=True, text=True).stdout.strip()


def run(source: Path, *argv: str) -> tuple[int, str]:
    done = subprocess.run(
        ["python3", "-m", "evidence_orchestrator", *argv],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": str(source), "PATH": "/usr/bin:/bin",
             "HOME": "/tmp", "LC_ALL": "C.UTF-8"})
    return done.returncode, (done.stdout + done.stderr)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      git(ANCHOR, "rev-parse", "HEAD"))
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git(ANCHOR, 'status', '--porcelain')!r}")
print("  This probe reads a SECOND ref on purpose and names both, the way")
print("  ADDENDUM-main-is-red does. The anchor is still not re-pointed.")
check("  the second checkout is at 7a9553b", "7a9553b",
      git(OTHER, "rev-parse", "--short=7", "HEAD"))
check("    and it is a different commit from the anchor", "same: False",
      f"same: {git(OTHER, 'rev-parse', 'HEAD') == git(ANCHOR, 'rev-parse', 'HEAD')}")

# ---------------------------------------------------------------- B
print("\n########## B. the feature W4 needs is ABSENT at the anchor ##########")
present_at_other = git(OTHER, "grep", "-l", "transfer_orchestrator",
                       "7a9553b").splitlines()
present_at_anchor = git(ANCHOR, "grep", "-l", "transfer_orchestrator",
                        "5694ab45").splitlines()
for path in present_at_other:
    print(f"    7a9553b  {path}")
# THREE files, not five: I wrote five from a reading of the seven matching
# LINES. `git grep -l` counts files; the occurrence count is asked for
# separately so neither number can stand in for the other.
occurrences = git(OTHER, "grep", "-c", "transfer_orchestrator",
                  "7a9553b").splitlines()
check("transfer_orchestrator lives in three files at 7a9553b",
      "at 7a9553b: 3", f"at 7a9553b: {len(present_at_other)}")
check("  over seven occurrences - cli, workspace and one test file",
      "occurrences: 7",
      "occurrences: " + str(sum(int(line.rsplit(":", 1)[1])
                                for line in occurrences)))
check("  and in NONE at the anchor - not src, not tests, not docs",
      "at anchor: []", f"at anchor: {present_at_anchor}")

ancestor = subprocess.run(
    ["git", "-C", str(ANCHOR), "merge-base", "--is-ancestor",
     "7a9553b", "5694ab45"], capture_output=True)
check("    and 7a9553b is NOT an ancestor of the anchor - divergent history",
      "is ancestor: False", f"is ancestor: {ancestor.returncode == 0}")
print(f"    the anchor's workspace.py line: "
      f"{git(ANCHOR, 'log', '--oneline', '5694ab45', '--', 'src/evidence_orchestrator/workspace.py').splitlines()[-1]}")

# The action name is DERIVED from the anchor's own source, not typed, so a
# rename cannot make this check pass by accident.
anchor_actions = sorted(set(re.findall(
    r'"((?:agent|task|workspace)\.[a-z_]+)"',
    "\n".join((ANCHOR / "src" / "evidence_orchestrator" / name)
              .read_text(encoding="utf-8")
              for name in ("workspace.py", "ledger.py", "adapter.py")))))
print(f"    the anchor's ledger actions: {anchor_actions}")
check("      none of them is an orchestrator transfer",
      "transfer actions: []",
      f"transfer actions: {[a for a in anchor_actions if 'orchestrator' in a]}")
print("  So W4, W5, W6 and W6b drive an API the anchor does not have. Item")
print("  52 said their blocker was gone; for these four a DIFFERENT blocker")
print("  exists, and that note is corrected in place.")

# ---------------------------------------------------------------- C
print("\n########## C. the expectations, PARSED from the committed W4 ##########")
text = COMMITTED.read_text(encoding="utf-8")
w4 = re.split(r"^#{10} W4 .*#{10}$", text, flags=re.M)[1]
w4 = re.split(r"^#{10} W5 ", w4, flags=re.M)[0]
committed_event = json.loads(re.search(r"(\{.*?\n\})", w4, re.S).group(1))
print(f"    handoff payload keys : {sorted(committed_event)}")
print(f"    from -> to           : {committed_event['from']} -> "
      f"{committed_event['to']}")
tracebacks = re.findall(r"^(\w+Error): (.*)$", w4, re.M)
for kind, detail in tracebacks:
    print(f"    traceback            : {kind}: {detail[:64]}")
check("  the committed handoff records four keys",
      "keys: ['event_hash', 'from', 'to', 'reason']",
      f"keys: {sorted(committed_event, key=['event_hash', 'from', 'to', 'reason'].index)}")
check("    and W4 records exactly two tracebacks", "tracebacks: 2",
      f"tracebacks: {len(tracebacks)}")

# ---------------------------------------------------------------- D
print("\n########## D. W4 REPLAYED - against 7a9553b, not the anchor ##########")
root = Path(tempfile.mkdtemp(prefix="efo-w4-"))
workspace = root / "ws"
try:
    init_code, _ = run(OTHER / "src", "init", str(workspace), "--name",
                       "compat", "--preset", "antigravity-codex-claude")
    transfer_code, transfer_out = run(
        OTHER / "src", "workspace", "transfer-orchestrator", str(workspace),
        "--actor", "antigravity", "--to", "codex", "--reason", "claude-b test")
    fresh_event = json.loads(transfer_out[transfer_out.index("{"):
                                          transfer_out.rindex("}") + 1])

    def driver(expression: str) -> str:
        done = subprocess.run(
            ["python3", "-c", expression], capture_output=True, text=True,
            env={"PYTHONPATH": str(OTHER / "src"), "PATH": "/usr/bin:/bin",
                 "HOME": "/tmp", "LC_ALL": "C.UTF-8"})
        if done.returncode == 0:
            return done.stdout.strip()
        last = done.stderr.strip().splitlines()[-1]
        return last

    wrong_path = driver(
        f"import json; print(json.load(open({str(workspace / 'workspace.json')!r}))['orchestrator'])")
    right_path = driver(
        f"import json; print(json.load(open({str(workspace / '.efo' / 'workspace.json')!r}))['orchestrator'])")
    wrong_key = driver(
        "import json, subprocess, sys;"
        "out = subprocess.run([sys.executable, '-m', 'evidence_orchestrator',"
        f" 'status', {str(workspace)!r}], capture_output=True, text=True).stdout;"
        "print(json.loads(out)['orchestrator'])")
    right_key = driver(
        "import json, subprocess, sys;"
        "out = subprocess.run([sys.executable, '-m', 'evidence_orchestrator',"
        f" 'status', {str(workspace)!r}], capture_output=True, text=True).stdout;"
        "print(json.loads(out)['status']['orchestrator'])")
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"    init                                     exit={init_code}")
print(f"    workspace transfer-orchestrator          exit={transfer_code}")
print(f"    from -> to                               {fresh_event.get('from')}"
      f" -> {fresh_event.get('to')}")
check("the handoff succeeds, as the committed run recorded",
      "transfer exit: 0", f"transfer exit: {transfer_code}")
check("  and returns the same four keys",
      f"keys: {sorted(committed_event)}", f"keys: {sorted(fresh_event)}")
check("    with the same from and to",
      f"{committed_event['from']} -> {committed_event['to']}",
      f"{fresh_event.get('from')} -> {fresh_event.get('to')}")
check("      but NOT the same event_hash - it is signed and timestamped",
      "hashes equal: False",
      f"hashes equal: {committed_event['event_hash'] == fresh_event.get('event_hash')}")

# ---------------------------------------------------------------- E
print("\n########## E. both tracebacks are the DRIVER's, adjudicated ##########")
print(f"    driver's path  ws/workspace.json        {wrong_path}")
print(f"    correct path   ws/.efo/workspace.json   {right_path}")
print(f"    driver's key   status()['orchestrator'] {wrong_key}")
print(f"    correct key    ['status']['orchestrator'] {right_key}")
check("the driver's path reproduces the committed FileNotFoundError",
      "FileNotFoundError", wrong_path)
check("  and the CORRECT path reads the config fine", "antigravity", right_path)
check("    the driver's key reproduces the committed KeyError",
      "KeyError: 'orchestrator'", wrong_key)
check("      and the CORRECT key - W6b's - returns the new orchestrator",
      "codex", right_key)
print("  Both are the ORIGINAL DRIVER's defects, not EFO's: one wrong path,")
print("  one index on the CLI's `{status, tasks}` wrapper. W6b is the same")
print("  question asked correctly, and it answers.")

# ---------------------------------------------------------------- F
print("\n########## F. the config/ledger divergence is REAL, and by design ##########")
source = (OTHER / "src" / "evidence_orchestrator" / "workspace.py"
          ).read_text(encoding="utf-8")
body = source.split("def orchestrator(self)")[1].split("def ")[0]
for line in body.strip().splitlines():
    print(f"      {line.strip()}")
check("7a9553b's `orchestrator` seeds from the CONFIG",
      'orchestrator = str(self.config["orchestrator"])', body)
check("  then REPLAYS the transfer events from the ledger",
      "workspace.orchestrator_transferred", body)
print("  So `config file orchestrator: antigravity` and `effective")
print("  orchestrator: codex` are BOTH correct at once - the config is a seed")
print("  and the ledger is the authority. W6/W6b measured a real divergence,")
print("  and it is the intended one, not a defect.")
print("  This says NOTHING about the anchor, where no such event exists and")
print("  `orchestrator` is the config value alone.")

print("\n########## G. what this does NOT do ##########")
print("  * It does not run W5, W6, W6b, W7 or W8. Four of the six remaining")
print("    sections need 7a9553b, which is now checked out and named.")
print("  * It does not review 7a9553b. That commit is NOT this review's")
print("    subject; nothing here is a verdict about its code.")
print("  * It does not file an issue and retracts no finding. It DOES correct")
print("    item 52's `their blocker is gone`, in place and dated.")
print("  * It does not claim to know which v2 produced raw-attack4.txt - only")
print("    that the API W4 uses exists on 7a9553b's line and not the anchor's.")
print("  * No network, no server. Both checkouts are local; the workspace is a")
print("    tempfile directory, removed before this section printed.")
print("  * MEASURED: both file censuses, the ancestry, the anchor's action")
print("    list, the committed payload, all five driven commands, both")
print("    tracebacks and both corrections, the property body. REASONED:")
print("    nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Two refs read and named. The anchor's working tree is untouched, no")
print("`main` write, no issue filed. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
