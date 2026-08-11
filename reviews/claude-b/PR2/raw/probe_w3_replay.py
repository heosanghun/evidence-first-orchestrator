#!/usr/bin/env python3
"""W3 of `raw-attack4.txt` REPLAYS - six steps, and the driver had to be rebuilt.

Queue item 52. Item 49 restored the v0.1 wheel from `git show 7a9553b:` and
re-ran W1 and W2, leaving W3-W8 un-run but no longer blocked. This does W3.

SCOPE, stated first, because the item asked for it before anything else:

    W3..W8 plus a W6b rerun is ~24 commands across 7 sections, driving a live
    v0.1-against-v2 shared workspace: init, task add, a signed orchestrator
    handoff, and both clients reading each other's state. Every one of them is
    a LOCAL FILESYSTEM command - EFO is a file-backed orchestrator and its own
    suite runs offline - so NO NETWORK AND NO SERVER are needed for any of it.
    Twenty-four is more than one round, so this does W3 ALONE, which is six
    steps, and says so.

THE DRIVER IS GONE, AND THAT IS THE INTERESTING PART.

Item 43 established that no `attack4` script ever existed in the repository -
`git log --all --diff-filter=D` finds nothing. So the exact command sequence is
NOT recoverable; it had to be RECONSTRUCTED from the output. The reconstruction
is not assumed correct - it is checked against two things the committed artifact
records and a wrong sequence would not produce:

    the ledger event count  (7)
    the rejection string    ("Agent 'antigravity' registration differs ...")

A first reconstruction - init + task add - produced FIVE events and v0.1 exiting
ZERO. It was wrong, and the event count said so. The missing step is
`agent attest`: v0.1 rejects a v2 workspace only once an agent carries an
identity attestation, which is the property W3 is about.

Every expectation below is PARSED OUT OF the committed `raw-attack4.txt`; the
observations come from a fresh run in a temporary directory. Neither side is
typed in twice.

    python3 probe_w3_replay.py

A REPLAY, not a new finding. No issue filed, nothing retracted.
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
V2 = ANCHOR / "src"
V1 = Path("/tmp/efo-v01/pkg")
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


def run(client: Path, *argv: str) -> tuple[int, str]:
    done = subprocess.run(
        ["python3", "-m", "evidence_orchestrator", *argv],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": str(client), "PATH": "/usr/bin:/bin",
             "HOME": "/tmp", "LC_ALL": "C.UTF-8"})
    return done.returncode, (done.stdout + done.stderr)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a",
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {subprocess.run(['git', '-C', str(ANCHOR), 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()!r}")

# The v0.1 client is the artifact item 49 restored. If it is missing the whole
# probe is meaningless, so assert it BEFORE anything is concluded from it.
check("  the restored v0.1 client is present and importable",
      "v0.1 CLI: 0", f"v0.1 CLI: {run(V1, '--help')[0]}")
check("    and it is NOT the anchor's source", "same tree: False",
      f"same tree: {V1.resolve() == V2.resolve()}")

text = COMMITTED.read_text(encoding="utf-8")
sections = re.findall(r"^#{10} (W\d\w?) ", text, re.M)
print(f"  sections in the committed output: {sections}")
check("  the committed output carries TEN sections, not eight",
      "sections: ['W1', 'W2', 'W2b', 'W3', 'W4', 'W5', 'W6', 'W7', 'W8', "
      "'W6b']", f"sections: {sections}")
# W1, W2 and W2b were re-run by item 49; the remainder is DERIVED from the
# measured list rather than typed, so a new section cannot slip past.
remaining = [s for s in sections if s not in ("W1", "W2", "W2b")]
check("    of which item 49 already re-ran three", "remaining: 7",
      f"remaining: {len(remaining)}")
check("      leaving exactly this population",
      "left: ['W3', 'W4', 'W5', 'W6', 'W7', 'W8', 'W6b']",
      f"left: {remaining}")
# Slice the section by its FULL header line. A first version split on
# "##########\nv2", which ate the `v2` of `v2 init exit=0` and made the inline
# count 1 where the file has 2 - the count is what caught it.
w3 = re.split(r"^#{10} W3 .*#{10}$", text, flags=re.M)[1]
w3 = re.split(r"^#{10} W4 ", w3, flags=re.M)[0]
check("        this round attempts ONE of the seven",
      "attempting: W3", f"attempting: {remaining[0]}")
print("  Every command in all seven sections is a local filesystem call -")
print("  no network, no server. Twenty-four of them is more than one round.")

# ---------------------------------------------------------------- B
print("\n########## B. the expectations, PARSED from the committed output ##########")
REJECTION = re.search(
    r"error: (Agent '?antigravity'? registration differs from the signed ledger)",
    w3).group(1)
committed_ledger = json.loads(
    re.search(r"-- v0\.1 ledger verify --\n(\{.*?\n\})", w3, re.S).group(1))
exits = re.findall(r"^exit=(\d+)$", w3, re.M)
print(f"    rejection string : {REJECTION!r}")
print(f"    ledger           : {committed_ledger}")
print(f"    exit codes, in order: {exits}")
inline = re.findall(r"^(v2 \w+(?: \w+)?) exit=(\d+)$", w3, re.M)
print(f"    v2 setup lines, written inline: {inline}")
check("  the committed W3 records four standalone exit lines", "exits: 4",
      f"exits: {len(exits)}")
check("    plus two v2 setup exits written INLINE - six steps in all",
      "inline: 2, total: 6",
      f"inline: {len(inline)}, total: {len(exits) + len(inline)}")
check("      and both v2 setup steps succeeded in the committed run",
      "v2 setup exits: ['0', '0']", f"v2 setup exits: {[c for _, c in inline]}")
check("    and a signed, valid ledger of 7 events",
      "events 7 signed True valid True",
      f"events {committed_ledger['events']} "
      f"signed {committed_ledger['signed']} valid {committed_ledger['valid']}")
print("  None of these is typed into this probe - they are read out of the")
print("  artifact, so the artifact supplies the expectation and the fresh run")
print("  supplies the observation.")

# ---------------------------------------------------------------- C
print("\n########## C. the RECONSTRUCTED driver, and why the first one was wrong ##########")
print("  No `attack4` script ever existed (item 43), so the sequence below is")
print("  rebuilt from the output. A first attempt ran only:")
print("      v2 init --preset antigravity-codex-claude ; v2 task add")
print("  and produced ledger events=5 with v0.1 status exit=0 - no rejection")
print("  at all. THE EVENT COUNT IS WHAT SAID IT WAS WRONG. The missing step")
print("  is `agent attest`, which writes the identity block v0.1 cannot read.")

workspace = Path(tempfile.mkdtemp(prefix="efo-w3-")) / "ws4"
observed = {}
try:
    code, _ = run(V2, "init", str(workspace), "--name", "compat",
                  "--preset", "antigravity-codex-claude")
    observed["v2 init"] = code
    code, _ = run(V2, "task", "add", str(workspace), "--actor", "antigravity",
                  "--id", "C1", "--owner", "codex", "--title", "compat probe",
                  "--description", "claude-b item 52 W3")
    observed["v2 task add"] = code
    for agent in ("antigravity", "codex"):
        code, _ = run(V2, "agent", "attest", str(workspace),
                      "--actor", "antigravity", "--id", agent,
                      "--control-principal", "antigravity",
                      "--model-family", "unknown")
        observed[f"v2 agent attest {agent}"] = code

    status_code, status_out = run(V1, "status", str(workspace))
    ledger_code, ledger_out = run(V1, "ledger", "verify", str(workspace))
    doctor_code, doctor_out = run(V1, "doctor", str(workspace))
    show_code, show_out = run(V1, "task", "show", str(workspace), "--id", "C1")
    fresh_ledger = json.loads(ledger_out[ledger_out.index("{"):
                                         ledger_out.rindex("}") + 1])
    fresh_doctor = json.loads(doctor_out[doctor_out.index("{"):
                                         doctor_out.rindex("}") + 1])
finally:
    shutil.rmtree(workspace.parent, ignore_errors=True)

for label, code in observed.items():
    print(f"    {label:<32}exit={code}")
check("  every v2 setup command succeeded",
      "non-zero: []",
      f"non-zero: {[k for k, v in observed.items() if v != 0]}")

# ---------------------------------------------------------------- D
print("\n########## D. W3 REPLAYED - six steps, committed vs fresh ##########")
print(f"    v0.1 status        exit={status_code}")
print(f"    v0.1 ledger verify exit={ledger_code}  {fresh_ledger}")
print(f"    v0.1 doctor        exit={doctor_code}  "
      f"healthy={fresh_doctor.get('healthy')}")
print(f"    v0.1 task show C1  exit={show_code}")
check("the v0.1 client REJECTS the v2 workspace, with the recorded string",
      REJECTION, status_out)
check("  and exits 2, as the committed run did", "status exit: 2",
      f"status exit: {status_code}")
check("  the ledger still verifies - signed, valid, 7 events",
      f"events {committed_ledger['events']} signed True valid True",
      f"events {fresh_ledger['events']} signed {fresh_ledger['signed']} "
      f"valid {fresh_ledger['valid']}")
check("    and ledger verify exits 0 even though status exits 2",
      "ledger exit: 0", f"ledger exit: {ledger_code}")
check("  doctor reports the SAME error and healthy=false",
      REJECTION, json.dumps(fresh_doctor))
check("    while itself exiting 0", "doctor exit: 0",
      f"doctor exit: {doctor_code}")
check("  and the task IS readable by v0.1 despite the agent rejection",
      "show exit: 0", f"show exit: {show_code}")
print("  Six for six. The shape W3 recorded is real and reproduces: the v0.1")
print("  client refuses the AGENT record while accepting the LEDGER and the")
print("  TASK written by v2 - it fails closed on identity, not on the chain.")

# ---------------------------------------------------------------- E
print("\n########## E. what does NOT reproduce, and why ##########")
committed_head = committed_ledger["head"]
check("the committed ledger head is NOT reproduced - and must not be",
      "heads equal: False",
      f"heads equal: {committed_head == fresh_ledger['head']}")
print(f"    committed head : {committed_head[:32]}...")
print(f"    fresh head     : {fresh_ledger['head'][:32]}...")
print("  The chain is HMAC-signed with a per-workspace key and every event")
print("  carries a timestamp, so a byte-equal head would mean the run had NOT")
print("  been redone. What must match is the PROPERTIES - count, signed,")
print("  valid, exit codes, the error string - and those do.")
print("  Also NOT reproduced, and not attempted: W8's thirteen-key agent")
print("  record. That listing was taken AFTER the W4 handoff, so it carries")
print("  `governance_epoch` and `active`; the record at W3 time has ten keys.")
print("  Reading it as a W3 expectation would be reading the wrong section.")

print("\n########## F. what this does NOT do ##########")
print("  * It does not run W4-W8. Their blocker is gone and their scope is")
print("    stated above; they remain UN-RUN and are not claimed otherwise.")
print("  * It does not claim P2-1 or P2-2 are re-verified.")
print("  * It does not file an issue and retracts nothing.")
print("  * It does not recover the original driver - that script never")
print("    existed. The sequence here is a reconstruction that matches the")
print("    recorded event count and error string; a different sequence")
print("    reaching the same state is not excluded.")
print("  * No network, no server, no pip, no build. The workspace is a")
print("    tempfile directory, removed before this section printed.")
print("  * MEASURED: all four parsed expectations, all four v2 setup exits,")
print("    all six W3 outcomes, the head mismatch. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Two clients driven against one temporary workspace. Anchor untouched,")
print("no `main` write, no issue filed. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
