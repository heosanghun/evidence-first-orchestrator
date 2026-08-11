#!/usr/bin/env python3
"""EFO proxy submission at main (5694ab45): the one-time grant and its archival.

`proxy_submit` is the only path by which work enters the workspace without the
author ever touching it.  Its safety rests on a single-use signed grant plus
Git-bound bytes.  Issues #4 and #5 already cover provenance.py itself, so this
probes what they do not: the grant lifecycle, and the archival call at
workspace.py:1220 that force-retains the provenance manifest.

Section A is the positive control - an honest proxy submission must reach
`submitted` before any refusal below means anything.  Every rejection is
asserted on its MESSAGE, by substring.

    python3 probe_proxy_grant.py
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
from evidence_orchestrator.doctor import audit_workspace  # noqa: E402
from evidence_orchestrator.workspace import Workspace  # noqa: E402

FAIL = 0
ROOT = Path(tempfile.mkdtemp(prefix="efo-proxy-"))
REMOTE_URL = "https://example.invalid/efo-delivery.git"

REPORT_BODY = "\n".join([
    "# report", "",
    "## 1. Scope", "proxy grant probe", "",
    "## 2. What was done", "one passing check", "",
    "## 3. Counts", "passed=1 failed=0 skipped=0", "",
    "## 4. Known-answer comparison", "expected 4, observed 4", "",
    "## 5. Outside ownership", "none", "",
    "## 6. Not verified", "nothing", "",
])


def check(name: str, expected: str, observed: str) -> None:
    global FAIL
    ok = expected in observed
    if not ok:
        FAIL += 1
    print(f"  [{'ok' if ok else '!! UNEXPECTED !!'}] {name}")
    print(f"        expected: {expected}")
    print(f"        observed: {observed}")


def attempt(name: str, expected: str, fn) -> None:
    try:
        value = fn()
        check(name, expected, f"accepted ({value})")
    except Exception as exc:
        check(name, expected, f"rejected ({type(exc).__name__}: {exc})")


def git(repository: Path, *arguments: str) -> str:
    done = subprocess.run(["git", "-C", str(repository), *arguments],
                          check=True, capture_output=True, text=True)
    return done.stdout.strip()


def sha_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Fixture:
    """An orchestrator, an offline author, a task, a delivery repo, a grant."""

    def __init__(self, *, artifact_bytes: int | None = None,
                 author_principal: str = "openai",
                 author_family: str = "openai-codex") -> None:
        self.root = Path(tempfile.mkdtemp(prefix="fx-", dir=ROOT))
        self.ws = Workspace.initialize(self.root / "ws", name="proxy-probe",
                                       orchestrator="antigravity",
                                       preset="antigravity-codex-claude")
        self.ws.attest_agent_identity(actor="antigravity",
                                      agent_id="antigravity",
                                      control_principal="google",
                                      model_family="google-antigravity")
        # `claude` already exists: the preset registers it. Attest it into the
        # principal/family this fixture needs.
        self.ws.attest_agent_identity(actor="antigravity", agent_id="claude",
                                      control_principal=author_principal,
                                      model_family=author_family)
        self.ws.add_agent(actor="antigravity", agent_id="other", role="worker",
                          mode="manual", control_principal="mistral",
                          model_family="mistral-large")
        self.ws.create_task(actor="antigravity", task_id="C1",
                            title="Externally delivered", description="work",
                            owner="claude")
        self.ws.create_task(actor="antigravity", task_id="C2",
                            title="Owned by the orchestrator's own worker",
                            description="work", owner="other")

        # Evidence lives under the TRANSPORT actor's report directory.
        home = self.ws.reports_dir / "antigravity"
        home.mkdir(parents=True, exist_ok=True)
        self.report = home / "C1.md"
        self.report.write_text(REPORT_BODY, encoding="utf-8")
        self.artifact = home / "C1.artifact.txt"
        self.artifact.write_bytes(b"measured artifact\n")
        if artifact_bytes is not None:
            with self.artifact.open("r+b") as handle:
                handle.truncate(artifact_bytes)
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
        source = self.repo / "deliverables" / "C1.artifact.txt"
        source.parent.mkdir(parents=True)
        source.write_bytes(self.artifact.read_bytes())
        # Every claim-bearing file must be commit-bound, raw output included.
        (self.repo / "deliverables" / "C1.raw.txt").write_bytes(
            self.raw.read_bytes())
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

    def authorize(self, **over: Any) -> str:
        kwargs: dict[str, Any] = {
            "actor": "antigravity", "task_id": "C1",
            "transport_actor": "antigravity", "remote_url": REMOTE_URL,
            "branch": "delivery", "commit": self.commit,
            "duration_seconds": 300,
        }
        kwargs.update(over)
        return self.ws.authorize_proxy_submission(**kwargs)["proxy_token"]

    def submit(self, token: str, **over: Any) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "actor": "antigravity", "author": "claude", "task_id": "C1",
            "proxy_token": token, "report_path": self.report,
            "manifest_path": self.manifest,
            "provenance_path": self.provenance,
            "source_repository": self.repo,
        }
        kwargs.update(over)
        return self.ws.proxy_submit(**kwargs)


def healthy(ws: Workspace) -> str:
    return str(audit_workspace(ws.root)["healthy"])


# ---------------------------------------------------------------- A
print("########## A. POSITIVE CONTROL - an honest proxy submission ##########")
fx = Fixture()
token = fx.authorize()
submitted = fx.submit(token)
check("the submission is accepted", "'state': 'submitted'",
      f"'state': {submitted['state']!r} attempt={submitted['attempt']}")
check("  authorship is the offline author, not the transport",
      "actor='claude' method='proxy'",
      f"actor={submitted['result']['authorship']['actor']!r} "
      f"method={submitted['result']['authorship']['method']!r}")
check("  transport is recorded separately", "actor='antigravity'",
      f"actor={submitted['result']['transport']['actor']!r}")
check("  the grant is marked consumed", "consumed_by='antigravity'",
      f"consumed_at={submitted['proxy_grant']['consumed_at'] is not None} "
      f"consumed_by={submitted['proxy_grant']['consumed_by']!r}")
check("  and doctor is healthy", "healthy=True", "healthy=" + healthy(fx.ws))

# ---------------------------------------------------------------- B
print("\n########## B. the grant gates ##########")
fx = Fixture()
attempt("submit with no grant at all", "has no proxy authorization",
        lambda: fx.submit("nonexistent-token"))

fx = Fixture()
token = fx.authorize()
attempt("a wrong token", "Proxy authorization token is invalid",
        lambda: fx.submit(token + "x"))

fx = Fixture()
token = fx.authorize(duration_seconds=10)
grant_task = fx.ws.get_task("C1")
attempt("an author who is not the task owner", "is not task owner",
        lambda: fx.submit(token, author="other"))
attempt("the transport submitting as itself",
        "An author must use the normal claim/start/submit path",
        lambda: fx.submit(token, author="antigravity"))

fx = Fixture()
token = fx.authorize()
attempt("a second authorization while one is active",
        "already has an active proxy authorization", fx.authorize)

fx = Fixture()
attempt("a transport that is not the orchestrator",
        "Proxy transport must be the workspace orchestrator",
        lambda: fx.authorize(transport_actor="claude"))
# workspace.py:745 refuses a grant whose task the transport owns. That branch
# is unreachable through the API: the transport must be the orchestrator, and
# an orchestrator cannot be a task owner in the first place.
attempt("can the orchestrator own a task at all?",
        "is not a worker",
        lambda: fx.ws.create_task(actor="antigravity", task_id="C3", title="x",
                                  description="x", owner="antigravity"))

fx = Fixture()
token = fx.authorize()
outside = fx.root / "elsewhere.md"
outside.write_text(REPORT_BODY, encoding="utf-8")
attempt("a report outside the transport's report directory",
        "Proxy report must be under the transport actor's report directory",
        lambda: fx.submit(token, report_path=outside))

fx = Fixture()
token = fx.authorize()
fx.write_provenance(commit="0" * 40)
attempt("a provenance commit that does not exist",
        "Needed a single revision", lambda: fx.submit(token))

fx = Fixture()
token = fx.authorize()
git(fx.repo, "commit", "--allow-empty", "-m", "second")
second = git(fx.repo, "rev-parse", "HEAD")
fx.write_provenance(commit=second)
attempt("a real commit that the grant does not name",
        "differs from the proxy authorization", lambda: fx.submit(token))

print("  replay: consume a grant, then present it again")
fx = Fixture()
token = fx.authorize()
fx.submit(token)
attempt("  the same token a second time",
        "does not match this submission: next_attempt",
        lambda: fx.submit(token))

print("  cross-workspace: both workspaces hold a live grant for C1;")
print("  present workspace A's token to workspace B")
fx_a, fx_b = Fixture(), Fixture()
token_a = fx_a.authorize()
fx_b.authorize()
attempt("  a token minted in another workspace",
        "Proxy authorization token is invalid",
        lambda: fx_b.submit(token_a))

# ---------------------------------------------------------------- C
print("\n########## C. the archival path at workspace.py:1220 ##########")
fx = Fixture()
token = fx.authorize()
submitted = fx.submit(token)
bundle = submitted["result"]["archive"]
check("the bundle is labelled as proxy work", "proxy-worker",
      bundle["bundle_id"])
check("  and filed under the grant's next_attempt", "attempt-001",
      bundle["path"])
for record in bundle["files"]:
    print(f"        {record['kind']:<20} retained={record['retained']} "
          f"size={record['size_bytes']}")
kinds = sorted(r["kind"] for r in bundle["files"])
check("  the provenance manifest is archived alongside the evidence",
      "provenance_manifest", str(kinds))

print("  the normal path lets an over-limit artifact stay external (issue #10).")
print("  does the proxy path?")
fx = Fixture(artifact_bytes=50 * 1024 * 1024 + 1)
token = fx.authorize()
attempt("  an artifact larger than max_evidence_bytes",
        "Git source blob exceeds the proxy verification limit",
        lambda: fx.submit(token))
print("  -> it never reaches archival, so a proxy bundle is always complete:")
check("  external count on the honest proxy bundle", "'external': 0",
      f"'external': {bundle['external']}")

archived = next(Path(r["archive_path"]) for r in bundle["files"]
                if r["kind"] == "provenance_manifest")
recorded = next(r["sha256"] for r in bundle["files"]
                if r["kind"] == "provenance_manifest")
archived.write_text('{"schema_version": 1, "kind": "git"}', encoding="utf-8")
print(f"  archived provenance manifest rewritten")
print(f"        recorded sha = {recorded[:16]}...")
print(f"        on-disk sha  = {sha_of(archived)[:16]}...")
attempt("does the ledger notice?", "accepted", fx.ws.ledger.verify)
check("  does doctor notice?", "healthy=", "healthy=" + healthy(fx.ws))

# ---------------------------------------------------------------- D
print("\n########## D. is transport independence enforced or only recorded? ##########")
fx = Fixture()
token = fx.authorize()
submitted = fx.submit(token)
record = submitted["result"]["transport_independence"]
check("an independent transport is recorded as independent", "True",
      str(record["independent"]))

# The transport must be the orchestrator, so overlap is produced by giving the
# offline author the orchestrator's own control principal and model family.
fx = Fixture(author_principal="google", author_family="google-antigravity")
token = fx.authorize()
submitted = fx.submit(token)
record = submitted["result"]["transport_independence"]
check("an author sharing the orchestrator's principal and family",
      "'state': 'submitted'", f"'state': {submitted['state']!r}")
check("  what does the record say?", "same_control_principal",
      f"independent={record['independent']} reasons={record['reasons']}")

source = Path("/tmp/efo-prov/src")
consumers = subprocess.run(
    ["grep", "-rn", "transport_independence", str(source)],
    capture_output=True, text=True).stdout.strip().splitlines()
print("  every mention of transport_independence in the source tree:")
for line in consumers:
    print(f"        {line.replace(str(source) + '/', '')}")

shutil.rmtree(ROOT, ignore_errors=True)
print(f"\n########## {FAIL} unexpected result(s) ##########")
print("SUBMITTED, not VERIFIED.")
