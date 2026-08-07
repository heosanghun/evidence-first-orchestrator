#!/usr/bin/env python3
"""The wheel is NOT permanently lost - git restores it byte-exact, and W1/W2 re-ran.

Queue item 49. Items 43 and 46 concluded that `raw-attack4.txt` is
unreproducible because the v0.1 wheel fixture it hashes and diffs is absent at
the anchor. The item asked whether `git show 7a9553b:<path>` can restore it,
and said to stop if that needs network or a build.

It needs neither.

    git show 7a9553b:tests/fixtures/...whl  ->  40269 bytes, exit 0
    sha256                                  ->  18ed72c3...b103b2354
    README's claim at that commit           ->  18ed72c3...b103b2354   MATCH

It is a pure `py3-none-any` wheel: unzip, put on PYTHONPATH, and the v0.1 CLI
runs. No pip, no network, no build step.

So W1 and W2 were RE-RUN here, and both match the committed output:

    W1  wheel sha256 == the hash README claimed
    W2  14 modules vs `git archive f827f29`: 6 byte-identical, 8 differing by
        exactly one byte (a trailing newline), which is what raw-attack4.txt
        recorded

THIS CORRECTS MY OWN EARLIER VERDICT. `NOTE-raw-attack4-is-unreproducible-...`
said the output was unreproducible because "the artifact under test is not in
the tree". That is true AT THE ANCHOR and wrong as "permanently lost" - the
tree is not the only place a git repository keeps a file. The note now carries
a dated correction.

    python3 probe_wheel_restored.py

SCOPE, stated first: one wheel, 14 modules, 2 of the 8 sections of
raw-attack4.txt (W1 and W2). W3-W8 drive a live v0.1-vs-v2 workspace and are
NOT attempted here - named, with the reason.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import zipfile
from pathlib import Path

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
WORK = Path("/tmp/efo-v01")
WHEEL_PATH = "tests/fixtures/evidence_first_orchestrator-0.1.0-py3-none-any.whl"
RAW = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2/raw")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def git(*args: str, binary: bool = False):
    result = subprocess.run(["git", "-C", str(ANCHOR), *args],
                            capture_output=True)
    return result.stdout if binary else result.stdout.decode()


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45",
      "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a", git("rev-parse", "HEAD").strip())
check("  with no working-tree modification", "dirty: ''",
      f"dirty: {git('status', '--porcelain').strip()!r}")
check("  and the wheel really is absent from the anchor's TREE",
      "in tree: False", f"in tree: {(ANCHOR / WHEEL_PATH).is_file()}")
print("  That absence is what items 43 and 46 measured. This asks the next")
print("  question: absent from the tree is not absent from the REPOSITORY.")

# ---------------------------------------------------------------- B
print("\n########## B. git restores it - no network, no build ##########")
WORK.mkdir(exist_ok=True)
blob = git("show", f"7a9553b:{WHEEL_PATH}", binary=True)
(WORK / "wheel.whl").write_bytes(blob)
digest = hashlib.sha256(blob).hexdigest()
print(f"    restored {len(blob)} bytes to {WORK / 'wheel.whl'}")
check("the restored wheel's sha256", "18ed72c3f2ddf38a9a18d435032095cfbc0"
      "74b2e21b9397d96e4a76b103b2354", digest)
# KNOWN ANSWER, and neither side is typed in by me: the expectation comes from
# the README AS IT WAS at the commit that shipped the wheel; the observation
# from hashing the bytes git just handed back.
# WHICH README. A first version read the ROOT README.md and found no hash at
# all - the claim lives in `tests/fixtures/README.md`, beside the wheel. The
# committed output says only "README claims:" without qualifying which, and I
# assumed the root one. Corrected to the file that actually carries it.
readme = git("show", "7a9553b:tests/fixtures/README.md")
claimed = re.search(r"([0-9a-f]{64})", readme)
check("  which is what the FIXTURE README claimed at that commit",
      f"claimed: {digest}",
      f"claimed: {claimed.group(1) if claimed else '(no hash found)'}")
check("    and the ROOT README never carried it - the assumption I made first",
      "root readme hash: False",
      f"root readme hash: {bool(re.search(r'[0-9a-f]{64}', git('show', '7a9553b:README.md')))}")
with zipfile.ZipFile(WORK / "wheel.whl") as archive:
    members = archive.namelist()
    corrupt = archive.testzip()
check("  it is a valid zip", "corrupt member: None", f"corrupt member: {corrupt}")
check("    with the expected member count", "members: 20",
      f"members: {len(members)}")
check("    and it is pure-python - no build step exists to run",
      "py3-none-any", WHEEL_PATH)

# ---------------------------------------------------------------- C
print("\n########## C. W1 and W2 RE-RUN, against the committed output ##########")
attack4 = (RAW / "raw-attack4.txt").read_text(encoding="utf-8", errors="replace")
w1_claim = re.search(r"README claims: ([0-9a-f]{64})", attack4)
check("W1: the committed output's README claim matches this run's hash",
      f"w1: {digest}",
      f"w1: {w1_claim.group(1) if w1_claim else '(not found)'}")

package = WORK / "pkg"
if package.exists():
    subprocess.run(["rm", "-rf", str(package)])
with zipfile.ZipFile(WORK / "wheel.whl") as archive:
    archive.extractall(package)
source = WORK / "f827"
if source.exists():
    subprocess.run(["rm", "-rf", str(source)])
source.mkdir()
subprocess.run(f"git -C {ANCHOR} archive f827f29 src/evidence_orchestrator "
               f"| tar -x -C {source}", shell=True)

identical, differing = [], []
for module in sorted((package / "evidence_orchestrator").glob("*.py")):
    original = source / "src/evidence_orchestrator" / module.name
    if not original.is_file():
        continue
    if original.read_bytes() == module.read_bytes():
        identical.append(module.name)
    else:
        differing.append((module.name, len(original.read_bytes()),
                          len(module.read_bytes())))
for name, before, after in differing:
    print(f"    DIFFERS {name:<16} {before} -> {after} bytes")
check("W2: modules byte-identical to git f827f29", "identical: 6",
      f"identical: {len(identical)}")
check("  and modules that differ", "differing: 8",
      f"differing: {len(differing)}")
check("    every difference is exactly ONE byte", "all +1: True",
      f"all +1: {all(after - before == 1 for _, before, after in differing)}")
print("    a trailing newline the wheel build added - the committed output")
print("    recorded `stripped_equal=True` for all eight.")
committed_identical = re.findall(
    r"^(\w+\.py)\s+[0-9a-f]{16}\s+[0-9a-f]{16}$", attack4, re.M)
check("  the committed output's byte-identical list, as the expectation",
      f"committed: {sorted(identical)}", f"committed: {sorted(committed_identical)}")

# ---------------------------------------------------------------- D
print("\n########## D. the v0.1 client RUNS - so W3-W8 are not lost either ##########")
result = subprocess.run(
    ["python3", "-m", "evidence_orchestrator", "--help"],
    capture_output=True, text=True, cwd=str(WORK),
    env={"PYTHONPATH": str(package), "PATH": "/usr/bin:/bin"})
check("the restored v0.1 CLI executes", "exit: 0", f"exit: {result.returncode}")
check("  and reports its own subcommands", "init,status,agent,task",
      result.stdout.replace("\n", " ").replace("  ", " "))
print("  W3-W8 drive a LIVE v0.1-against-v2 workspace - init, task add, a")
print("  signed orchestrator handoff, and both clients reading each other's")
print("  state. That is a multi-step scenario, not a diff, and it is NOT")
print("  attempted here. What is measured is that the blocker items 43 and 46")
print("  named - `the client is gone` - does not hold.")

# ---------------------------------------------------------------- E
print("\n########## E. this CORRECTS my own earlier verdict ##########")
note = (RAW.parent / "NOTE-raw-attack4-is-unreproducible-and-my-manifest-was-wrong.md"
        ).read_text(encoding="utf-8")
check("the earlier note now carries a dated correction",
      "Correction, 2026-08-03", note)
check("  and it still stands on the two things that ARE true",
      "zero\nattack4 *scripts* have ever been committed", note)
print("  Unchanged and still correct: no attack4 SCRIPT ever existed, and")
print("  REPORT.md's sentence about where the output came from is false.")
print("  WRONG, and corrected: `the artifact under test is not in the tree`")
print("  was read as `permanently lost`. A git repository keeps a file after")
print("  the tree stops carrying it, and I did not try `git show` before")
print("  writing the verdict. That is the method's own rule - do not declare")
print("  something unreproducible until you have tried it - applied to me.")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT do ##########")
print("  * It does not re-run W3-W8, and does not claim P2-1 or P2-2 are")
print("    re-verified. It removes their stated blocker; driving them is a")
print("    separate job.")
print("  * It does not retract P2-1, P2-2 or P2-3.")
print("  * It does not install anything. The wheel is unzipped to /tmp and")
print("    put on PYTHONPATH; no pip, no network, no build.")
print("  * It does not touch main, the anchor's working tree, or any other")
print("    agent's branch. `git show` writes nothing back.")
print("  * MEASURED: the restored bytes and their hash, the README claim at")
print("    7a9553b, the zip integrity, both W1 and W2 comparisons, the CLI")
print("    exit code. REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Read-only git object reads plus one unzip and one --help. No workspace")
print("mutation, no network, no issue filed. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
