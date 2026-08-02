#!/usr/bin/env python3
"""EFO at main (5694ab45): the evidence size ceiling and the Git LFS guard.

Both are on `NOTE-byte-exactness-holds.md`'s not-examined list.

What the documentation says, and where:

  README.md:391-394
    "At submission, EFO copies the report, manifest, and evidence files up to
     50 MB into `submissions/<task>/<attempt>/`. LARGER ARTIFACTS SUCH AS
     CHECKPOINTS STAY EXTERNAL; their absolute path, byte size, and SHA-256
     remain in the signed record. The size limit is stored in the workspace
     configuration."

  docs/ARCHITECTURE.md:138-142 restates it: larger files "remain external and
  are bound by path".

Nothing in README.md or docs/*.md mentions `max_blob_bytes`, Git LFS, or a
proxy-specific size behaviour. That absence is the point of section C.

The 50 MB default is exercised for real - no reduced stand-in limit - because
the question is whether the DOCUMENTED number behaves as documented.

    python3 probe_blob_limit_and_lfs.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, "/tmp/efo-prov/src")
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-limit-")).resolve()
REMOTE_URL = "https://example.invalid/repository.git"
LIMIT = 50 * 1024 * 1024
REPORT_BODY = "\n".join(
    f"## {n}. Section {n}\n\ncontent\n" for n in range(1, 7)) + "\n"
LFS_HEADER = b"version https://git-lfs.github.com/spec/v1\n"


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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class Fixture:
    """Orchestrator, offline author, task, delivery repo, grant."""

    def __init__(self, artifact_bytes: bytes) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fx-", dir=ROOT))
        self.ws = Workspace.initialize(self.root / "ws", name="limit-probe",
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
        self.artifact = home / "C1.artifact.bin"
        self.artifact.write_bytes(artifact_bytes)
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
        source = self.repo / "deliverables"
        source.mkdir(parents=True)
        (source / "C1.artifact.bin").write_bytes(self.artifact.read_bytes())
        (source / "C1.raw.txt").write_bytes(self.raw.read_bytes())
        git(self.repo, "add", "deliverables")
        git(self.repo, "commit", "-m", "Deliver C1 evidence")
        self.commit = git(self.repo, "rev-parse", "HEAD")

        self.provenance = home / "C1.provenance.json"
        self.provenance.write_text(json.dumps({
            "schema_version": 1, "kind": "git", "author": "claude",
            "remote_name": "origin", "remote_url": REMOTE_URL,
            "branch": "delivery", "commit": self.commit,
            "files": [{"source_path": "deliverables/C1.artifact.bin",
                       "submitted_path": self.artifact.name},
                      {"source_path": "deliverables/C1.raw.txt",
                       "submitted_path": self.raw.name}],
        }, indent=2), encoding="utf-8")

    def configured_limit(self) -> int:
        return int(self.ws.config["defaults"]["max_evidence_bytes"])

    def proxy(self) -> str:
        token = self.ws.authorize_proxy_submission(
            actor="antigravity", task_id="C1", transport_actor="antigravity",
            remote_url=REMOTE_URL, branch="delivery", commit=self.commit,
            duration_seconds=300)["proxy_token"]
        try:
            outcome = self.ws.proxy_submit(
                actor="antigravity", author="claude", task_id="C1",
                proxy_token=token, report_path=self.report,
                manifest_path=self.manifest,
                provenance_path=self.provenance,
                source_repository=self.repo)
            return f"ACCEPTED, state: {outcome['state']}"
        except Exception as exc:  # noqa: BLE001 - the message is the assertion
            return f"{type(exc).__name__}: {exc}"

    def direct(self) -> str:
        """The non-proxy path: claude claims its own task and submits."""
        home = self.ws.reports_dir / "claude"
        home.mkdir(parents=True, exist_ok=True)
        for source in (self.report, self.manifest, self.artifact, self.raw):
            shutil.copy2(source, home / source.name)
        manifest = home / self.manifest.name
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["artifacts"][0]["path"] = str(home / self.artifact.name)
        payload["validations"][0]["raw_output_path"] = str(home / self.raw.name)
        payload["claims"][0]["evidence"] = [str(home / self.artifact.name)]
        manifest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        claim = self.ws.claim(actor="claude", task_id="C1")
        token = claim["lease_token"]
        self.ws.start(actor="claude", task_id="C1", lease_token=token)
        try:
            outcome = self.ws.submit(actor="claude", task_id="C1",
                                     lease_token=token,
                                     report_path=home / self.report.name,
                                     manifest_path=manifest)
            files = outcome["result"]["archive"]["files"]
            external = [f for f in files if not f["retained"]]
            detail = ", ".join(
                f"{f['kind']}={f['size_bytes']}B" for f in external)
            return (f"ACCEPTED, state: {outcome['state']}, "
                    f"left external: {len(external)} ({detail}), "
                    f"still bound by sha256: "
                    f"{all('sha256' in f for f in external)}")
        except Exception as exc:  # noqa: BLE001
            return f"{type(exc).__name__}: {exc}"


def filler(size: int) -> bytes:
    return (b"E" * (size - 1) + b"\n") if size else b""


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - the configured limit is the documented one ##########")
small = Fixture(b"measured artifact\n")
check("the workspace ships the 50 MB default README.md:391 names",
      f"max_evidence_bytes: {LIMIT}",
      f"max_evidence_bytes: {small.configured_limit()}")
check("  and a small artifact submits by proxy", "ACCEPTED, state: submitted",
      small.proxy())

# ---------------------------------------------------------------- B
print("\n########## B. the ceiling, at the real 50 MB boundary ##########")
print("  No reduced stand-in limit: these are genuine 50 MB blobs, because the")
print("  question is whether the DOCUMENTED number behaves as documented.")
for label, size in [("exactly at the limit", LIMIT),
                    ("one byte over", LIMIT + 1)]:
    fixture = Fixture(filler(size))
    blob_size = int(git(fixture.repo, "cat-file", "-s",
                        f"{fixture.commit}:deliverables/C1.artifact.bin"))
    expected = ("ACCEPTED, state: submitted" if size <= LIMIT
                else "exceeds the proxy verification limit")
    check(f"  {label} ({blob_size} bytes)", expected, fixture.proxy())
print("  The comparison is `blob_size > max_blob_bytes` (provenance.py:263),")
print("  so exactly-at-the-limit is accepted and limit+1 is refused. The")
print("  boundary is inclusive and off-by-one clean.")

# ---------------------------------------------------------------- C
print("\n########## C. the same limit, opposite behaviour on the two paths ##########")
print("  README.md:391-394 promises what happens to an over-limit artifact:")
print("    'Larger artifacts such as checkpoints STAY EXTERNAL; their absolute")
print("     path, byte size, and SHA-256 remain in the signed record.'")
print("  Both paths read ONE config key, `max_evidence_bytes`:")
print("    workspace.py:1159  -> validate_git_provenance(max_blob_bytes=...)")
print("    workspace.py:1227  -> archive(max_artifact_bytes=...)")
oversize_direct = Fixture(filler(LIMIT + 1))
check("the DIRECT path honours the documented behaviour",
      "ACCEPTED, state: submitted", oversize_direct.direct())
oversize_proxy = Fixture(filler(LIMIT + 1))
check("the PROXY path refuses the same artifact outright",
      "exceeds the proxy verification limit", oversize_proxy.proxy())
print("  -> `archive.py:128` treats the limit as a COPY threshold")
print("     (`should_copy = force or size <= max_artifact_bytes`), which is")
print("     what README.md:391-394 describes. `provenance.py:263-266` treats")
print("     the identical number as a HARD CEILING and raises.")
print("  The documented sentence is true on the direct path and false on the")
print("  proxy path, and nothing in README.md or docs/*.md says the proxy")
print("  path differs. An offline author delivering a >50 MB checkpoint by")
print("  proxy - the exact scenario PROXY_SUBMISSION.md exists for - cannot")
print("  submit at all, and the refusal names a limit the docs describe as a")
print("  copy threshold.")

# ---------------------------------------------------------------- D
print("\n########## D. the Git LFS guard, and its near misses ##########")
print("  provenance.py:288-291 rejects a blob that startswith:")
print(f"    {LFS_HEADER!r}")
print("  Nothing in README.md or docs/*.md mentions Git LFS at all - this is")
print("  UNDOCUMENTED DEFENCE, so the bar is 'does it do something sensible',")
print("  not 'does it match a promise'.")

POINTER = (LFS_HEADER
           + b"oid sha256:4d7a2143b2ee2b0d1cd94b1a2d7c88bd3ea9d4a2\n"
           + b"size 12345\n")
CASES: dict[str, tuple[bytes, str]] = {
    "a real LFS pointer":
        (POINTER, "Git LFS pointer is not accepted as evidence content"),
    "the header with CRLF instead of LF":
        (LFS_HEADER.replace(b"\n", b"\r\n") + b"size 1\n", "ACCEPTED"),
    "the header uppercased":
        (LFS_HEADER.upper() + b"size 1\n", "ACCEPTED"),
    "the header on line 2, not line 1":
        (b"# notes\n" + LFS_HEADER, "ACCEPTED"),
    "a leading space before the header":
        (b" " + LFS_HEADER, "ACCEPTED"),
    "prose that DOCUMENTS the pointer format":
        (LFS_HEADER + b"\nThe line above is what an LFS pointer looks like.\n",
         "Git LFS pointer is not accepted as evidence content"),
}
for label, (content, expected) in CASES.items():
    check(f"  {label}", expected, Fixture(content).proxy())
print("  The guard is an exact-prefix match on the canonical first line. The")
print("  four near misses are ACCEPTED - correctly, since none of them is a")
print("  pointer Git would smudge; a CRLF or uppercased header is just a file.")
print("  The last row is the honest cost: a legitimate artifact whose first")
print("  line quotes the pointer format is refused. Recorded, NOT FILED -")
print("  nothing claims otherwise, the false-positive class is narrow (the")
print("  quote must be byte-exact AND at offset 0), and refusing evidence is")
print("  the safe direction for a guard whose job is to stop a 130-byte stub")
print("  standing in for a checkpoint.")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("No network call was made: proxy submission never fetches, the remote is")
print("example.invalid, and no LFS object was resolved. Pre-registered")
print("permissions unchanged - gpu/network/performance_metrics all false.")
print("SUBMITTED, not VERIFIED.")
