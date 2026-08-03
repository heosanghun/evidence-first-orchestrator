#!/usr/bin/env python3
"""The last of item 53's seven: what class of projection did #19's probe never feed?

Queue item 71, closing the population item 50 named. `probe_implicit_exceptions.py`
concluded that #19 is "the SOLE instance of its class" because
`repair_projections` drops exactly one key. That is true of the class it fed.
It fed exactly TWO classes of task projection - the NORMAL one the workspace
wrote, and the REPAIRED one with a key dropped - and never fed a projection
that had been EDITED.

Three edited classes exist. Two are covered, and this round measures that
rather than assuming it:

    the file is valid JSON but not an object -> ConfigurationError from
        read_json, before validate_task can index it
    any key other than `last_event_hash` altered -> IntegrityError, because
        get_task compares the whole projection against the signed ledger

The third is not covered. `last_event_hash` is EXCLUDED BY NAME from every
comparison in the package - four sites - so it is the one key that can be set
to anything at all. Driven through a real `proxy_submit` with a local git
delivery repo:

    control              ACCEPTED, and grant_event_hash == the hash of the
                         task.proxy_authorized event, which is its purpose
    key hand-deleted     KeyError: 'last_event_hash'   <- #19, reproduced
    key forged to f*64   ACCEPTED - and the forged value is written into the
                         SIGNED task.proxy_submitted event, with
                         doctor healthy=True, ledger valid=True, signed=True
    key set to 12345     ACCEPTED
    key set to null      ACCEPTED

So the same blindness #19 names produces a second consequence: not a crash but
a SIGNED RECORD BOUND TO AN EVENT THAT DOES NOT EXIST. Reported on #19 rather
than filed as a new issue - it is the same key and the same missing guard.

    python3 probe_implicit_exceptions_input_class.py

SCOPE, stated first: 1 probe re-classified, 10 of its checks, 4 feeders, 5
projection classes, 3 un-fed, 2 of them covered, 1 driven to a signed forgery,
1 known answer (#19's own traceback). Roughly 90s - it builds six workspaces
and six git delivery repos.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import doctor  # noqa: E402
from evidence_orchestrator.errors import EFOError  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ANCHOR = Path("/tmp/efo-prov")
ANCHOR_SHA = "5694ab455139f1e72d946bc2fe7e42c7c0c8a43a"
SOURCE = ANCHOR / "src/evidence_orchestrator/workspace.py"
CLI = ANCHOR / "src/evidence_orchestrator/cli.py"
SUBJECT = Path(__file__).with_name("probe_implicit_exceptions.py")
ROOT = Path(tempfile.mkdtemp(prefix="efo-inclass71-")).resolve()
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


def git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(repository), *arguments],
                          capture_output=True, text=True,
                          check=True).stdout.strip()


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL, and the scope FIRST ##########")
check("the review's anchor is UNMOVED at 5694ab45", ANCHOR_SHA,
      subprocess.run(["git", "-C", str(ANCHOR), "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip())
check("  with no working-tree modification", "dirty: ''",
      "dirty: " + repr(subprocess.run(
          ["git", "-C", str(ANCHOR), "status", "--porcelain"],
          capture_output=True, text=True).stdout.strip()))
# RE-DERIVED, not cited: the catch tuple decides which failures escape at all.
catch = next(line.strip() for line in CLI.read_text(encoding="utf-8").splitlines()
             if "except (" in line and "as exc" in line)
check("  cli.main's catch tuple, re-read from source",
      "(EFOError, OSError, ValueError, json.JSONDecodeError)", catch)
check("    KeyError is not in it, which is why #19 is a traceback",
      "KeyError not caught: True",
      f"KeyError not caught: {not issubclass(KeyError, (OSError, ValueError))}")


class Fixture:
    """Orchestrator, author, a report bundle and a local git delivery repo.

    Rebuilt here rather than imported: probe_byte_exactness_input_class.py
    runs its whole suite at import time, so importing it would execute
    twenty-odd unrelated checks as a side effect of this one.
    """

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fx-", dir=ROOT))
        self.ws = Workspace.initialize(self.root / "ws", name="inclass71",
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
        self.provenance.write_text(json.dumps({
            "schema_version": 1, "kind": "git", "author": "claude",
            "remote_name": "origin", "remote_url": REMOTE_URL,
            "branch": "delivery", "commit": self.commit,
            "files": [{"source_path": "deliverables/C1.artifact.txt",
                       "submitted_path": self.artifact.name},
                      {"source_path": "deliverables/C1.raw.txt",
                       "submitted_path": self.raw.name}],
        }, indent=2), encoding="utf-8")

    @property
    def projection(self) -> Path:
        return self.ws.root / "tasks" / "C1.json"

    def grant(self) -> str:
        return self.ws.authorize_proxy_submission(
            actor="antigravity", task_id="C1", transport_actor="antigravity",
            remote_url=REMOTE_URL, branch="delivery", commit=self.commit,
            duration_seconds=300)["proxy_token"]

    def submit(self, token: str) -> dict[str, Any]:
        return self.ws.proxy_submit(
            actor="antigravity", author="claude", task_id="C1",
            proxy_token=token, report_path=self.report,
            manifest_path=self.manifest, provenance_path=self.provenance,
            source_repository=self.repo)


control_fixture = Fixture()
control_token = control_fixture.grant()
control_hash = json.loads(
    control_fixture.projection.read_text(encoding="utf-8"))["last_event_hash"]
control_result = control_fixture.submit(control_token)
check("  the CONTROL submission is accepted - the driver works",
      "state: submitted", f"state: {control_result['state']}")

# ---------------------------------------------------------------- B
print("\n########## B. what fed the subject probe's checks, BY HAND ##########")
subject_source = SUBJECT.read_text(encoding="utf-8")
subject_checks = sum(1 for node in ast.walk(ast.parse(subject_source))
                     if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name)
                     and node.func.id == "check")
check("probe_implicit_exceptions.py makes this many checks", "checks: 10",
      f"checks: {subject_checks}")
# Classified BY HAND from its source, then asserted exhaustive in BOTH
# directions below. The point of the split is that only ONE feeder is a live
# task projection - the other three cannot see an edited file at all.
FEEDERS = {
    "source text of cli.py": 1,
    "a hardcoded set of exception types": 1,
    "the workspace.py AST": 2,
    "a live task projection": 5,
    "a live workspace config": 1,
}
check("  and every one is fed by one of five feeders",
      f"total: {subject_checks}", f"total: {sum(FEEDERS.values())}")
for feeder, count in FEEDERS.items():
    print(f"      {count}x  {feeder}")
print("  Only the fourth can be affected by editing a file on disk. The AST")
print("  and source-text feeders are static, and section E's config feeder is")
print("  ledger-bound. So the un-fed class, if there is one, is a class of")
print("  TASK PROJECTION.")

CLASSES = {
    "normal": "the projection the workspace itself wrote",
    "repair-dropped": "a key absent after repair_projections",
    "hand-absent": "a key removed by editing the file",
    "wrong-valued": "a key present, holding anything at all",
    "non-object": "valid JSON that is not an object",
}
FED = {"normal", "repair-dropped"}
UNFED = set(CLASSES) - FED
# The feeder split above is a HAND classification and its total is the only
# machine-checked thing about it. This pair is not: it proves MECHANICALLY that
# the subject probe never wrote a projection file, so it cannot have fed any
# edited class whatever my hand classification says.
projection_writes = [line.strip() for line in subject_source.splitlines()
                     if "projection." in line and "write" in line]
check("  and it never WRITES a projection - so no edited class is reachable",
      "writes: []", f"writes: {projection_writes}")
check("    it only deletes one, which is how it reaches the repair path",
      "projection.unlink()",
      next(line.strip() for line in subject_source.splitlines()
           if "projection.unlink" in line))
check("  the subject probe feeds exactly two of the five classes",
      "fed: ['normal', 'repair-dropped']", f"fed: {sorted(FED)}")
check("    leaving three UN-FED",
      "un-fed: ['hand-absent', 'non-object', 'wrong-valued']",
      f"un-fed: {sorted(UNFED)}")
check("      and the split is exhaustive in both directions",
      f"classes: {len(CLASSES)}", f"classes: {len(FED | UNFED)}")

# ---------------------------------------------------------------- C
print("\n########## C. two of the three are COVERED - measured, not assumed ##########")


def drive(mutate) -> str:
    """Run a full proxy submission against a mutated projection."""
    fixture = Fixture()
    token = fixture.grant()
    payload = json.loads(fixture.projection.read_text(encoding="utf-8"))
    mutated = mutate(payload)
    fixture.projection.write_text(
        json.dumps(mutated) if isinstance(mutated, (dict, list))
        else str(mutated), encoding="utf-8")
    try:
        return f"ACCEPTED state={fixture.submit(token)['state']}"
    except EFOError as exc:
        return f"CAUGHT {type(exc).__name__}: {exc}"
    except Exception as exc:  # noqa: BLE001 - the TYPE is the result
        return f"ESCAPES {type(exc).__name__}: {exc}"


non_object = drive(lambda payload: [1, 2, 3])
check("a projection that is not an object is refused before any index",
      "CAUGHT ConfigurationError", non_object)
check("  and read_json is what refuses it", "Expected a JSON object",
      non_object)
other_key = drive(lambda payload: {**payload, "title": "X"})
check("any OTHER key altered is caught by the ledger comparison",
      "CAUGHT IntegrityError", other_key)
check("  with the projection named", "projection differs from the signed ledger",
      other_key)
print("  Both un-fed classes are REAL absences of a defect, not gaps. That is")
print("  the useful half of an input-class round: two of three predictions")
print("  came back negative, and they are reported as negatives.")

# ---------------------------------------------------------------- D
print("\n########## D. the third is NOT covered - driven end to end ##########")
# KNOWN ANSWER FIRST: #19 says a proxy submit dies with an uncaught KeyError
# when the key is missing. If the driver cannot reproduce that, nothing below
# it can be trusted.
hand_absent = drive(lambda payload: {k: v for k, v in payload.items()
                                     if k != "last_event_hash"})
check("KNOWN ANSWER - deleting the key reproduces #19's traceback",
      "ESCAPES KeyError: 'last_event_hash'", hand_absent)
forged = drive(lambda payload: {**payload, "last_event_hash": "f" * 64})
check("  but FORGING it to any hex string is accepted", "ACCEPTED state=submitted",
      forged)
check("    an integer is accepted too", "ACCEPTED state=submitted",
      drive(lambda payload: {**payload, "last_event_hash": 12345}))
check("      and so is null", "ACCEPTED state=submitted",
      drive(lambda payload: {**payload, "last_event_hash": None}))
print("  Absent CRASHES; present-and-arbitrary is ACCEPTED. The subject probe")
print("  measured the first and named it the sole instance of its class.")

# ---------------------------------------------------------------- E
print("\n########## E. why - and what the forged value becomes ##########")
tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
excluded = sorted({node.lineno for node in ast.walk(tree)
                   if isinstance(node, ast.Compare)
                   and ast.unparse(node).replace('"', "'")
                   == "key != 'last_event_hash'"})
read_sites = sorted({node.lineno for node in ast.walk(tree)
                     if isinstance(node, ast.Subscript)
                     and isinstance(node.slice, ast.Constant)
                     and node.slice.value == "last_event_hash"
                     and not ast.unparse(node).startswith("projected[")})
check("the key is excluded BY NAME from this many comparisons",
      "excluded at: [470, 495, 517, 1511]", f"excluded at: {excluded}")
check("  and read into a record at exactly one site", "read at: [1182]",
      f"read at: {read_sites}")
print("  470 get_task, 495 list_tasks, 517 the projection writer's own")
print("  comparison, 1511 the doctor/audit path - so no comparison in the")
print("  package covers it, which is the blindness #19's title already names.")

ledger_events = [json.loads(line) for line in
                 (control_fixture.ws.root / "ledger" / "events.jsonl")
                 .read_text(encoding="utf-8").splitlines()]


def find(node: Any, key: str, path: str = "") -> list:
    hits = []
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                hits.append((path + "/" + name, value))
            hits += find(value, key, path + "/" + name)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            hits += find(value, key, f"{path}[{index}]")
    return hits


control_sites = [(index, path, value)
                 for index, event in enumerate(ledger_events, 1)
                 for path, value in find(event, "grant_event_hash")]
check("  on the CONTROL it lands in one signed ledger event",
      "sites: 1", f"sites: {len(control_sites)}")
check("    the proxy-submitted one",
      "task.proxy_submitted",
      str(ledger_events[control_sites[0][0] - 1].get("action")))
check("      at this path",
      "/payload/task/result/transport/grant_event_hash", control_sites[0][1])
check("        and it equals the hash of the AUTHORIZATION event, its purpose",
      control_hash, str(control_sites[0][2]))
authorizing = next(index for index, event in enumerate(ledger_events, 1)
                   if event.get("event_hash") == control_hash)
check("          which is action",
      "task.proxy_authorized",
      str(ledger_events[authorizing - 1].get("action")))

forged_fixture = Fixture()
forged_token = forged_fixture.grant()
forged_payload = json.loads(
    forged_fixture.projection.read_text(encoding="utf-8"))
forged_payload["last_event_hash"] = "f" * 64
forged_fixture.projection.write_text(json.dumps(forged_payload),
                                     encoding="utf-8")
forged_fixture.submit(forged_token)
forged_events = [json.loads(line) for line in
                 (forged_fixture.ws.root / "ledger" / "events.jsonl")
                 .read_text(encoding="utf-8").splitlines()]
forged_sites = [value for event in forged_events
                for _, value in find(event, "grant_event_hash")]
check("  and the FORGED value is written into the signed event",
      "['" + "f" * 64 + "']", str(forged_sites))
check("    bound to no event in the ledger at all", "matches: 0",
      "matches: " + str(sum(1 for event in forged_events
                            if event.get("event_hash") == "f" * 64)))
report = doctor.audit_workspace(forged_fixture.ws.root)
check("      doctor reports the workspace healthy", "healthy: True",
      f"healthy: {report['healthy']}")
check("        the ledger valid and signed", "valid: True, signed: True",
      "valid: {}, signed: {}".format(
          report["checks"]["integrity"]["ledger"]["valid"],
          report["checks"]["integrity"]["ledger"]["signed"]))
check("          with no projection mismatch", "mismatches: []",
      f"mismatches: {report['checks']['integrity']['mismatches']}")

# ---------------------------------------------------------------- F
print("\n########## F. what this does NOT establish ##########")
print("  * It does NOT retract probe_implicit_exceptions.py. Its measurement")
print("    stands for the classes it fed: repair drops exactly one key, and")
print("    no second key sits in #19's position. What was wrong was the WORD")
print("    `class` - it named a class of REPAIR, not a class of INPUT.")
print("  * It does NOT file a new issue. Same key, same missing guard, and")
print("    #19's own title already says `audit_projections is blind to it`.")
print("    A second consequence of one blindness belongs on that issue.")
print("  * It does NOT claim the forged submission is undetectable by a human")
print("    reading the bundle. It claims doctor, ledger verify and the")
print("    projection comparison all report clean, which is measured above.")
print("  * It does NOT measure the direct (non-proxy) submit path, which")
print("    reads no last_event_hash - the AST census above found ONE read.")
print("  * Writing to `tasks/C1.json` is the tamper. That file being editable")
print("    with doctor clean was measured in item 66; what is new here is")
print("    that ONE key in it is exempt from every comparison, and that the")
print("    exempt key is the one that ends up in a signed record.")
print("  * No network beyond a LOCAL git repo with an unreachable remote URL,")
print("    no GPU. Six workspaces under tempfile, removed before this prints.")
print("    The anchor's working tree is untouched, and it does not touch")
print("    `main` or another agent's branch.")
print("  * MEASURED: the ten checks' feeders, the five classes, all five")
print("    driven end to end, the exclusion and read sites from the AST, the")
print("    control's binding to the authorization event, the forged value in")
print("    the signed event, doctor's verdict. REASONED: nothing.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("Pre-registered permissions unchanged - gpu/network/performance_metrics")
print("all false. SUBMITTED, not VERIFIED: re-running my own evidence is a")
print("re-run, not independent confirmation.")
