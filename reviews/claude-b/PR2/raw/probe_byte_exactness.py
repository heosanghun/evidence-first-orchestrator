#!/usr/bin/env python3
"""EFO proxy submission at main (5694ab45): the byte-exactness claim.

`NOTE-proxy-grant-holds.md` measured the GRANT gates - replay, expiry, cross
workspace, state ordering. It did not measure the bytes. This does.

The claim, and which paragraph each half sits in:

  PROXY_SUBMISSION.md:78-82
    "The blob comparison intentionally happens before any checkout conversion.
     LF-to-CRLF conversion, BOM insertion, encoding conversion, or any other
     byte mutation is a hard failure even when rendered text looks identical."

  PROXY_SUBMISSION.md:61-63
    "The transport actor CREATES the six-section report and evidence envelope
     under its own report directory. Claim-bearing ARTIFACTS AND RAW
     VALIDATION OUTPUTS must be exact Git blobs from the author's commit."

  MIGRATION.md:141-143 (looser wording for the same rule)
    "The transport envelope belongs under the transport actor's report
     directory. Its claim-bearing files must be byte-identical to raw Git
     blobs. Do not copy them through a text-mode tool."

Section B is the attack surface. Each mutation is applied to the SUBMITTED
file AND the manifest hash is updated to match, so that the guard under test
is the blob comparison and not the earlier manifest-hash check. Section C
measures both orderings and shows there are three layers, not two.

    python3 probe_byte_exactness.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-bytes-")).resolve()
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


class Fixture:
    """Orchestrator, offline author, task, delivery repo, grant."""

    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fx-", dir=ROOT))
        self.ws = Workspace.initialize(self.root / "ws", name="bytes-probe",
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
        self.home = home
        self.report = home / "C1.md"
        self.report.write_text(REPORT_BODY, encoding="utf-8")
        self.artifact = home / "C1.artifact.txt"
        self.artifact.write_bytes(b"measured artifact\nsecond line\n")
        self.raw = home / "C1.raw.txt"
        self.raw.write_bytes(b"1 passed in 0.01s\n")
        self.manifest = home / "C1.evidence.json"
        self.write_manifest()

        self.repo = self.root / "delivery"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "delivery")
        git(self.repo, "config", "user.name", "Claude Delivery")
        git(self.repo, "config", "user.email", "cd@example.invalid")
        git(self.repo, "config", "core.autocrlf", "false")
        git(self.repo, "remote", "add", "origin", REMOTE_URL)
        source = self.repo / "deliverables"
        source.mkdir(parents=True)
        (source / "C1.artifact.txt").write_bytes(self.artifact.read_bytes())
        (source / "C1.raw.txt").write_bytes(self.raw.read_bytes())
        git(self.repo, "add", "deliverables")
        git(self.repo, "commit", "-m", "Deliver C1 evidence")
        self.commit = git(self.repo, "rev-parse", "HEAD")

        self.provenance = home / "C1.provenance.json"
        self.write_provenance()

    def write_manifest(self) -> None:
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

    def run(self, **over: Any) -> dict[str, Any]:
        token = self.ws.authorize_proxy_submission(
            actor="antigravity", task_id="C1", transport_actor="antigravity",
            remote_url=REMOTE_URL, branch="delivery", commit=self.commit,
            duration_seconds=300)["proxy_token"]
        kwargs: dict[str, Any] = {
            "actor": "antigravity", "author": "claude", "task_id": "C1",
            "proxy_token": token, "report_path": self.report,
            "manifest_path": self.manifest,
            "provenance_path": self.provenance,
            "source_repository": self.repo,
        }
        kwargs.update(over)
        return self.ws.proxy_submit(**kwargs)


def attempt(name: str, expected: str, mutate: Callable[[Fixture], None],
            *, resync_manifest: bool = True) -> None:
    fixture = Fixture()
    mutate(fixture)
    if resync_manifest:
        fixture.write_manifest()
    try:
        fixture.run()
        observed = "ACCEPTED"
    except Exception as exc:  # noqa: BLE001 - the message is the assertion
        observed = f"{type(exc).__name__}: {exc}"
    check(name, expected, observed)


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - a byte-exact submission is accepted ##########")
base = Fixture()
result = base.run()
check("the untouched envelope submits", "state: submitted",
      f"state: {result['state']}")
provenance_record = result["result"]["provenance"]
check("  and every declared file was blob-verified", "verified: 2",
      "verified: " + str(len(provenance_record["files"])))
check("  with byte_exact recorded", "byte_exact: True",
      "byte_exact: " + str(provenance_record["byte_exact"]))
check("  bound to the commit, not to a checkout", base.commit,
      provenance_record["commit"])
print("  The control is LIVE: one flipped byte in the artifact must be refused.")
attempt("  a single flipped byte",
        "Git blob bytes differ from submitted evidence",
        lambda f: f.artifact.write_bytes(
            f.artifact.read_bytes().replace(b"measured", b"meesured")))

# ---------------------------------------------------------------- B
print("\n########## B. every mutation PROXY_SUBMISSION.md:78-82 names ##########")
print("  Each is applied to the SUBMITTED file and the manifest hash is")
print("  re-synced, so the guard under test is the BLOB comparison and not")
print("  the earlier manifest-hash check. Section C shows there are THREE")
print("  layers here and proves which one these results exercise.")

MUTATIONS: dict[str, Callable[[bytes], bytes]] = {
    "LF -> CRLF (the documented text-mode copy)":
        lambda b: b.replace(b"\n", b"\r\n"),
    "UTF-8 BOM inserted":
        lambda b: b"\xef\xbb\xbf" + b,
    "encoding conversion to UTF-16LE":
        lambda b: b.decode("utf-8").encode("utf-16-le"),
    "one trailing newline ADDED":
        lambda b: b + b"\n",
    "the trailing newline REMOVED":
        lambda b: b.rstrip(b"\n"),
    "trailing whitespace on a line":
        lambda b: b.replace(b"artifact\n", b"artifact \n"),
    "NUL byte appended":
        lambda b: b + b"\x00",
    "empty file":
        lambda _: b"",
}
for label, mutate in MUTATIONS.items():
    attempt(f"  {label}",
            "Git blob bytes differ from submitted evidence",
            lambda f, m=mutate: f.artifact.write_bytes(m(f.artifact.read_bytes())))
print("  Every documented mutation is a HARD FAILURE, and the message names")
print("  the cause: 'possible newline or transport mutation'. Rendered text")
print("  being identical does not help - the comparison is over raw bytes")
print("  from `git cat-file blob`, never a checkout.")

print("\n  The raw validation output is held to the same rule, not just artifacts:")
attempt("  CRLF in the raw output file",
        "Git blob bytes differ from submitted evidence",
        lambda f: f.raw.write_bytes(f.raw.read_bytes().replace(b"\n", b"\r\n")))

# ---------------------------------------------------------------- C
print("\n########## C. three guards, not one, and they fire in order ##########")
attempt("mutate WITHOUT re-syncing the manifest -> the FIRST guard fires",
        "Evidence artifact SHA mismatch",
        lambda f: f.artifact.write_bytes(b"tampered\n"),
        resync_manifest=False)
print("  -> that message is `evidence.py:119`, raised while the manifest is")
print("     validated - BEFORE provenance.py is entered at all. So the layers")
print("     are:")
print("       1. evidence.py:119        manifest hash vs file, at validation")
print("       2. provenance.py:294-297  manifest hash vs file, AGAIN, inside")
print("                                 the provenance loop")
print("       3. provenance.py:298-303  Git blob bytes vs file")
print("     Layer 2 is unreachable from outside: it can only fire if the file")
print("     changes BETWEEN layers 1 and 3, i.e. a concurrent writer during a")
print("     single proxy_submit. It is a TOCTOU backstop, and this probe did")
print("     NOT reach it - that is stated as unmeasured, not as covered.")
print("  The point for a prober: a run that forgot to re-sync the manifest")
print("  measures layer 1 and never exercises layer 3, and would report the")
print("  blob check as working when it had never executed.")

# ---------------------------------------------------------------- D
print("\n########## D. is the six-section REPORT byte-bound? ##########")
print("  It is NOT, and the narrow document says so plainly.")
altered = Fixture()
altered.report.write_text(REPORT_BODY.replace("content", "different content"),
                          encoding="utf-8")
try:
    outcome = altered.run()
    observed = f"ACCEPTED, state: {outcome['state']}"
except Exception as exc:  # noqa: BLE001
    observed = f"{type(exc).__name__}: {exc}"
check("a report with no Git blob behind it submits", "ACCEPTED", observed)
evidence_map = json.loads(altered.manifest.read_text(encoding="utf-8"))
check("  the manifest never references the report",
      "report in manifest: False",
      "report in manifest: " + str(
          altered.report.name in json.dumps(evidence_map)))
print("  NOT FILED, and the reason is which paragraph the claim sits in:")
print("    PROXY_SUBMISSION.md:61-63 says the transport actor CREATES the")
print("    six-section report, and requires exactness of 'claim-bearing")
print("    ARTIFACTS AND RAW VALIDATION OUTPUTS' - a set that excludes it.")
print("    MIGRATION.md:141-143 is looser ('its claim-bearing files'), but the")
print("    narrow document governs and is self-consistent: a file the")
print("    transport actor authors cannot also be a blob from the author's")
print("    commit.")
print("  Worth an operator knowing anyway: `byte_exact: true` in the recorded")
print("  provenance covers the artifacts and raw outputs. The prose of the")
print("  report around them is transport-authored and commit-bound to nothing.")

# ---------------------------------------------------------------- E
print("\n########## E. the completeness rule (PROXY_SUBMISSION.md:73) ##########")
print("  'every claim-bearing artifact and raw output is listed once'")
attempt("dropping the raw output from the provenance list",
        "Git provenance does not bind every claim-bearing evidence file",
        lambda f: f.write_provenance(files=[
            {"source_path": "deliverables/C1.artifact.txt",
             "submitted_path": f.artifact.name}]))
attempt("  listing the same file twice",
        "Duplicate submitted_path in Git provenance",
        lambda f: f.write_provenance(files=[
            {"source_path": "deliverables/C1.artifact.txt",
             "submitted_path": f.artifact.name},
            {"source_path": "deliverables/C1.artifact.txt",
             "submitted_path": f.artifact.name},
            {"source_path": "deliverables/C1.raw.txt",
             "submitted_path": f.raw.name}]))
attempt("  two source paths for one submitted file",
        "Duplicate submitted_path in Git provenance",
        lambda f: f.write_provenance(files=[
            {"source_path": "deliverables/C1.artifact.txt",
             "submitted_path": f.artifact.name},
            {"source_path": "deliverables/C1.raw.txt",
             "submitted_path": f.artifact.name},
            {"source_path": "deliverables/C1.raw.txt",
             "submitted_path": f.raw.name}]))
print("  Both directions are closed: nothing may be omitted, and nothing may")
print("  be listed twice. The set equality at provenance.py:320 is what makes")
print("  'listed once' mechanical rather than advisory.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("No network call was made: proxy submission never fetches, and the")
print("remote is example.invalid. Pre-registered permissions unchanged -")
print("gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
