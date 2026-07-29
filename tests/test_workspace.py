from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.errors import (
    AuthorizationError,
    ConfigurationError,
    EvidenceError,
    IntegrityError,
    LeaseError,
    TransitionError,
)

from .helpers import make_workspace, write_evidence_manifest, write_submission


class WorkspaceLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.workspace = make_workspace(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_task(self, task_id: str = "T1") -> dict:
        return self.workspace.create_task(
            actor="antigravity",
            task_id=task_id,
            title="Implement one tool",
            description="Create and validate a deterministic tool.",
            owner="codex",
        )

    def test_runtime_secrets_and_runs_are_git_ignored(self) -> None:
        self.assertEqual(
            (self.workspace.control_dir / ".gitignore").read_text(encoding="utf-8"),
            "ledger.key\nlocks/\n",
        )
        self.assertEqual(
            (self.workspace.runs_dir / ".gitignore").read_text(encoding="utf-8"),
            "*\n!.gitignore\n",
        )

    def test_full_lifecycle_requires_independent_verification(self) -> None:
        self.create_task()
        claim = self.workspace.claim(actor="codex", task_id="T1")
        token = claim["lease_token"]
        self.assertNotIn(token, str(claim["task"]))
        self.workspace.start(actor="codex", task_id="T1", lease_token=token)
        report, manifest = write_submission(self.workspace, task_id="T1")
        submitted = self.workspace.submit(
            actor="codex",
            task_id="T1",
            lease_token=token,
            report_path=report,
            manifest_path=manifest,
        )
        self.assertEqual(submitted["state"], "submitted")
        archived_report = next(
            item
            for item in submitted["result"]["archive"]["files"]
            if item["kind"] == "report"
        )
        self.assertTrue(archived_report["retained"])
        retained_text = Path(archived_report["archive_path"]).read_text(
            encoding="utf-8"
        )
        report.write_text("overwritten after submission\n", encoding="utf-8")
        self.assertEqual(
            Path(archived_report["archive_path"]).read_text(encoding="utf-8"),
            retained_text,
        )
        with self.assertRaisesRegex(EvidenceError, "verification manifest"):
            self.workspace.verify(
                actor="antigravity",
                task_id="T1",
                decision="accept",
                note="Reproduced.",
            )
        with self.assertRaisesRegex(AuthorizationError, "orchestrator's report"):
            self.workspace.verify(
                actor="antigravity",
                task_id="T1",
                decision="accept",
                note="Reproduced.",
                verification_manifest=manifest,
            )
        verification = write_evidence_manifest(
            self.workspace,
            actor="antigravity",
            task_id="T1",
            suffix="-verification",
        )
        verified = self.workspace.verify(
            actor="antigravity",
            task_id="T1",
            decision="accept",
            note="Independent known-answer test passed.",
            verification_manifest=verification,
        )
        self.assertEqual(verified["state"], "verified")
        self.assertEqual(verified["verification"]["archive"]["external"], 0)
        archived = self.workspace.archive(actor="antigravity", task_id="T1")
        self.assertEqual(archived["state"], "archived")
        self.assertTrue((self.workspace.archive_dir / "T1.json").is_file())
        self.assertTrue(self.workspace.ledger.verify()["valid"])

    def test_wrong_actor_cannot_create_or_claim(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.workspace.create_task(
                actor="codex",
                task_id="T1",
                title="Forbidden",
                description="No.",
                owner="codex",
            )
        self.create_task()
        with self.assertRaises(AuthorizationError):
            self.workspace.claim(actor="claude", task_id="T1")

    def test_invalid_lease_token_fails(self) -> None:
        self.create_task()
        self.workspace.claim(actor="codex", task_id="T1")
        with self.assertRaises(LeaseError):
            self.workspace.start(
                actor="codex",
                task_id="T1",
                lease_token="not-the-token",
            )

    def test_prerequisite_must_be_verified(self) -> None:
        self.create_task("T1")
        self.workspace.create_task(
            actor="antigravity",
            task_id="T2",
            title="Dependent",
            description="Wait for T1.",
            owner="claude",
            prerequisites=["T1"],
        )
        with self.assertRaisesRegex(TransitionError, "unverified prerequisites"):
            self.workspace.claim(actor="claude", task_id="T2")

    def test_idempotency_key_returns_existing_task(self) -> None:
        first = self.workspace.create_task(
            actor="antigravity",
            task_id="T1",
            title="First",
            description="First.",
            owner="codex",
            idempotency_key="stable-key",
        )
        second = self.workspace.create_task(
            actor="antigravity",
            task_id="T1",
            title="First",
            description="First.",
            owner="codex",
            idempotency_key="stable-key",
        )
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(second["title"], "First")

    def test_expired_lease_is_blocked_not_silently_requeued(self) -> None:
        self.create_task()
        self.workspace.claim(actor="codex", task_id="T1", lease_seconds=10)
        recovered = self.workspace.recover_expired(
            actor="antigravity",
            now="2999-01-01T00:00:00Z",
        )
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["state"], "blocked")
        self.assertIn("manual requeue", recovered[0]["blocked_reason"])

    def test_expired_running_lease_retains_lock_until_termination_confirmed(
        self,
    ) -> None:
        self.create_task()
        claimed = self.workspace.claim(
            actor="codex",
            task_id="T1",
            lease_seconds=10,
        )
        self.workspace.start(
            actor="codex",
            task_id="T1",
            lease_token=claimed["lease_token"],
        )
        recovered = self.workspace.recover_expired(
            actor="antigravity",
            now="2999-01-01T00:00:00Z",
        )
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["state"], "revoking")
        self.assertIsNotNone(recovered[0]["lease"])
        self.assertIn("termination must be confirmed", recovered[0]["blocked_reason"])

    def test_projection_loss_is_detected_and_repairable(self) -> None:
        self.create_task()
        self.workspace._task_path("T1").unlink()
        with self.assertRaises(IntegrityError):
            self.workspace.audit_projections()
        result = self.workspace.repair_projections(actor="antigravity")
        self.assertEqual(result["repaired"], ["T1"])
        self.assertEqual(self.workspace.get_task("T1")["state"], "pending")

    def test_projection_tampering_blocks_the_next_transition(self) -> None:
        self.create_task()
        path = self.workspace._task_path("T1")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["permissions"]["performance_metrics"] = True
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(IntegrityError, "differs from the signed ledger"):
            self.workspace.claim(actor="codex", task_id="T1")

    def test_configuration_tampering_is_detected_on_open(self) -> None:
        config_path = self.workspace.config_path
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        payload["orchestrator"] = "codex"
        config_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(IntegrityError, "configuration differs"):
            type(self.workspace)(self.root)

    def test_agent_registration_tampering_is_detected(self) -> None:
        path = self.workspace._agent_path("codex")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["role"] = "verifier"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(IntegrityError, "registration differs"):
            self.workspace.get_agent("codex")

    def test_same_idempotency_key_cannot_create_a_second_task(self) -> None:
        first = self.workspace.create_task(
            actor="antigravity",
            task_id="T1",
            title="Original",
            description="One task.",
            owner="codex",
            idempotency_key="one-operation",
        )
        with self.assertRaisesRegex(ConfigurationError, "immutable task contract"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="T2",
                title="Accidental duplicate",
                description="Must not resolve to unrelated work.",
                owner="claude",
                idempotency_key="one-operation",
            )
        self.assertEqual(first["id"], "T1")
        self.assertFalse(self.workspace._task_path("T2").exists())


if __name__ == "__main__":
    unittest.main()
