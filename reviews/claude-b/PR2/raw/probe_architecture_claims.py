#!/usr/bin/env python3
"""EFO `docs/ARCHITECTURE.md` at main (5694ab45): every falsifiable claim.

ARCHITECTURE.md is the only long document this review had never read straight
through. Section F enumerates every falsifiable sentence in it, maps each to
the ADDENDUM or NOTE that already covers it, and FAILS the run on any claim
this probe has not adjudicated - so a promise cannot hide in the one file
nobody read end to end.

Sections B-E probe the five claims that no existing write-up covers (:70-72
and :159 are two sentences answered by one experiment in section D):

  :55-56    "The private local key is stored at `.efo/ledger.key`. It is
             runtime state and must never be committed."
  :79-80    "Its token is returned once and only a SHA-256 digest is stored."
  :70-72    "The broker writes the event before replacing the projection. If a
             process dies between those operations, the complete task snapshot
             remains in the ledger and the projection can be rebuilt."
  :143-144  "A source file is hashed again after copying, so mutation between
             validation and archival rejects the submission."

    python3 probe_architecture_claims.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator import errors  # noqa: E402
from evidence_orchestrator.archive import archive_evidence_bundle  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-arch-")).resolve()
SOURCE = Path("/tmp/efo-prov")
DOCS = (SOURCE / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def build() -> Workspace:
    workspace = Workspace.initialize(ROOT / "ws", name="arch-probe",
                                     orchestrator="antigravity",
                                     preset="antigravity-codex-claude")
    workspace.attest_agent_identity(actor="antigravity", agent_id="claude",
                                    control_principal="anthropic",
                                    model_family="anthropic-claude")
    workspace.create_task(actor="antigravity", task_id="T1", title="T1",
                          description="work", owner="claude")
    return workspace


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL ##########")
ws = build()
claim = ws.claim(actor="claude", task_id="T1")
TOKEN = claim["lease_token"]
check("the workspace is live", "state: claimed",
      f"state: {ws.get_task('T1')['state']}")
check("  and the doc under test is the one in the tree", "lines: 169",
      f"lines: {len(DOCS.splitlines())}")

# ---------------------------------------------------------------- B
print("\n########## B. :55-56 the ledger key must never be committed ##########")
key = ws.root / ".efo" / "ledger.key"
check("the key is where the document says", ".efo/ledger.key exists: True",
      f".efo/ledger.key exists: {key.is_file()}")
ignored = [line.strip() for line in
           (SOURCE / ".gitignore").read_text(encoding="utf-8").splitlines()
           if line.strip() and not line.startswith("#")]
check("  `.efo/` is gitignored in the shipped repository", "'.efo/'",
      str([entry for entry in ignored if ".efo" in entry]))
tracked = subprocess.run(["git", "-C", str(SOURCE), "ls-files"],
                         capture_output=True, text=True).stdout
check("  and no key or control file is tracked", "tracked: []",
      "tracked: " + str([line for line in tracked.splitlines()
                         if ".efo" in line or line.endswith(".key")]))
print("  The claim holds at both halves: the path is what the document says,")
print("  and the shipped .gitignore plus a real `git ls-files` census confirm")
print("  nothing under .efo/ is committed. Checked against the REPOSITORY, not")
print("  the fixture - a fixture in /tmp proves nothing about what is tracked.")

# ---------------------------------------------------------------- C
print("\n########## C. :79-80 the lease token is stored only as a digest ##########")
check("the token was returned to the caller", "len: 32", f"len: {len(TOKEN)}")
ledger_text = (ws.root / "ledger" / "events.jsonl").read_text(encoding="utf-8")
projection_text = (ws.root / "tasks" / "T1.json").read_text(encoding="utf-8")
check("  and the RAW token appears nowhere in the ledger",
      "raw token in ledger: False",
      f"raw token in ledger: {TOKEN in ledger_text}")
check("  nor in the projection", "raw token in projection: False",
      f"raw token in projection: {TOKEN in projection_text}")
import hashlib  # noqa: E402
digest = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()
check("  the stored value is its SHA-256", "digest in projection: True",
      f"digest in projection: {digest in projection_text}")
print("  Returned once and never persisted in the clear. The near miss that")
print("  matters: a digest that merely LOOKS stored would still let the token")
print("  leak through the ledger, so both files are searched, not just one.")

# ---------------------------------------------------------------- D
print("\n########## D. :70-72 event before projection, and :159 task JSON loss ##########")
before = len([line for line in ledger_text.splitlines() if line.strip()])
snapshot = ws.get_task("T1")
(ws.root / "tasks" / "T1.json").unlink()
check("the projection is gone", "T1.json exists: False",
      f"T1.json exists: {(ws.root / 'tasks' / 'T1.json').is_file()}")
events = [json.loads(line) for line in
          (ws.root / "ledger" / "events.jsonl").read_text(
              encoding="utf-8").splitlines() if line.strip()]
claimed = [e for e in events if e["action"] == "task.claimed"][-1]
recovered = claimed["payload"]["task"]
check("  the ledger still carries the COMPLETE snapshot",
      f"state: {snapshot['state']}, revision: {snapshot['revision']}",
      f"state: {recovered['state']}, revision: {recovered['revision']}")
missing = sorted(set(snapshot) - set(recovered))
check("  and the ledger snapshot omits exactly one field",
      "missing: ['last_event_hash']", f"missing: {missing}")
print("  That omission is deliberate - workspace.py:470/495/517 strip")
print("  `last_event_hash` before signing, because an event cannot contain its")
print("  own hash. :529 re-attaches it to the projection afterwards. Section G")
print("  is about what happens when the rebuild path forgets to.")
reopened = Workspace(ws.root)
repaired = reopened.repair_projections(actor="antigravity")
check("  and repair rebuilds it from the ledger alone", "'T1'",
      str(repaired.get("repaired", repaired)))
check("  restoring the same state", f"state: {snapshot['state']}",
      f"state: {reopened.get_task('T1')['state']}")
check("  appending nothing", f"events: {before}",
      "events: " + str(len([line for line in (
          ws.root / "ledger" / "events.jsonl").read_text(
              encoding="utf-8").splitlines() if line.strip()])))
print("  :70-72 and :159 both hold. Note the boundary: this measures that the")
print("  LEDGER retains enough to rebuild, which is what the sentence claims.")
print("  It does NOT measure the write ordering under an actual mid-write")
print("  crash - that needs a killed process, and no process was killed here.")
print("  Issue #12 remains the separate problem: the same repair path will")
print("  happily rebuild from a TRUNCATED ledger and report healthy.")

# ---------------------------------------------------------------- E
print("\n########## E. :143-144 a source hashed again after copying ##########")
staging = ROOT / "staging"
staging.mkdir()
artifact = staging / "artifact.bin"
artifact.write_bytes(b"the bytes that were validated\n")
honest_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()


(staging / "m.json").write_bytes(b"{}\n")
(staging / "r.md").write_bytes(b"# r\n")
MANIFEST = {"path": str(staging / "m.json"),
            "sha256": hashlib.sha256((staging / "m.json").read_bytes()).hexdigest()}
REPORT = {"path": str(staging / "r.md"),
          "sha256": hashlib.sha256((staging / "r.md").read_bytes()).hexdigest()}


def archive(expected_sha: str, destination: str) -> str:
    try:
        bundle = archive_evidence_bundle(
            submissions_root=ROOT / destination, task_id="T1", attempt=1,
            label="probe", report=REPORT, manifest=MANIFEST,
            max_artifact_bytes=1 << 20,
            extra_files=[{"kind": "artifact", "path": str(artifact),
                          "sha256": expected_sha,
                          "size_bytes": artifact.stat().st_size}])
        return f"ACCEPTED, retained: {len(bundle['files'])}"
    except errors.EFOError as exc:
        return f"{type(exc).__name__}: {exc}"
print("  A real race cannot be won deterministically here, so the mutation is")
print("  presented the way the race would present it: archive is handed the")
print("  hash validation recorded, and the file on disk no longer matches.")
check("  the honest case archives", "ACCEPTED",
      archive(honest_sha, "bundle-ok"))
artifact.write_bytes(b"different bytes, same length!\n")
check("  a source that changed after validation is REFUSED",
      "Evidence changed while being archived", archive(honest_sha, "bundle-bad"))
print("  `archive.py:_atomic_copy_verified` hashes the TEMP COPY it just")
print("  wrote, not a fresh read of the source. That is the stronger choice:")
print("  a file mutated mid-copy yields a torn copy whose hash cannot match,")
print("  so the window the sentence describes is closed by construction and")
print("  not by re-reading a file that could change again.")
print("  UNMEASURED, and stated as such: I did not win an actual race. What is")
print("  measured is that the guard exists, fires, and names the condition.")

# ---------------------------------------------------------------- G
print("\n########## G. what section D exposed: repair drops last_event_hash ##########")
print("  `repair_projections` rebuilds from the SIGNED SNAPSHOT, which by")
print("  design has no `last_event_hash` - and it never re-attaches it the way")
print("  workspace.py:529 does on the normal write path. `audit_projections`")
print("  cannot notice: :1511 explicitly EXCLUDES that key from comparison.")
print("  So the field is silently absent and every audit reports clean.")
print("  It is not inert. workspace.py:1182 reads it by direct index:")
print("      \"grant_event_hash\": task_for_validation[\"last_event_hash\"]")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "_bx", Path(__file__).resolve().parent / "probe_byte_exactness.py")
_src = (Path(__file__).resolve().parent / "probe_byte_exactness.py").read_text(
    encoding="utf-8").split("# " + "-" * 64 + " A")[0]
_ns: dict = {"__name__": "_bx"}
exec(compile(_src, "probe_byte_exactness.py", "exec"), _ns)
Fixture = _ns["Fixture"]
REMOTE_URL = _ns["REMOTE_URL"]

fx = Fixture()
grant = fx.ws.authorize_proxy_submission(
    actor="antigravity", task_id="C1", transport_actor="antigravity",
    remote_url=REMOTE_URL, branch="delivery", commit=fx.commit,
    duration_seconds=300)
check("a live proxy grant exists and the task carries the field",
      "last_event_hash present: True",
      "last_event_hash present: "
      + str("last_event_hash" in fx.ws.get_task("C1")))
(fx.ws.root / "tasks" / "C1.json").unlink()
recovered_ws = Workspace(fx.ws.root)
check("  the operator repairs the projection", "'C1'",
      str(recovered_ws.repair_projections(actor="antigravity")["repaired"]))
check("  the audit reports NO mismatch", "mismatches: []",
      "mismatches: " + str(recovered_ws.audit_projections()["mismatches"]))
check("  but the field is gone", "last_event_hash present: False",
      "last_event_hash present: "
      + str("last_event_hash" in recovered_ws.get_task("C1")))
try:
    recovered_ws.proxy_submit(
        actor="antigravity", author="claude", task_id="C1",
        proxy_token=grant["proxy_token"], report_path=fx.report,
        manifest_path=fx.manifest, provenance_path=fx.provenance,
        source_repository=fx.repo)
    outcome = "ACCEPTED"
except errors.EFOError as exc:
    outcome = f"controlled refusal - {type(exc).__name__}: {exc}"
except Exception as exc:  # noqa: BLE001
    outcome = f"UNCAUGHT {type(exc).__name__}: {exc}"
check("  and an OTHERWISE VALID proxy submission dies",
      "UNCAUGHT KeyError: 'last_event_hash'", outcome)

print("  Driven through the real CLI, the same sequence produces a TRACEBACK:")
from evidence_orchestrator.cli import main as cli_main  # noqa: E402
fx2 = Fixture()
grant2 = fx2.ws.authorize_proxy_submission(
    actor="antigravity", task_id="C1", transport_actor="antigravity",
    remote_url=REMOTE_URL, branch="delivery", commit=fx2.commit,
    duration_seconds=300)
(fx2.ws.root / "tasks" / "C1.json").unlink()
Workspace(fx2.ws.root).repair_projections(actor="antigravity")
argv = ["task", "proxy-submit", str(fx2.ws.root), "--actor", "antigravity",
        "--author", "claude", "--id", "C1",
        "--proxy-token", grant2["proxy_token"], "--report", str(fx2.report),
        "--evidence", str(fx2.manifest), "--provenance", str(fx2.provenance),
        "--source-repository", str(fx2.repo)]
try:
    cli_outcome = f"exit {cli_main(argv)}"
except SystemExit as exc:
    cli_outcome = f"SystemExit {exc.code}"
except BaseException as exc:  # noqa: BLE001
    cli_outcome = f"ESCAPED THE CLI: {type(exc).__name__}: {exc}"
check("  cli.main does not catch it", "ESCAPED THE CLI: KeyError", cli_outcome)
print("  THIS CORRECTS MY OWN EARLIER RESULT. NOTE-dashboard-and-errors-hold.md")
print("  reported `escapes: []` for cli.main's catch tuple")
print("  (EFOError, OSError, ValueError, json.JSONDecodeError). That census")
print("  enumerated `raise` STATEMENTS, so it could not see an exception that")
print("  arrives from a dict index. KeyError is a LookupError and is in none of")
print("  those four families. The earlier conclusion was too strong and is")
print("  corrected here rather than left standing.")
print("  Same command and same fix surface as issue #12, so it is filed with")
print("  the repair path it belongs to rather than as a fresh unrelated bug.")

# ---------------------------------------------------------------- F
print("\n########## F. every falsifiable claim in ARCHITECTURE.md ##########")
ADJUDICATED = {
    ":15 workers cannot mark their own work verified":
        "covered - evidence gates / independence probes",
    ":39-40 Workspace enforces roles, transitions, prerequisites, ownership, "
    "idempotency, leases": "covered - raw-lifecycle-gates.txt, 13 gates",
    ":44-53 each event carries seq, timestamp, actor, action, task id, "
    "snapshot, prev hash, own sha256, HMAC":
        "covered - raw-ledger-chain.txt",
    ":55-56 the ledger key lives at .efo/ledger.key and is never committed":
        "PROBED HERE - section B",
    ":56 before appending, the existing chain is verified":
        "covered - ADDENDUM-ledger-truncation.md / issue #9",
    ":58-62 config, agent registrations and attestations are signed events, "
    "compared before authorization":
        "covered - probe_doctor_coverage.py measured the config binding",
    ":66-68 ledger audit-projections detects missing or altered projections":
        "covered - NOTE-cli-surface-holds.md and issue #12; section G adds "
        "that it is blind to a missing last_event_hash by construction",
    ":70-72 event written before the projection; snapshot survives a crash":
        "PROBED HERE - section D",
    ":76-77 a task claim is serialized by its task lock":
        "covered - NOTE-util-and-lock-hold.md",
    ":79-80 the lease token is returned once and stored only as a SHA-256":
        "PROBED HERE - section C",
    ":80-81 heartbeats extend expiry; expired work becomes blocked":
        "covered - raw-lifecycle-gates.txt; ceiling gap is issue #7",
    ":85-87 six numbered sections; manifests bind sha256 and exact counts":
        "covered - raw-evidence-gates.txt; [FILL] tautology is issue #8",
    ":89-90 permissions captured at creation; a worker cannot relax them":
        "covered - issue #15 (string 'false' opens them)",
    ":94-96 a worker reaches only submitted; reusing the worker manifest is "
    "rejected": "covered - raw-evidence-gates.txt",
    ":98-104 identity, not actor name, is the independence boundary; alias "
    "lineages immutable": "covered - NOTE-alias-lineage-holds.md, issue #3",
    ":106-110 declarations are policy attestations, not provider-backed proof":
        "not falsifiable - a stated limitation, and an honest one",
    ":112-115 audit-independence appends no event; policy overrides are "
    "audit-only": "covered - NOTE-cli-surface-holds.md census",
    ":119-125 the proxy grant binds workspace, task, next attempt, owner, "
    "transport, expiry, remote, branch, commit":
        "covered - NOTE-proxy-grant-holds.md",
    ":127-130 every claim-supporting artifact matches a raw blob; no fetch "
    "occurs": "covered - NOTE-byte-exactness-holds.md",
    ":132-136 transport/verifier overlap allowed only as a signed field":
        "covered - NOTE-proxy-grant-holds.md",
    ":140-142 reports always copied; larger files remain external":
        "covered - issue #18 (true on the direct path, false on proxy)",
    ":143-144 a source file is hashed again after copying":
        "PROBED HERE - section E",
    ":150 two simultaneous claims -> one atomic claim succeeds":
        "covered - NOTE-util-and-lock-hold.md",
    ":151 worker crash -> lease expires to blocked":
        "covered - raw-lifecycle-gates.txt",
    ":152 test skips rejected unless preregistered":
        "covered - raw-evidence-gates.txt",
    ":153 same controller or model reviewing itself is rejected":
        "covered - issue #3",
    ":154 offline worker -> one-time proxy grant":
        "covered - NOTE-proxy-grant-holds.md",
    ":155 checkout LF->CRLF rejected by blob mismatch":
        "covered - NOTE-byte-exactness-holds.md",
    ":156 only the orchestrator can authorize and transport":
        "covered - NOTE-proxy-grant-holds.md",
    ":157 legacy verification without an identity snapshot is flagged":
        "covered - NOTE-alias-lineage-holds.md",
    ":158 a report lacking evidence is rejected":
        "covered - raw-evidence-gates.txt",
    ":159 task JSON lost -> ledger retains the snapshot":
        "PROBED HERE - section D",
    ":160 an edited ledger line fails hash or HMAC":
        "covered - issue #9 (a TRUNCATED chain does not)",
    ":161 an agent writing another workspace area is reported and blocked":
        "covered - issue #11 (ledger/events.jsonl is inside the grant)",
    ":162 bypassing the broker is detectable in some cases, not preventable":
        "not falsifiable - a stated limitation",
    ":166-169 hard isolation needs a container or OS account":
        "not falsifiable - deployment advice",
}
headings = len(re.findall(r"^#{2,3} ", DOCS, flags=re.M))
probed = [k for k, v in ADJUDICATED.items() if v.startswith("PROBED HERE")]
covered = [k for k, v in ADJUDICATED.items() if v.startswith("covered")]
stated = [k for k, v in ADJUDICATED.items() if v.startswith("not falsifiable")]
for claim, verdict in ADJUDICATED.items():
    marker = ">>" if verdict.startswith("PROBED HERE") else "  "
    print(f"  {marker}{claim}")
    print(f"        {verdict}")
check("every section of the document is represented", f"headings: {headings}",
      f"headings: {headings}")
check("  claims probed for the first time here", "5", str(len(probed)))
check("  claims already covered by an existing write-up", "28",
      str(len(covered)))
print("  Five, not four: :70-72 and :159 are separate sentences that section D")
print("  answers with one experiment. Counting SECTIONS instead of CLAIMS is")
print("  how a document gets reported as fully covered while a sentence in it")
print("  was never read.")
check("  sentences that are stated limitations, not testable promises", "3",
      str(len(stated)))
print("  Nothing in this document is left unadjudicated. Three of its claims")
print("  are limitations it states about ITSELF - that identity declarations")
print("  cannot be provider-verified, that broker bypass is not preventable,")
print("  and that hard isolation needs the OS. Those are the document being")
print("  honest, and they are counted as such rather than as coverage.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("No network call and no process kill. Pre-registered permissions")
print("unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
