#!/usr/bin/env python3
"""What "`provenance.py` byte-exactness is clean" fed - and the class it never did.

Queue item 53, first of seven. Item 47 narrowed `util.py is clean` by asking
one question of it: WHAT INPUT CLASS did its checks actually feed? Item 50
showed the cheap mechanical way to ask that of every clean note is refuted, and
named seven notes to do BY HAND instead. This is the first.

`NOTE-byte-exactness-holds.md` reports 20 checks, 0 unexpected, over
`proxy_submit`. Classified by hand, one check at a time:

    11  a BYTE-LEVEL mutation of a well-formed file
     4  an untouched, structurally valid submission (the controls)
     3  a WELL-FORMED provenance list with the wrong MEMBERSHIP
     2  a report whose prose was altered
    --
    20

ZERO of the twenty feed a STRUCTURALLY MALFORMED provenance record. Every one
of the three membership cases is a `list[dict[str, str]]`; only which entries
are in it changes. And `provenance.py` carries three guards for exactly the
class they skip:

    provenance.py:216   declared_files not a list, or empty
    provenance.py:230   files[i] not an object
    provenance.py:234   files[i].submitted_path not a non-empty string

The same shape as items 8, 13, 14 and 47: THE GUARD HAS A TEST, AND THE TEST
FEEDS IT ONLY THE INPUT IT ALREADY HANDLES - found again in my own clean note.

So section D DRIVES the un-fed class rather than leaving it named. Item 47's
answer was 17 raw Python exceptions and 0 EFOError; the answer here is
different, and that difference is the result.

    python3 probe_byte_exactness_input_class.py

SCOPE, stated first: 1 note, 20 checks, 3 unfed guards, 7 driven inputs.
A MAP. No issue filed, and `byte-exactness is clean` is NOT retracted.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
REVIEWS = Path("/workspace/evidence-first-orchestrator/reviews/claude-b/PR2")
COMMITTED = REVIEWS / "raw" / "raw-byte-exactness.txt"
ROOT = Path(tempfile.mkdtemp(prefix="efo-inclass-")).resolve()
REMOTE_URL = "https://example.invalid/repository.git"
REPORT_BODY = "\n".join(
    f"## {n}. Section {n}\n\ncontent\n" for n in range(1, 7)) + "\n"


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
          if line.startswith("  [ok] ") or line.startswith("  [ok]   ")]
check("  checks in the committed byte-exactness output", "checks: 20",
      f"checks: {len(labels)}")
note = (REVIEWS / "NOTE-byte-exactness-holds.md").read_text(encoding="utf-8")
stated = re.search(r"\*\*(\d+) checks, (\d+) unexpected", note)
check("    and the note's headline agrees with the file",
      "stated: 20 / 0", f"stated: {stated.group(1)} / {stated.group(2)}")

# ---------------------------------------------------------------- B
print("\n########## B. the twenty, classified BY HAND ##########")
# Hand adjudication - the cheap proxy is refuted (item 50), so each label was
# read against the probe source one at a time. A lookup table IS a filter, so
# the mapping is asserted EXHAUSTIVE below: an unclassified label fails the run
# rather than vanishing.
CLASS_OF = {
    "the untouched envelope submits": "control (well-formed)",
    "and every declared file was blob-verified": "control (well-formed)",
    "with byte_exact recorded": "control (well-formed)",
    "bound to the commit, not to a checkout": "control (well-formed)",
    "a single flipped byte": "byte mutation",
    "LF -> CRLF (the documented text-mode copy)": "byte mutation",
    "UTF-8 BOM inserted": "byte mutation",
    "encoding conversion to UTF-16LE": "byte mutation",
    "one trailing newline ADDED": "byte mutation",
    "the trailing newline REMOVED": "byte mutation",
    "trailing whitespace on a line": "byte mutation",
    "NUL byte appended": "byte mutation",
    "empty file": "byte mutation",
    "CRLF in the raw output file": "byte mutation",
    "mutate WITHOUT re-syncing the manifest -> the FIRST guard fires":
        "byte mutation",
    "a report with no Git blob behind it submits": "altered prose",
    "the manifest never references the report": "altered prose",
    "dropping the raw output from the provenance list": "membership",
    "listing the same file twice": "membership",
    "two source paths for one submitted file": "membership",
}
unclassified = [label for label in labels if label not in CLASS_OF]
check("every one of the twenty labels is classified - the table is exhaustive",
      "unclassified: []", f"unclassified: {unclassified}")
tally: dict[str, int] = {}
for label in labels:
    tally[CLASS_OF[label]] = tally.get(CLASS_OF[label], 0) + 1
for kind, count in sorted(tally.items(), key=lambda kv: -kv[1]):
    print(f"    {count:>3}  {kind}")
check("  byte-level mutations of a well-formed file", "byte mutation: 11",
      f"byte mutation: {tally['byte mutation']}")
check("  well-formed provenance lists with the wrong membership",
      "membership: 3", f"membership: {tally['membership']}")
check("    and the classes sum to the whole population",
      f"sum: {len(labels)}", f"sum: {sum(tally.values())}")
print("  All three membership cases are a `list[dict[str, str]]`. Only WHICH")
print("  entries are present changes - never the SHAPE of an entry.")

# ---------------------------------------------------------------- C
print("\n########## C. the class the twenty never fed ##########")
source = (ANCHOR / "src" / "evidence_orchestrator" / "provenance.py"
          ).read_text(encoding="utf-8").splitlines()
for line_number in (216, 230, 234):
    print(f"    provenance.py:{line_number}  {source[line_number - 1].strip()}")
check("  provenance.py:216 rejects a non-list `files`",
      "isinstance(declared_files, list)", source[215])
check("    :230 rejects an entry that is not an object",
      "isinstance(record, dict)", source[229])
check("      :234 rejects a non-string submitted_path",
      "isinstance(submitted_value, str)", source[233])
print("  Three guards, and the clean note fed none of them. Same shape as")
print("  issues 8, 13 and 14 and as item 47 - a guard whose test supplies only")
print("  the input it already handles - this time in MY OWN clean note.")


# ---------------------------------------------------------------- D
print("\n########## D. DRIVEN - the un-fed class, against a live submission ##########")


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *arguments],
                          capture_output=True, text=True,
                          check=True).stdout.strip()


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fixture:
    """Same shape as probe_byte_exactness.py's - orchestrator, author, grant.

    Rebuilt here rather than imported: that probe executes its whole run at
    import time, so importing it would re-run twenty checks as a side effect.
    """

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fx-", dir=ROOT))
        self.ws = Workspace.initialize(self.root / "ws", name="inclass-probe",
                                       orchestrator="antigravity",
                                       preset="antigravity-codex-claude")
        self.ws.attest_agent_identity(actor="antigravity",
                                      agent_id="antigravity",
                                      control_principal="google",
                                      model_family="google-antigravity")
        self.ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                                      control_principal="openai",
                                      model_family="openai-codex")
        self.ws.create_task(actor="antigravity", task_id="C1",
                            title="Externally delivered", description="work",
                            owner="claude")
        home = self.ws.reports_dir / "antigravity"
        home.mkdir(parents=True, exist_ok=True)
        self.report = home / "C1.md"
        self.report.write_text(REPORT_BODY, encoding="utf-8")
        self.artifact = home / "C1.artifact.txt"
        self.artifact.write_bytes(b"measured artifact\nsecond line\n")
        self.raw = home / "C1.raw.txt"
        self.raw.write_bytes(b"1 passed in 0.01s\n")
        self.manifest = home / "C1.evidence.json"
        self.manifest.write_text(json.dumps({
            "schema_version": 1,
            "artifacts": [{"path": str(self.artifact),
                           "sha256": sha_of(self.artifact)}],
            "validations": [{"command": "pytest -q", "exit_code": 0,
                             "passed": 1, "failed": 0, "skipped": 0,
                             "skip_reasons": [],
                             "raw_output_path": str(self.raw),
                             "raw_output_sha256": sha_of(self.raw)}],
            "known_answer_checks": [{"name": "two plus two", "expected": 4,
                                     "observed": 4, "passed": True}],
            "claims": [{"name": "functional behavior", "kind": "functional",
                        "measured": True, "value": "pass",
                        "evidence": [str(self.artifact)]}],
        }, indent=2), encoding="utf-8")

        self.repo = self.root / "delivery"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "delivery")
        git(self.repo, "config", "user.name", "Claude Delivery")
        git(self.repo, "config", "user.email", "cd@example.invalid")
        git(self.repo, "config", "core.autocrlf", "false")
        git(self.repo, "remote", "add", "origin", REMOTE_URL)
        source_dir = self.repo / "deliverables"
        source_dir.mkdir(parents=True)
        (source_dir / "C1.artifact.txt").write_bytes(self.artifact.read_bytes())
        (source_dir / "C1.raw.txt").write_bytes(self.raw.read_bytes())
        git(self.repo, "add", "deliverables")
        git(self.repo, "commit", "-m", "Deliver C1 evidence")
        self.commit = git(self.repo, "rev-parse", "HEAD")
        self.provenance = home / "C1.provenance.json"
        self.write_provenance()

    def write_provenance(self, **updates: Any) -> None:
        payload: dict[str, Any] = {
            "schema_version": 1, "kind": "git", "author": "claude",
            "remote_name": "origin", "remote_url": REMOTE_URL,
            "branch": "delivery", "commit": self.commit,
            "files": [{"source_path": "deliverables/C1.artifact.txt",
                       "submitted_path": self.artifact.name},
                      {"source_path": "deliverables/C1.raw.txt",
                       "submitted_path": self.raw.name}],
        }
        payload.update(updates)
        self.provenance.write_text(json.dumps(payload, indent=2),
                                   encoding="utf-8")

    def run(self) -> dict[str, Any]:
        token = self.ws.authorize_proxy_submission(
            actor="antigravity", task_id="C1", transport_actor="antigravity",
            remote_url=REMOTE_URL, branch="delivery", commit=self.commit,
            duration_seconds=300)["proxy_token"]
        return self.ws.proxy_submit(
            actor="antigravity", author="claude", task_id="C1",
            proxy_token=token, report_path=self.report,
            manifest_path=self.manifest, provenance_path=self.provenance,
            source_repository=self.repo)


def drive(label: str, files: Any = ..., **updates: Any) -> str:
    fixture = Fixture()
    if files is not ...:
        updates["files"] = files
    if updates:
        fixture.write_provenance(**updates)
    try:
        return f"ACCEPTED, state: {fixture.run()['state']}"
    except Exception as exc:  # noqa: BLE001 - the exception TYPE is the result
        return f"{type(exc).__name__}"


try:
    control = drive("control")
    outcomes = {
        "files = None": drive("f", files=None),
        "files = {} (an object, not a list)": drive("f", files={}),
        "files = [] (empty list)": drive("f", files=[]),
        'files = ["a string"]': drive("f", files=["a string"]),
        "files = [null]": drive("f", files=[None]),
        "submitted_path = 123": drive("f", files=[
            {"source_path": "deliverables/C1.artifact.txt",
             "submitted_path": 123}]),
        'submitted_path = ""': drive("f", files=[
            {"source_path": "deliverables/C1.artifact.txt",
             "submitted_path": ""}]),
    }
finally:
    shutil.rmtree(ROOT, ignore_errors=True)

print(f"    {'the untouched envelope (CONTROL)':<40}{control}")
for label, outcome in outcomes.items():
    print(f"    {label:<40}{outcome}")
check("the control still submits - the driver is right before the code is",
      "ACCEPTED, state: submitted", control)
EFO = {"EvidenceError", "ConfigurationError", "AuthorizationError",
       "IntegrityError", "TransitionError", "LeaseError", "EFOError",
       "LockTimeout"}
raw_python = {label: outcome for label, outcome in outcomes.items()
              if outcome not in EFO}
check("  every un-fed input is refused - none is ACCEPTED",
      "accepted: []",
      f"accepted: {[k for k, v in outcomes.items() if v.startswith('ACCEPTED')]}")
check("    and every one becomes an EFOError, not a raw Python exception",
      "raw python: {}", f"raw python: {raw_python}")
check("      seven inputs driven", "driven: 7", f"driven: {len(outcomes)}")
print("  This is the OPPOSITE of item 47's answer. There, 17 driven inputs")
print("  gave 17 raw Python exceptions and 0 EFOError. Here all seven convert.")
print("  Item 51 says why: these are guards on a value PARSED FROM A DOCUMENT,")
print("  which is the class EFO does guard - `util.py`'s were on ARGUMENTS,")
print("  which is the class it does not.")

# ---------------------------------------------------------------- E
print("\n########## E. the verdict, narrowed and not retracted ##########")
print("  * `provenance.py byte-exactness is clean` STANDS. All 20 checks still")
print("    pass and nothing here contradicts one of them.")
print("  * What is now stated: those 20 fed byte mutations and membership")
print("    errors, never a malformed record. That gap is REAL and was")
print("    invisible until asked.")
print("  * Driving the gap found EFO sound there too, so this closes rather")
print("    than opens. A NEGATIVE result, and worth publishing as one.")
print("  * NOT filed. Nothing was accepted that should not have been.")

print("\n########## F. what this does NOT do ##########")
print("  * It does not re-run probe_byte_exactness.py's twenty checks; it")
print("    classifies them from the COMMITTED output and drives what they")
print("    missed.")
print("  * It does not adjudicate the other six notes item 50 named.")
print("  * It does not reach provenance.py:294-297, the TOCTOU backstop the")
print("    original note already recorded as unmeasured. Still unmeasured.")
print("  * It does not cover malformed `source_path`, `commit`, `branch` or")
print("    `remote_url` - item 48 drove `_validate_remote_url` and item 51")
print("    censused the guards; this section is about the `files` list.")
print("  * No network: the remote is example.invalid and proxy submission")
print("    never fetches. Workspaces are tempfile directories, removed above.")
print("  * MEASURED: the 20-label classification, its exhaustiveness, the")
print("    three guard lines, all seven driven outcomes and the control.")
print("    REASONED: nothing.")

print(f"\n########## {FAIL} unexpected result(s) ##########")
print("One clean note re-examined by hand and its un-fed input class driven.")
print("Anchor untouched, no `main` write, no issue filed, no verdict")
print("retracted. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false. SUBMITTED, not VERIFIED.")
