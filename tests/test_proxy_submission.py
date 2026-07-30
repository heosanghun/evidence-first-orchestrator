from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.errors import (
    AuthorizationError,
    ConfigurationError,
    EvidenceError,
    TransitionError,
)
from evidence_orchestrator.workspace import Workspace

from .helpers import make_workspace, write_evidence_manifest, write_submission


def run_git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


class ProxySubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.fail("git is required; a skipped provenance test is not a pass")
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.workspace = make_workspace(root / "workspace")
        self.workspace.create_task(
            actor="antigravity",
            task_id="C1",
            title="Externally delivered task",
            description="Exercise transparent proxy submission.",
            owner="claude",
        )
        self.report, self.manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="C1",
        )
        manifest_payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.artifact = (
            self.manifest.parent / manifest_payload["artifacts"][0]["path"]
        ).resolve()
        self.artifact.write_bytes(
            self.artifact.read_bytes().replace(b"\r\n", b"\n")
        )
        manifest_payload["artifacts"][0]["sha256"] = hashlib.sha256(
            self.artifact.read_bytes()
        ).hexdigest()
        self.manifest.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.repository = root / "delivery"
        self.repository.mkdir()
        run_git(self.repository, "init", "-b", "delivery")
        run_git(self.repository, "config", "user.name", "Claude Delivery")
        run_git(
            self.repository,
            "config",
            "user.email",
            "claude-delivery@example.invalid",
        )
        run_git(self.repository, "config", "core.autocrlf", "false")
        self.remote_url = "https://example.invalid/efo-delivery.git"
        run_git(self.repository, "remote", "add", "origin", self.remote_url)
        source = self.repository / "deliverables" / "C1.artifact.txt"
        source.parent.mkdir(parents=True)
        source.write_bytes(self.artifact.read_bytes())
        run_git(self.repository, "add", "deliverables/C1.artifact.txt")
        run_git(self.repository, "commit", "-m", "Deliver C1 evidence")
        self.commit = run_git(self.repository, "rev-parse", "HEAD")
        self.provenance = self.manifest.parent / "C1.provenance.json"
        self.write_provenance()
        authorization = self.workspace.authorize_proxy_submission(
            actor="antigravity",
            task_id="C1",
            transport_actor="antigravity",
            remote_url=self.remote_url,
            branch="delivery",
            commit=self.commit,
            duration_seconds=300,
        )
        self.proxy_token = authorization["proxy_token"]

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_provenance(self, **updates: object) -> None:
        payload: dict[str, object] = {
            "schema_version": 1,
            "kind": "git",
            "author": "claude",
            "remote_name": "origin",
            "remote_url": self.remote_url,
            "branch": "delivery",
            "commit": self.commit,
            "files": [
                {
                    "source_path": "deliverables/C1.artifact.txt",
                    "submitted_path": self.artifact.name,
                }
            ],
        }
        payload.update(updates)
        self.provenance.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def proxy_submit(self) -> dict:
        return self.workspace.proxy_submit(
            actor="antigravity",
            author="claude",
            task_id="C1",
            proxy_token=self.proxy_token,
            report_path=self.report,
            manifest_path=self.manifest,
            provenance_path=self.provenance,
            source_repository=self.repository,
        )

    def test_proxy_submission_separates_author_and_transport(self) -> None:
        submitted = self.proxy_submit()
        self.assertEqual(submitted["state"], "submitted")
        self.assertEqual(submitted["attempt"], 1)
        self.assertEqual(submitted["result"]["authorship"]["actor"], "claude")
        self.assertEqual(
            submitted["result"]["transport"]["actor"],
            "antigravity",
        )
        self.assertTrue(submitted["result"]["provenance"]["byte_exact"])
        self.assertEqual(submitted["result"]["provenance"]["commit"], self.commit)
        self.assertEqual(
            submitted["proxy_grant"]["consumed_by"],
            "antigravity",
        )
        self.assertIsNotNone(submitted["proxy_grant"]["consumed_at"])
        retained_kinds = {
            item["kind"]
            for item in submitted["result"]["archive"]["files"]
            if item["retained"]
        }
        self.assertIn("provenance_manifest", retained_kinds)

        event = self.workspace.ledger.read()[-1]
        self.assertEqual(event["actor"], "antigravity")
        self.assertEqual(event["action"], "task.proxy_submitted")
        self.assertEqual(event["payload"]["details"]["author_actor"], "claude")
        self.assertEqual(
            event["payload"]["details"]["transport_actor"],
            "antigravity",
        )
        reopened = Workspace(self.workspace.root)
        self.assertEqual(reopened.get_task("C1")["state"], "submitted")

    def test_transport_actor_may_verify_only_when_independent_of_author(self) -> None:
        self.proxy_submit()
        verification = write_evidence_manifest(
            self.workspace,
            actor="antigravity",
            task_id="C1",
            suffix="-verification",
        )
        verified = self.workspace.verify(
            actor="antigravity",
            task_id="C1",
            decision="accept",
            note="Transport was not authorship; evidence was independently rerun.",
            verification_manifest=verification,
        )
        self.assertEqual(verified["state"], "verified")
        self.assertTrue(verified["verification"]["transport_overlap"])
        self.assertTrue(
            verified["verification"]["independence"]["independent"]
        )
        audit = self.workspace.audit_independence()
        self.assertEqual(audit["checked"], 1)
        self.assertTrue(audit["findings"][0]["independent"])

    def test_transport_alias_is_recorded_as_overlap(self) -> None:
        self.proxy_submit()
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="antigravity-alias",
            role="verifier",
            alias_of="antigravity",
        )
        verification = write_evidence_manifest(
            self.workspace,
            actor="antigravity-alias",
            task_id="C1",
            suffix="-alias-verification",
        )
        verified = self.workspace.verify(
            actor="antigravity-alias",
            task_id="C1",
            decision="accept",
            note="Alias transport overlap must remain visible.",
            verification_manifest=verification,
        )
        self.assertTrue(verified["verification"]["transport_overlap"])
        relation = verified["verification"]["transport_independence"]
        self.assertFalse(relation["independent"])
        self.assertIn("same_control_principal", relation["reasons"])

    def test_non_orchestrator_cannot_proxy_for_another_agent(self) -> None:
        with self.assertRaisesRegex(AuthorizationError, "Only orchestrator"):
            self.workspace.proxy_submit(
                actor="codex",
                author="claude",
                task_id="C1",
                proxy_token=self.proxy_token,
                report_path=self.report,
                manifest_path=self.manifest,
                provenance_path=self.provenance,
                source_repository=self.repository,
            )

    def test_non_orchestrator_cannot_issue_proxy_grant(self) -> None:
        other = make_workspace(Path(self.temp.name) / "other-workspace")
        other.create_task(
            actor="antigravity",
            task_id="C2",
            title="No forged grant",
            description="Only the orchestrator may authorize transport.",
            owner="claude",
        )
        with self.assertRaisesRegex(AuthorizationError, "Only orchestrator"):
            other.authorize_proxy_submission(
                actor="codex",
                task_id="C2",
                transport_actor="antigravity",
                remote_url=self.remote_url,
                branch="delivery",
                commit=self.commit,
            )

    def test_proxy_grant_rejects_unusable_non_orchestrator_transport(self) -> None:
        other = make_workspace(Path(self.temp.name) / "transport-workspace")
        other.create_task(
            actor="antigravity",
            task_id="C2",
            title="No dead proxy grant",
            description="Reject a transport that cannot call proxy_submit.",
            owner="claude",
        )
        with self.assertRaisesRegex(
            AuthorizationError,
            "transport must be the workspace orchestrator",
        ):
            other.authorize_proxy_submission(
                actor="antigravity",
                task_id="C2",
                transport_actor="codex",
                remote_url=self.remote_url,
                branch="delivery",
                commit=self.commit,
            )
        self.assertIsNone(other.get_task("C2").get("proxy_grant"))

    def test_active_proxy_grant_cannot_be_replaced(self) -> None:
        with self.assertRaisesRegex(
            TransitionError,
            "active proxy authorization",
        ):
            self.workspace.authorize_proxy_submission(
                actor="antigravity",
                task_id="C1",
                transport_actor="antigravity",
                remote_url=self.remote_url,
                branch="delivery",
                commit=self.commit,
            )

    def test_task_owner_cannot_be_forged(self) -> None:
        self.write_provenance(author="codex")
        with self.assertRaisesRegex(AuthorizationError, "not task owner"):
            self.workspace.proxy_submit(
                actor="antigravity",
                author="codex",
                task_id="C1",
                proxy_token=self.proxy_token,
                report_path=self.report,
                manifest_path=self.manifest,
                provenance_path=self.provenance,
                source_repository=self.repository,
            )

    def test_normal_submit_still_requires_running_state(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            actor="claude",
            task_id="C1",
            suffix="-normal",
        )
        with self.assertRaisesRegex(TransitionError, "must be running"):
            self.workspace.submit(
                actor="claude",
                task_id="C1",
                lease_token="not-a-lease",
                report_path=report,
                manifest_path=manifest,
            )

    def test_crlf_transport_mutation_is_rejected(self) -> None:
        self.artifact.write_bytes(
            self.artifact.read_bytes().replace(b"\n", b"\r\n")
        )
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["artifacts"][0]["sha256"] = hashlib.sha256(
            self.artifact.read_bytes()
        ).hexdigest()
        self.manifest.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(EvidenceError, "newline or transport mutation"):
            self.proxy_submit()

    def test_invalid_proxy_token_is_rejected(self) -> None:
        original = self.proxy_token
        self.proxy_token = "invalid-token"
        try:
            with self.assertRaisesRegex(AuthorizationError, "token is invalid"):
                self.proxy_submit()
        finally:
            self.proxy_token = original

    def test_remote_mismatch_is_rejected(self) -> None:
        self.write_provenance(
            remote_url="https://example.invalid/forged.git"
        )
        with self.assertRaisesRegex(EvidenceError, "Git remote mismatch"):
            self.proxy_submit()

    def test_branch_must_match_preregistered_grant(self) -> None:
        run_git(self.repository, "branch", "other-delivery")
        self.write_provenance(branch="other-delivery")
        with self.assertRaisesRegex(
            AuthorizationError,
            "branch differs from the proxy authorization",
        ):
            self.proxy_submit()

    def test_commit_must_match_preregistered_grant(self) -> None:
        extra = self.repository / "unrelated.txt"
        extra.write_text("new branch state\n", encoding="utf-8")
        run_git(self.repository, "add", "unrelated.txt")
        run_git(self.repository, "commit", "-m", "Advance delivery branch")
        later_commit = run_git(self.repository, "rev-parse", "HEAD")
        self.write_provenance(commit=later_commit)
        with self.assertRaisesRegex(
            AuthorizationError,
            "commit differs from the proxy authorization",
        ):
            self.proxy_submit()

    def test_unbound_claim_evidence_is_rejected(self) -> None:
        self.write_provenance(files=[])
        with self.assertRaisesRegex(EvidenceError, "at least one source file"):
            self.proxy_submit()

    def test_source_path_cannot_escape_repository(self) -> None:
        self.write_provenance(
            files=[
                {
                    "source_path": "../C1.artifact.txt",
                    "submitted_path": self.artifact.name,
                }
            ]
        )
        with self.assertRaisesRegex(
            ConfigurationError,
            "must not escape the repository",
        ):
            self.proxy_submit()

    def test_remote_url_cannot_embed_credentials(self) -> None:
        self.write_provenance(
            remote_url="https://secret@example.invalid/repo.git"
        )
        with self.assertRaisesRegex(
            AuthorizationError,
            "embedded credentials",
        ):
            self.proxy_submit()


if __name__ == "__main__":
    unittest.main()
