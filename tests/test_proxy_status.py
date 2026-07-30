from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evidence_orchestrator.errors import (
    AuthorizationError,
    ConfigurationError,
    TransitionError,
)
from evidence_orchestrator.cli import build_parser
from evidence_orchestrator.workspace import Workspace

from .helpers import make_workspace


class ProxyStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = make_workspace(Path(self.temp.name) / "workspace")
        self.workspace.create_task(
            actor="antigravity",
            task_id="C1",
            title="Offline implementation",
            description="Track transport observations without a worker lease.",
            owner="claude",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def report(
        self,
        phase: str,
        *,
        actor: str = "antigravity",
        author: str = "claude",
        reference: str = "dispatch-001",
        note: str = "Observed by the transport.",
    ) -> dict:
        return self.workspace.report_proxy_status(
            actor=actor,
            author=author,
            task_id="C1",
            phase=phase,
            reference=reference,
            note=note,
        )

    def test_status_is_signed_without_claim_lease_or_state_transition(self) -> None:
        original = self.workspace.get_task("C1")
        reported = self.report("dispatched")

        self.assertEqual(reported["state"], "pending")
        self.assertIsNone(reported["lease"])
        self.assertEqual(reported["attempt"], 0)
        self.assertEqual(reported["revision"], original["revision"] + 1)
        status = reported["external_status"]
        self.assertEqual(status["phase"], "dispatched")
        self.assertEqual(status["reference"], "dispatch-001")
        self.assertEqual(status["reported_by"], "antigravity")
        self.assertEqual(status["author"], "claude")
        self.assertEqual(status["assertion"], "transport_observation")
        self.assertEqual(
            status["transport_identity"]["control_principal"],
            "antigravity-control",
        )
        self.assertEqual(
            status["author_identity"]["control_principal"],
            "claude",
        )

        event = self.workspace.ledger.read()[-1]
        self.assertEqual(event["action"], "task.proxy_status_reported")
        self.assertEqual(event["actor"], "antigravity")
        self.assertEqual(event["payload"]["task"]["state"], "pending")
        self.assertNotIn("lease_token", str(event))
        self.assertTrue(self.workspace.ledger.verify()["valid"])
        self.assertEqual(
            self.workspace.ledger.projected_tasks()["C1"],
            {
                key: value
                for key, value in self.workspace.get_task("C1").items()
                if key != "last_event_hash"
            },
        )

    def test_phase_order_reference_and_block_recovery_are_fail_closed(self) -> None:
        with self.assertRaisesRegex(TransitionError, "first.*dispatched"):
            self.report("working")
        self.report("dispatched")
        self.report("working")
        self.report("reviewing")
        self.report("blocked")
        resumed = self.report("working")
        self.assertEqual(resumed["external_status"]["phase"], "working")

        with self.assertRaisesRegex(TransitionError, "cannot regress"):
            self.report("dispatched")
        with self.assertRaisesRegex(AuthorizationError, "cannot change"):
            self.report("reviewing", reference="dispatch-002")

    def test_ready_can_be_blocked_and_resume_as_working(self) -> None:
        self.report("dispatched")
        self.report("working")
        self.report("reviewing")
        self.report("ready")
        blocked = self.report("blocked")
        self.assertEqual(blocked["external_status"]["phase"], "blocked")
        resumed = self.report("working")
        self.assertEqual(resumed["external_status"]["phase"], "working")

    def test_cli_parser_routes_proxy_status_arguments(self) -> None:
        args = build_parser().parse_args(
            [
                "task",
                "proxy-status",
                "workspace",
                "--actor",
                "antigravity",
                "--author",
                "claude",
                "--id",
                "C1",
                "--phase",
                "working",
                "--reference",
                "dispatch-001",
                "--note",
                "Observed by transport.",
            ]
        )
        self.assertEqual(args.task_command, "proxy-status")
        self.assertEqual(args.actor, "antigravity")
        self.assertEqual(args.author, "claude")
        self.assertEqual(args.task_id, "C1")
        self.assertEqual(args.phase, "working")
        self.assertEqual(args.reference, "dispatch-001")
        self.assertEqual(args.note, "Observed by transport.")

    def test_authorization_owner_phase_and_text_validation(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.report("dispatched", actor="codex")
        with self.assertRaisesRegex(AuthorizationError, "not task owner"):
            self.report("dispatched", author="codex")
        with self.assertRaises(ConfigurationError):
            self.report("unknown")
        with self.assertRaises(ConfigurationError):
            self.report("dispatched", reference="")
        with self.assertRaises(ConfigurationError):
            self.report("dispatched", note="")
        with self.assertRaises(ConfigurationError):
            self.report("dispatched", reference=None)  # type: ignore[arg-type]
        with self.assertRaises(ConfigurationError):
            self.report("dispatched", note=None)  # type: ignore[arg-type]

    def test_ready_does_not_replace_proxy_submission_requirements(self) -> None:
        self.report("dispatched")
        self.report("working")
        self.report("reviewing")
        ready = self.report("ready")
        self.assertEqual(ready["state"], "pending")
        self.assertIsNone(ready.get("proxy_grant"))

        authorization = self.workspace.authorize_proxy_submission(
            actor="antigravity",
            task_id="C1",
            transport_actor="antigravity",
            remote_url="https://example.invalid/delivery.git",
            branch="delivery",
            commit="1" * 40,
            duration_seconds=300,
        )
        self.assertEqual(authorization["task"]["state"], "pending")
        self.assertEqual(
            authorization["task"]["external_status"]["phase"],
            "ready",
        )
        self.assertIn("proxy_token", authorization)

    def test_status_rejected_after_canonical_state_changes(self) -> None:
        claim = self.workspace.claim(actor="claude", task_id="C1")
        self.workspace.start(
            actor="claude",
            task_id="C1",
            lease_token=claim["lease_token"],
        )
        with self.assertRaisesRegex(TransitionError, "pending task"):
            self.report("dispatched")

    def test_ready_pending_task_can_follow_existing_proxy_submit_path(self) -> None:
        self.report("dispatched")
        self.report("working")
        self.report("reviewing")
        self.report("ready")
        authorization = self.workspace.authorize_proxy_submission(
            actor="antigravity",
            task_id="C1",
            transport_actor="antigravity",
            remote_url="https://example.invalid/delivery.git",
            branch="delivery",
            commit="2" * 40,
            duration_seconds=300,
        )
        report = self.workspace.reports_dir / "antigravity" / "C1.md"
        manifest = self.workspace.reports_dir / "antigravity" / "C1.json"
        provenance = self.workspace.reports_dir / "antigravity" / "provenance.json"
        source_repository = Path(self.temp.name) / "source"
        report.write_text("report", encoding="utf-8")
        manifest.write_text("{}", encoding="utf-8")
        provenance.write_text("{}", encoding="utf-8")
        source_repository.mkdir()
        evidence = {
            "report": {"path": str(report), "sha256": "3" * 64},
            "manifest": {"path": str(manifest), "sha256": "4" * 64},
        }
        provenance_result = {
            "path": str(provenance),
            "sha256": "5" * 64,
            "remote_url": "https://example.invalid/delivery.git",
            "branch": "delivery",
            "commit": "2" * 40,
            "byte_exact": True,
        }
        with (
            patch(
                "evidence_orchestrator.workspace.validate_submission",
                return_value=evidence,
            ),
            patch(
                "evidence_orchestrator.workspace.validate_git_provenance",
                return_value=provenance_result,
            ),
            patch(
                "evidence_orchestrator.workspace.archive_evidence_bundle",
                return_value={"retained": 0, "external": 0},
            ),
        ):
            submitted = self.workspace.proxy_submit(
                actor="antigravity",
                author="claude",
                task_id="C1",
                proxy_token=authorization["proxy_token"],
                report_path=report,
                manifest_path=manifest,
                provenance_path=provenance,
                source_repository=source_repository,
            )
        self.assertEqual(submitted["state"], "submitted")
        self.assertEqual(submitted["external_status"]["phase"], "ready")
        self.assertEqual(submitted["result"]["authorship"]["actor"], "claude")
        self.assertEqual(
            submitted["result"]["transport"]["actor"],
            "antigravity",
        )


if __name__ == "__main__":
    unittest.main()
