from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from evidence_orchestrator import Workspace, __version__
from evidence_orchestrator.doctor import audit_workspace
from evidence_orchestrator.errors import (
    AuthorizationError,
    ConfigurationError,
    EvidenceError,
    IntegrityError,
    TransitionError,
)
from evidence_orchestrator.identity import evaluate_independence
from evidence_orchestrator.provenance import verify_git_delivery

from .helpers import make_workspace, write_evidence_manifest, write_submission

V01_WHEEL = (
    Path(__file__).parent
    / "fixtures"
    / "evidence_first_orchestrator-0.1.0-py3-none-any.whl"
)
V01_WHEEL_SHA256 = "18ed72c3f2ddf38a9a18d435032095cfbc074b2e21b9397d96e4a76b103b2354"


def _run_v01(code: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the preserved v0.1 wheel without importing current source code."""

    environment = {
        **os.environ,
        "PYTHONPATH": str(V01_WHEEL),
    }
    return subprocess.run(
        [sys.executable, "-c", code, *arguments],
        check=check,
        capture_output=True,
        text=True,
        env=environment,
        cwd=V01_WHEEL.parent,
    )


def make_v01_workspace(root: Path) -> Workspace:
    """Create a signed workspace with the preserved v0.1 runtime."""

    _run_v01(
        "\n".join(
            [
                "import sys",
                "from evidence_orchestrator import Workspace",
                "workspace = Workspace.initialize(",
                "    sys.argv[1],",
                "    name='v0.1 fixture',",
                "    orchestrator='antigravity',",
                "    preset='antigravity-codex-claude',",
                ")",
                "workspace.create_task(",
                "    actor='antigravity',",
                "    task_id='LEGACY',",
                "    title='Legacy task',",
                "    description='Exercise v0.1 compatibility.',",
                "    owner='codex',",
                ")",
            ]
        ),
        str(root),
    )
    return Workspace(root)


class MetaOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.workspace = make_workspace(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_runtime_version_matches_v2_release(self) -> None:
        self.assertEqual(__version__, "0.2.0")

    def test_preserved_v01_wheel_matches_release_hash(self) -> None:
        self.assertTrue(V01_WHEEL.is_file())
        self.assertEqual(
            hashlib.sha256(V01_WHEEL.read_bytes()).hexdigest(),
            V01_WHEEL_SHA256,
        )

    def test_v02_reads_and_transitions_a_v01_workspace(self) -> None:
        legacy = make_v01_workspace(Path(self.temp.name) / "v01-workspace")
        self.assertNotIn("identity", legacy.get_agent("codex"))
        claimed = legacy.claim(actor="codex", task_id="LEGACY")
        token = claimed["lease_token"]
        running = legacy.start(
            actor="codex",
            task_id="LEGACY",
            lease_token=token,
        )
        self.assertEqual(running["state"], "running")
        revoking = legacy.block(
            actor="codex",
            task_id="LEGACY",
            lease_token=token,
            reason="Compatibility smoke completed.",
        )
        self.assertEqual(revoking["state"], "revoking")
        blocked = legacy.confirm_revocation(
            actor="antigravity",
            task_id="LEGACY",
            termination_evidence="Compatibility process inventory is empty.",
        )
        self.assertEqual(blocked["state"], "blocked")

    def test_v01_agent_check_fails_closed_after_v02_handoff(self) -> None:
        legacy = make_v01_workspace(
            Path(self.temp.name) / "v01-handoff-workspace"
        )
        legacy.transfer_orchestrator(
            actor="antigravity",
            target="codex",
            reason="Exercise the legacy client guard.",
        )
        completed = _run_v01(
            "\n".join(
                [
                    "import sys",
                    "from evidence_orchestrator import Workspace",
                    "Workspace(sys.argv[1]).get_agent('codex')",
                ]
            ),
            str(legacy.root),
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(
            "differs from the signed ledger",
            completed.stderr,
        )

    def test_meta_four_agent_preset_declares_specialized_roles(self) -> None:
        workspace = Workspace.initialize(
            Path(self.temp.name) / "meta-preset",
            name="meta-preset",
            orchestrator="antigravity",
            preset="meta-4-agent",
        )
        agents = {agent["id"]: agent for agent in workspace.list_agents()}
        self.assertEqual(
            set(agents),
            {"antigravity", "codex", "claude-a", "claude-b"},
        )
        self.assertEqual(agents["claude-b"]["role"], "verifier")
        self.assertIn("meta-orchestrate", agents["codex"]["capabilities"])
        self.assertIn("experiment-ops", agents["antigravity"]["capabilities"])
        self.assertEqual(
            agents["antigravity"]["identity"]["model_family"],
            "unknown",
        )

    def test_orchestrator_can_sign_command_delivery_for_existing_agent(self) -> None:
        record = self.workspace.configure_agent_delivery(
            actor="antigravity",
            agent_id="codex",
            mode="command",
            command=[
                sys.executable,
                "-c",
                "print('consume the EFO task from stdin')",
            ],
            prompt_stdin=True,
        )
        self.assertEqual(record["mode"], "command")
        self.assertTrue(record["prompt_stdin"])
        self.assertEqual(
            self.workspace.get_agent("codex")["command"],
            record["command"],
        )
        self.assertEqual(
            self.workspace.ledger.read()[-1]["action"],
            "agent.updated",
        )

    def test_delivery_change_is_rejected_while_agent_owns_active_task(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="ACTIVE-DELIVERY",
            title="Hold delivery stable",
            description="A claimed task freezes the delivery configuration.",
            owner="codex",
        )
        self.workspace.claim(actor="codex", task_id="ACTIVE-DELIVERY")
        with self.assertRaisesRegex(
            ConfigurationError,
            "owns active tasks: ACTIVE-DELIVERY",
        ):
            self.workspace.configure_agent_delivery(
                actor="antigravity",
                agent_id="codex",
                mode="command",
                command=[sys.executable, "-c", "print('unsafe update')"],
                prompt_stdin=True,
            )

    def test_manual_delivery_rejects_prompt_stdin(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationError,
            "Manual-mode delivery",
        ):
            self.workspace.configure_agent_delivery(
                actor="antigravity",
                agent_id="codex",
                mode="manual",
                prompt_stdin=True,
            )

    def _add_claude_pair(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="claude-a",
            role="worker",
            controller_id="claude-a",
            provider="anthropic",
            model_family="claude-code",
            capabilities=["code"],
        )
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="claude-b",
            role="verifier",
            controller_id="claude-b",
            provider="anthropic",
            model_family="claude-code",
            capabilities=["review", "verify"],
        )
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="codex-verifier",
            role="verifier",
            controller_id="codex-verifier",
            provider="openai",
            model_family="codex",
            capabilities=["review", "verify"],
        )

    def _submit(
        self,
        *,
        task_id: str,
        actor: str,
    ) -> None:
        claim = self.workspace.claim(actor=actor, task_id=task_id)
        token = claim["lease_token"]
        self.workspace.start(actor=actor, task_id=task_id, lease_token=token)
        report, manifest = write_submission(
            self.workspace,
            actor=actor,
            task_id=task_id,
        )
        self.workspace.submit(
            actor=actor,
            task_id=task_id,
            lease_token=token,
            report_path=report,
            manifest_path=manifest,
        )

    def test_known_independence_cases(self) -> None:
        cases = [
            (
                {
                    "id": "antigravity-worker",
                    "controller_id": "antigravity",
                    "model_family": "claude-code",
                },
                {
                    "id": "antigravity",
                    "controller_id": "antigravity",
                    "model_family": "claude-code",
                },
                False,
            ),
            (
                {
                    "id": "claude-a",
                    "controller_id": "claude-a",
                    "model_family": "claude-code",
                },
                {
                    "id": "claude-b",
                    "controller_id": "claude-b",
                    "model_family": "claude-code",
                },
                False,
            ),
            (
                {
                    "id": "codex",
                    "controller_id": "codex",
                    "model_family": "codex",
                },
                {
                    "id": "claude-a",
                    "controller_id": "claude-a",
                    "model_family": "claude-code",
                },
                True,
            ),
            (
                {
                    "id": "same",
                    "controller_id": "one",
                    "model_family": "one",
                },
                {
                    "id": "same",
                    "controller_id": "two",
                    "model_family": "two",
                },
                False,
            ),
        ]
        for author, verifier, expected in cases:
            with self.subTest(author=author["id"], verifier=verifier["id"]):
                result = evaluate_independence(
                    author=author,
                    verifier=verifier,
                    dimensions=["actor", "controller", "model_family"],
                )
                self.assertEqual(result["independent"], expected)

    def test_same_model_verifier_is_rejected_but_codex_verifier_passes(self) -> None:
        self._add_claude_pair()
        self.workspace.create_task(
            actor="antigravity",
            task_id="CROSS",
            title="Cross-model verification",
            description="Exercise strict verifier independence.",
            owner="claude-a",
            required_capabilities=["code"],
            verification_policy={
                "required_attestations": 0,
                "allowed_verifiers": ["claude-b", "codex-verifier"],
                "independence_dimensions": [
                    "actor",
                    "controller",
                    "model_family",
                ],
            },
        )
        self._submit(task_id="CROSS", actor="claude-a")

        claude_manifest = write_evidence_manifest(
            self.workspace,
            actor="claude-b",
            task_id="CROSS",
            suffix="-verify",
        )
        with self.assertRaisesRegex(AuthorizationError, "model_family matches"):
            self.workspace.verify(
                actor="claude-b",
                task_id="CROSS",
                decision="accept",
                note="Same-family review.",
                verification_manifest=claude_manifest,
            )

        codex_manifest = write_evidence_manifest(
            self.workspace,
            actor="codex-verifier",
            task_id="CROSS",
            suffix="-verify",
        )
        verified = self.workspace.verify(
            actor="codex-verifier",
            task_id="CROSS",
            decision="accept",
            note="Independent reproduction.",
            verification_manifest=codex_manifest,
        )
        self.assertEqual(verified["state"], "verified")

    def test_submission_freezes_author_identity_before_profile_changes(self) -> None:
        self._add_claude_pair()
        self.workspace.create_task(
            actor="antigravity",
            task_id="FROZEN-AUTHOR",
            title="Frozen author identity",
            description="Post-submission updates must not change independence.",
            owner="claude-a",
            required_capabilities=["code"],
            verification_policy={
                "required_attestations": 0,
                "allowed_verifiers": ["codex-verifier"],
                "independence_dimensions": [
                    "actor",
                    "controller",
                    "model_family",
                ],
            },
        )
        self._submit(task_id="FROZEN-AUTHOR", actor="claude-a")
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="claude-a",
            controller_id="codex-verifier",
            provider="other",
            model_family="codex",
            capabilities=["code"],
        )
        manifest = write_evidence_manifest(
            self.workspace,
            actor="codex-verifier",
            task_id="FROZEN-AUTHOR",
            suffix="-verify",
        )
        verified = self.workspace.verify(
            actor="codex-verifier",
            task_id="FROZEN-AUTHOR",
            decision="accept",
            note="Frozen submission identity remains authoritative.",
            verification_manifest=manifest,
        )
        self.assertEqual(verified["state"], "verified")
        submission = self.workspace.get_task("FROZEN-AUTHOR")["result"]["submission"]
        self.assertEqual(
            submission["author_profile"]["model_family"],
            "claude-code",
        )

    def test_legacy_alias_approval_is_found_by_retrospective_audit(self) -> None:
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="antigravity",
            controller_id="antigravity",
            provider="anthropic",
            model_family="claude-code",
            capabilities=["orchestrate", "proxy_submit", "verify"],
        )
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="antigravity-worker",
            role="worker",
            controller_id="antigravity",
            provider="anthropic",
            model_family="claude-code",
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="GATE-PROBE",
            title="Legacy alias probe",
            description="Legacy actor-only policy.",
            owner="antigravity-worker",
        )
        self._submit(task_id="GATE-PROBE", actor="antigravity-worker")
        manifest = write_evidence_manifest(
            self.workspace,
            actor="antigravity",
            task_id="GATE-PROBE",
            suffix="-verify",
        )
        self.workspace.verify(
            actor="antigravity",
            task_id="GATE-PROBE",
            decision="accept",
            note="Legacy actor-only verification.",
            verification_manifest=manifest,
        )
        audit = self.workspace.audit_independence()
        record = next(
            item for item in audit["records"] if item["task_id"] == "GATE-PROBE"
        )
        self.assertEqual(record["status"], "non_independent")
        self.assertIn(
            "controller matches (antigravity)",
            record["result"]["reasons"],
        )
        self.assertEqual(audit["summary"]["action_required"], 1)
        invalidated = self.workspace.invalidate(
            actor="antigravity",
            task_id="GATE-PROBE",
            reason="Retrospective audit found a controller alias approval.",
        )
        self.assertEqual(invalidated["state"], "invalidated")
        self.assertEqual(
            self.workspace.audit_independence()["summary"]["action_required"],
            0,
        )
        self.workspace.requeue(
            actor="antigravity",
            task_id="GATE-PROBE",
            reason="Repeat the work under the corrected policy.",
        )
        after_requeue = self.workspace.audit_independence()
        old_attempt = next(
            item
            for item in after_requeue["records"]
            if item["task_id"] == "GATE-PROBE" and item["attempt"] == 1
        )
        self.assertTrue(old_attempt["quarantined"])
        self.assertEqual(old_attempt["status"], "non_independent")
        self.assertEqual(after_requeue["summary"]["action_required"], 0)

    def test_signed_orchestrator_transfer_changes_authority(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationError,
            "Transfer orchestration",
        ):
            self.workspace.update_agent(
                actor="antigravity",
                agent_id="antigravity",
                controller_id="antigravity",
                provider="anthropic",
                model_family="claude-code",
                capabilities=["orchestrate", "proxy_submit", "verify"],
                active=False,
            )
        transferred = self.workspace.transfer_orchestrator(
            actor="antigravity",
            target="codex",
            reason="User appointed Codex as the meta-orchestrator.",
        )
        self.assertEqual(transferred["to"], "codex")
        self.assertEqual(self.workspace.orchestrator, "codex")
        self.assertEqual(self.workspace.get_agent("antigravity")["governance_epoch"], 1)
        self.assertEqual(self.workspace.get_agent("codex")["governance_epoch"], 1)
        self.assertEqual(
            [
                event["action"]
                for event in self.workspace.ledger.read()[-3:]
            ],
            [
                "agent.updated",
                "agent.updated",
                "workspace.orchestrator_transferred",
            ],
        )
        with self.assertRaises(AuthorizationError):
            self.workspace.create_task(
                actor="antigravity",
                task_id="OLD",
                title="Old authority",
                description="Must fail.",
                owner="claude",
            )
        with self.assertRaisesRegex(AuthorizationError, "authority changed"):
            self.workspace.ledger.append(
                actor="antigravity",
                action="stale.orchestrator.command",
                task_id=None,
                payload={},
                expected_orchestrator="antigravity",
            )
        created = self.workspace.create_task(
            actor="codex",
            task_id="NEW",
            title="New authority",
            description="Must pass.",
            owner="claude",
        )
        self.assertEqual(created["created_by"], "codex")

    def test_doctor_fails_closed_on_inconclusive_historical_identity(self) -> None:
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="antigravity",
            controller_id="antigravity",
            provider="unknown",
            model_family="unknown",
            capabilities=["orchestrate", "proxy_submit", "verify"],
        )
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="claude",
            controller_id="claude",
            provider="unknown",
            model_family="unknown",
            capabilities=["code"],
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="INCONCLUSIVE",
            title="Unknown historical identity",
            description="Doctor must require an explicit decision.",
            owner="claude",
        )
        self._submit(task_id="INCONCLUSIVE", actor="claude")
        manifest = write_evidence_manifest(
            self.workspace,
            actor="antigravity",
            task_id="INCONCLUSIVE",
            suffix="-verify",
        )
        self.workspace.verify(
            actor="antigravity",
            task_id="INCONCLUSIVE",
            decision="accept",
            note="Actor-only legacy acceptance.",
            verification_manifest=manifest,
        )
        audit = self.workspace.audit_independence()
        self.assertEqual(audit["summary"]["inconclusive"], 1)
        self.assertEqual(audit["summary"]["action_required"], 1)
        self.assertFalse(audit_workspace(self.root)["healthy"])

    def test_verifier_profile_is_rechecked_after_task_lock_acquisition(self) -> None:
        self._add_claude_pair()
        self.workspace.create_task(
            actor="antigravity",
            task_id="VERIFIER-RACE",
            title="Verifier deactivation race",
            description="A stale verifier profile must not finalize.",
            owner="codex",
            verification_policy={
                "required_attestations": 0,
                "allowed_verifiers": ["claude-b"],
                "independence_dimensions": [
                    "actor",
                    "controller",
                    "model_family",
                ],
            },
        )
        self._submit(task_id="VERIFIER-RACE", actor="codex")
        manifest = write_evidence_manifest(
            self.workspace,
            actor="claude-b",
            task_id="VERIFIER-RACE",
            suffix="-verify",
        )
        original_task_lock = self.workspace._task_lock

        @contextmanager
        def deactivating_task_lock(task_id: str):
            with original_task_lock(task_id):
                self.workspace.update_agent(
                    actor="antigravity",
                    agent_id="claude-b",
                    controller_id="claude-b",
                    provider="anthropic",
                    model_family="claude-code",
                    capabilities=["review", "verify"],
                    active=False,
                )
                yield

        with patch.object(
            self.workspace,
            "_task_lock",
            side_effect=deactivating_task_lock,
        ):
            with self.assertRaisesRegex(AuthorizationError, "inactive"):
                self.workspace.verify(
                    actor="claude-b",
                    task_id="VERIFIER-RACE",
                    decision="accept",
                    note="Must observe deactivation under lock.",
                    verification_manifest=manifest,
                )

    def test_capability_and_resource_policies_block_bad_claims(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "lacks required capabilities"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="CAP",
                title="Capability mismatch",
                description="Must fail at creation.",
                owner="claude",
                required_capabilities=["gpu-train"],
            )

        self.workspace.create_task(
            actor="antigravity",
            task_id="LOCK-A",
            title="First resource owner",
            description="Hold one repository lock.",
            owner="codex",
            resource_locks=["repo:shared"],
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="LOCK-B",
            title="Second resource owner",
            description="Conflict on the same repository lock.",
            owner="claude",
            resource_locks=[" REPO:SHARED "],
        )
        claimed = self.workspace.claim(actor="codex", task_id="LOCK-A")
        with self.assertRaisesRegex(TransitionError, "repo:shared"):
            self.workspace.claim(actor="claude", task_id="LOCK-B")
        token = claimed["lease_token"]
        self.workspace.start(
            actor="codex",
            task_id="LOCK-A",
            lease_token=token,
        )
        report, manifest = write_submission(
            self.workspace,
            actor="codex",
            task_id="LOCK-A",
        )
        self.workspace.submit(
            actor="codex",
            task_id="LOCK-A",
            lease_token=token,
            report_path=report,
            manifest_path=manifest,
        )
        with self.assertRaisesRegex(TransitionError, "repo:shared"):
            self.workspace.claim(actor="claude", task_id="LOCK-B")

    def test_deactivated_owner_cannot_advance_and_orchestrator_revokes_lease(
        self,
    ) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="LEASE-REVOKE",
            title="Lease revocation",
            description="Deactivation must halt the task immediately.",
            owner="codex",
            required_capabilities=["code"],
            resource_locks=["repo:lease-test"],
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="LEASE-SUCCESSOR",
            title="Lease successor",
            description="The resource must be released after revocation.",
            owner="claude",
            required_capabilities=["code"],
            resource_locks=["repo:lease-test"],
        )
        claimed = self.workspace.claim(actor="codex", task_id="LEASE-REVOKE")
        token = claimed["lease_token"]
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="codex",
            controller_id="codex",
            provider="openai",
            model_family="codex",
            capabilities=["code", "research", "verify"],
            active=False,
        )
        with self.assertRaisesRegex(AuthorizationError, "inactive"):
            self.workspace.start(
                actor="codex",
                task_id="LEASE-REVOKE",
                lease_token=token,
            )
        revoked = self.workspace.revoke_lease(
            actor="antigravity",
            task_id="LEASE-REVOKE",
            reason="Owner identity was deactivated.",
        )
        self.assertEqual(revoked["state"], "revoking")
        self.assertIsNotNone(revoked["lease"])
        audit = audit_workspace(self.root)
        self.assertFalse(audit["healthy"])
        self.assertEqual(
            audit["checks"]["pending_revocations"],
            ["LEASE-REVOKE"],
        )
        with self.assertRaisesRegex(TransitionError, "repo:lease-test"):
            self.workspace.claim(
                actor="claude",
                task_id="LEASE-SUCCESSOR",
            )
        with self.assertRaisesRegex(
            AuthorizationError,
            "Manual agents cannot self-confirm",
        ):
            self.workspace.acknowledge_revocation(
                actor="codex",
                task_id="LEASE-REVOKE",
                lease_token=token,
                termination_evidence="Untrusted manual assertion.",
            )
        acknowledged = self.workspace.confirm_revocation(
            actor="antigravity",
            task_id="LEASE-REVOKE",
            termination_evidence="External process inventory is empty.",
        )
        self.assertEqual(acknowledged["state"], "blocked")
        self.assertIsNone(acknowledged["lease"])
        successor = self.workspace.claim(
            actor="claude",
            task_id="LEASE-SUCCESSOR",
        )
        self.assertEqual(successor["task"]["state"], "claimed")
        self.assertEqual(
            self.workspace.ledger.read()[-2]["action"],
            "task.revocation_confirmed",
        )

    def test_running_worker_block_retains_lock_until_external_confirmation(
        self,
    ) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="RUNNING-BLOCK",
            title="Running blocker",
            description="A blocker does not prove that the process stopped.",
            owner="codex",
            resource_locks=["repo:block-test"],
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="BLOCK-SUCCESSOR",
            title="Blocked successor",
            description="This must wait for external termination evidence.",
            owner="claude",
            required_capabilities=["code"],
            resource_locks=["repo:block-test"],
        )
        claimed = self.workspace.claim(actor="codex", task_id="RUNNING-BLOCK")
        token = claimed["lease_token"]
        self.workspace.start(
            actor="codex",
            task_id="RUNNING-BLOCK",
            lease_token=token,
        )
        revoking = self.workspace.block(
            actor="codex",
            task_id="RUNNING-BLOCK",
            lease_token=token,
            reason="A dependency is unavailable.",
        )
        self.assertEqual(revoking["state"], "revoking")
        self.assertIsNotNone(revoking["lease"])
        with self.assertRaisesRegex(TransitionError, "repo:block-test"):
            self.workspace.claim(actor="claude", task_id="BLOCK-SUCCESSOR")
        with self.assertRaisesRegex(
            AuthorizationError,
            "Manual agents cannot self-confirm",
        ):
            self.workspace.acknowledge_revocation(
                actor="codex",
                task_id="RUNNING-BLOCK",
                lease_token=token,
                termination_evidence="Untrusted manual assertion.",
            )
        self.workspace.confirm_revocation(
            actor="antigravity",
            task_id="RUNNING-BLOCK",
            termination_evidence="External process inventory is empty.",
        )
        successor = self.workspace.claim(
            actor="claude",
            task_id="BLOCK-SUCCESSOR",
        )
        self.assertEqual(successor["task"]["state"], "claimed")

    def test_orchestrator_can_confirm_external_termination(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="MANUAL-REVOKE",
            title="Manual revocation",
            description="Keep the lock until external termination is checked.",
            owner="codex",
            resource_locks=["gpu:0"],
        )
        self.workspace.claim(actor="codex", task_id="MANUAL-REVOKE")
        requested = self.workspace.revoke_lease(
            actor="antigravity",
            task_id="MANUAL-REVOKE",
            reason="Operator requested a stop.",
        )
        self.assertEqual(requested["state"], "revoking")
        with self.assertRaises(AuthorizationError):
            self.workspace.confirm_revocation(
                actor="claude",
                task_id="MANUAL-REVOKE",
                termination_evidence="Untrusted assertion.",
            )
        confirmed = self.workspace.confirm_revocation(
            actor="antigravity",
            task_id="MANUAL-REVOKE",
            termination_evidence=(
                "PID inventory and physical GPU 0 process list are empty."
            ),
        )
        self.assertEqual(confirmed["state"], "blocked")
        self.assertEqual(
            confirmed["revocation"]["acknowledged_by"],
            "antigravity",
        )

    def test_command_revocation_requires_adapter_execution_token(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="command-worker",
            role="worker",
            mode="command",
            command=["unused-command"],
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="EXECUTION-TOKEN",
            title="Execution token",
            description="Only the broker-owned adapter can release this lock.",
            owner="command-worker",
            resource_locks=["gpu:0"],
        )
        claimed = self.workspace.claim(
            actor="command-worker",
            task_id="EXECUTION-TOKEN",
        )
        lease_token = claimed["lease_token"]
        self.workspace.start(
            actor="command-worker",
            task_id="EXECUTION-TOKEN",
            lease_token=lease_token,
        )
        self.workspace.register_execution(
            actor="command-worker",
            task_id="EXECUTION-TOKEN",
            lease_token=lease_token,
            execution_token="adapter-only-secret",
            pid=12345,
            isolation="process-group",
        )
        self.workspace.revoke_lease(
            actor="antigravity",
            task_id="EXECUTION-TOKEN",
            reason="Exercise execution-token binding.",
        )
        for wrong_token in (None, "forged"):
            with self.assertRaisesRegex(
                AuthorizationError,
                "adapter-held execution token",
            ):
                self.workspace.acknowledge_revocation(
                    actor="command-worker",
                    task_id="EXECUTION-TOKEN",
                    lease_token=lease_token,
                    execution_token=wrong_token,
                    termination_evidence="Untrusted assertion.",
                )
        acknowledged = self.workspace.acknowledge_revocation(
            actor="command-worker",
            task_id="EXECUTION-TOKEN",
            lease_token=lease_token,
            execution_token="adapter-only-secret",
            termination_evidence="Broker-owned process tree reports empty.",
        )
        self.assertEqual(acknowledged["state"], "blocked")

    def test_capability_withdrawal_blocks_heartbeat_and_submission(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="CAP-WITHDRAW",
            title="Capability withdrawal",
            description="A live lease cannot retain withdrawn authority.",
            owner="codex",
            required_capabilities=["code"],
        )
        claimed = self.workspace.claim(actor="codex", task_id="CAP-WITHDRAW")
        token = claimed["lease_token"]
        self.workspace.start(
            actor="codex",
            task_id="CAP-WITHDRAW",
            lease_token=token,
        )
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="codex",
            controller_id="codex",
            provider="openai",
            model_family="codex",
            capabilities=["research", "verify"],
        )
        with self.assertRaisesRegex(AuthorizationError, "required capabilities"):
            self.workspace.heartbeat(
                actor="codex",
                task_id="CAP-WITHDRAW",
                lease_token=token,
            )
        report, manifest = write_submission(
            self.workspace,
            actor="codex",
            task_id="CAP-WITHDRAW",
        )
        with self.assertRaisesRegex(AuthorizationError, "required capabilities"):
            self.workspace.submit(
                actor="codex",
                task_id="CAP-WITHDRAW",
                lease_token=token,
                report_path=report,
                manifest_path=manifest,
            )
        self.assertFalse(
            (self.workspace.submissions_dir / "CAP-WITHDRAW").exists()
        )

    def test_gpu_permission_requires_an_explicit_gpu_lock(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "gpu:<index>"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="GPU",
                title="Unsafe GPU task",
                description="No implicit GPU allocation.",
                owner="codex",
                permissions={"gpu": True},
            )

    def test_proxy_policy_requires_remote_identity_and_full_branch_ref(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "git_remote_name"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="PROXY-NO-REMOTE",
                title="Missing proxy remote name",
                description="Programmatic callers must preregister it.",
                owner="claude",
                delivery_policy={
                    "allow_proxy": True,
                    "git_remote_url": "https://example.invalid/repo.git",
                    "git_ref": "refs/heads/main",
                    "required_repo_paths": ["file.py"],
                },
            )
        with self.assertRaisesRegex(ConfigurationError, "refs/heads"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="PROXY-BAD-REF",
                title="Ambiguous proxy ref",
                description="Short or wildcard refs must fail.",
                owner="claude",
                delivery_policy={
                    "allow_proxy": True,
                    "git_remote_name": "origin",
                    "git_remote_url": "https://example.invalid/repo.git",
                    "git_ref": "main",
                    "required_repo_paths": ["file.py"],
                },
            )

    def test_critical_risk_enforces_strict_named_verification(self) -> None:
        self._add_claude_pair()
        with self.assertRaisesRegex(
            ConfigurationError,
            "actor, controller, and model_family",
        ):
            self.workspace.create_task(
                actor="antigravity",
                task_id="WEAK-CRITICAL",
                title="Weak critical policy",
                description="Actor-only verification is insufficient.",
                owner="codex",
                risk_tier="critical",
                verification_policy={
                    "required_attestations": 0,
                    "allowed_verifiers": ["claude-b"],
                    "independence_dimensions": ["actor"],
                },
            )
        task = self.workspace.create_task(
            actor="antigravity",
            task_id="STRICT-CRITICAL",
            title="Strict critical policy",
            description="Named cross-model finalization.",
            owner="codex",
            risk_tier="critical",
            verification_policy={
                "required_attestations": 0,
                "allowed_verifiers": ["claude-b"],
                "independence_dimensions": [
                    "actor",
                    "controller",
                    "model_family",
                ],
            },
        )
        self.assertEqual(task["risk_tier"], "critical")

    def test_idempotency_key_cannot_reuse_a_weaker_task_contract(self) -> None:
        self._add_claude_pair()
        original = self.workspace.create_task(
            actor="antigravity",
            task_id="IDEMPOTENT",
            title="Immutable idempotent task",
            description="The first contract is low risk.",
            owner="codex",
            risk_tier="low",
            idempotency_key="stable-key",
        )
        repeated = self.workspace.create_task(
            actor="antigravity",
            task_id="IDEMPOTENT",
            title="Immutable idempotent task",
            description="The first contract is low risk.",
            owner="codex",
            risk_tier="low",
            idempotency_key="stable-key",
        )
        self.assertEqual(repeated["last_event_hash"], original["last_event_hash"])
        with self.assertRaisesRegex(ConfigurationError, "immutable task contract"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="IDEMPOTENT",
                title="Immutable idempotent task",
                description="The first contract is low risk.",
                owner="codex",
                risk_tier="critical",
                verification_policy={
                    "required_attestations": 0,
                    "allowed_verifiers": ["claude-b"],
                    "independence_dimensions": [
                        "actor",
                        "controller",
                        "model_family",
                    ],
                },
                idempotency_key="stable-key",
            )

    def test_attestation_quorum_cannot_be_filled_by_same_model_aliases(self) -> None:
        attestations = [
            {
                "actor": "claude-b",
                "verifier": {
                    "id": "claude-b",
                    "controller_id": "claude-b",
                    "model_family": "claude-code",
                },
            },
            {
                "actor": "claude-c",
                "verifier": {
                    "id": "claude-c",
                    "controller_id": "claude-c",
                    "model_family": "claude-code",
                },
            },
        ]
        quorum = self.workspace._diverse_attestation_quorum(
            attestations=attestations,
            required=2,
            dimensions=["actor", "controller", "model_family"],
            finalizer={
                "id": "codex",
                "controller_id": "codex",
                "model_family": "codex",
            },
        )
        self.assertIsNone(quorum)

    def test_impossible_attestation_and_finalizer_policy_is_rejected(self) -> None:
        self._add_claude_pair()
        with self.assertRaisesRegex(
            ConfigurationError,
            "required_attestations \\+ 1",
        ):
            self.workspace.create_task(
                actor="antigravity",
                task_id="SELF-QUORUM",
                title="Distinct attester and finalizer",
                description="One identity cannot fill two review stages.",
                owner="claude-a",
                required_capabilities=["code"],
                verification_policy={
                    "required_attestations": 1,
                    "allowed_verifiers": ["codex-verifier"],
                    "independence_dimensions": [
                        "actor",
                        "controller",
                        "model_family",
                    ],
                },
            )

    def test_distinct_model_attester_and_finalizer_can_complete_quorum(self) -> None:
        self._add_claude_pair()
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="gemini-verifier",
            role="verifier",
            controller_id="gemini-verifier",
            provider="google",
            model_family="gemini",
            capabilities=["review", "verify"],
        )
        self.workspace.create_task(
            actor="antigravity",
            task_id="DIVERSE-QUORUM",
            title="Diverse verification quorum",
            description="Attester and finalizer use distinct model families.",
            owner="claude-a",
            required_capabilities=["code"],
            verification_policy={
                "required_attestations": 1,
                "allowed_verifiers": ["codex-verifier", "gemini-verifier"],
                "independence_dimensions": [
                    "actor",
                    "controller",
                    "model_family",
                ],
            },
        )
        self._submit(task_id="DIVERSE-QUORUM", actor="claude-a")
        attestation_manifest = write_evidence_manifest(
            self.workspace,
            actor="codex-verifier",
            task_id="DIVERSE-QUORUM",
            suffix="-attest",
        )
        self.workspace.attest(
            actor="codex-verifier",
            task_id="DIVERSE-QUORUM",
            decision="accept",
            note="First independent model-family reproduction.",
            verification_manifest=attestation_manifest,
        )
        with self.assertRaisesRegex(
            EvidenceError,
            "finalizer verification manifest",
        ):
            self.workspace.verify(
                actor="gemini-verifier",
                task_id="DIVERSE-QUORUM",
                decision="accept",
                note="A bare final decision is insufficient.",
            )
        finalizer_manifest = write_evidence_manifest(
            self.workspace,
            actor="gemini-verifier",
            task_id="DIVERSE-QUORUM",
            suffix="-final",
        )
        verified = self.workspace.verify(
            actor="gemini-verifier",
            task_id="DIVERSE-QUORUM",
            decision="accept",
            note="Distinct finalizer independently reproduced the result.",
            verification_manifest=finalizer_manifest,
        )
        self.assertEqual(verified["state"], "verified")

    def test_same_model_aliases_cannot_form_creation_time_quorum(self) -> None:
        self._add_claude_pair()
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="antigravity",
            controller_id="antigravity",
            provider="anthropic",
            model_family="claude-code",
            capabilities=["orchestrate", "proxy_submit", "verify"],
        )
        with self.assertRaisesRegex(
            ConfigurationError,
            "cannot form",
        ):
            self.workspace.create_task(
                actor="antigravity",
                task_id="ALIAS-QUORUM",
                title="Same-model alias quorum",
                description="Two names do not create model diversity.",
                owner="codex",
                verification_policy={
                    "required_attestations": 1,
                    "allowed_verifiers": ["antigravity", "claude-b"],
                    "independence_dimensions": [
                        "actor",
                        "controller",
                        "model_family",
                    ],
                },
            )

    def test_inactive_agent_cannot_claim(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="QUEUED-BEFORE-DEACTIVATION",
            title="Queued before deactivation",
            description="Fresh claim policy must see the inactive profile.",
            owner="claude",
        )
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="claude",
            controller_id="claude",
            provider="anthropic",
            model_family="claude-code",
            capabilities=["code"],
            active=False,
        )
        with self.assertRaisesRegex(ConfigurationError, "inactive"):
            self.workspace.create_task(
                actor="antigravity",
                task_id="INACTIVE",
                title="Inactive owner",
                description="Must not be assigned.",
                owner="claude",
            )
        with self.assertRaisesRegex(AuthorizationError, "inactive"):
            self.workspace.claim(
                actor="claude",
                task_id="QUEUED-BEFORE-DEACTIVATION",
            )


class GitProxySubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.workspace = make_workspace(root / "workspace")
        self.remote = root / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "-b", "main", str(self.remote)],
            check=True,
            capture_output=True,
        )
        self.REMOTE_URL = self.remote.resolve().as_uri()
        self.repo = root / "source"
        subprocess.run(
            ["git", "init", "-b", "main", str(self.repo)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "core.autocrlf", "false"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "remote",
                "add",
                "origin",
                self.REMOTE_URL,
            ],
            check=True,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _commit_file(self, content: bytes, *, push: bool = True) -> str:
        path = self.repo / "artifact.txt"
        path.write_bytes(content)
        subprocess.run(
            ["git", "-C", str(self.repo), "add", "artifact.txt"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-m", "artifact"],
            check=True,
            capture_output=True,
        )
        commit = (
            subprocess.run(
                ["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            .stdout.strip()
        )
        if push:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.repo),
                    "push",
                    "--force",
                    "origin",
                    "HEAD:refs/heads/main",
                ],
                check=True,
                capture_output=True,
            )
        return commit

    def test_proxy_submission_records_author_proxy_and_git_commit(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="C1",
            title="Cloud worker delivery",
            description="Proxy a byte-exact Git delivery.",
            owner="claude",
            delivery_policy={
                "allow_proxy": True,
                "git_remote_name": "origin",
                "git_remote_url": self.REMOTE_URL,
                "git_ref": "refs/heads/main",
                "required_repo_paths": ["artifact.txt"],
            },
        )
        report, manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="C1",
            suffix="-proxy",
        )
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        artifact = (manifest.parent / manifest_payload["artifacts"][0]["path"]).resolve()
        commit = self._commit_file(artifact.read_bytes())

        submitted = self.workspace.proxy_submit(
            actor="antigravity",
            task_id="C1",
            author="claude",
            report_path=report,
            manifest_path=manifest,
            source_repo=self.repo,
            source_commit=commit,
            source_files=[
                {
                    "local_path": str(artifact),
                    "repo_path": "artifact.txt",
                }
            ],
        )
        submission = submitted["result"]["submission"]
        self.assertEqual(submission["author"], "claude")
        self.assertEqual(submission["submitted_by"], "antigravity")
        self.assertEqual(submission["source"]["source_commit"], commit)
        self.assertEqual(
            submission["source"]["remote_observation"]["method"],
            "git-ls-remote",
        )
        proxy_event = self.workspace.ledger.read()[-1]
        self.assertEqual(proxy_event["actor"], "antigravity")
        self.assertEqual(proxy_event["payload"]["details"]["author"], "claude")

    def test_proxy_rechecks_orchestrator_before_archiving(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="PROXY-HANDOFF",
            title="Proxy handoff race",
            description="A stale orchestrator must not leave an archive.",
            owner="claude",
            delivery_policy={
                "allow_proxy": True,
                "git_remote_name": "origin",
                "git_remote_url": self.REMOTE_URL,
                "git_ref": "refs/heads/main",
                "required_repo_paths": ["artifact.txt"],
            },
        )
        report, manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="PROXY-HANDOFF",
            suffix="-proxy",
        )
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        artifact = (manifest.parent / manifest_payload["artifacts"][0]["path"]).resolve()
        commit = self._commit_file(artifact.read_bytes())

        def verify_then_handoff(**kwargs: object) -> dict[str, object]:
            verified = verify_git_delivery(**kwargs)
            self.workspace.transfer_orchestrator(
                actor="antigravity",
                target="codex",
                reason="Race proxy submission with a signed handoff.",
            )
            return verified

        with patch(
            "evidence_orchestrator.workspace.verify_git_delivery",
            side_effect=verify_then_handoff,
        ):
            with self.assertRaisesRegex(AuthorizationError, "Only orchestrator"):
                self.workspace.proxy_submit(
                    actor="antigravity",
                    task_id="PROXY-HANDOFF",
                    author="claude",
                    report_path=report,
                    manifest_path=manifest,
                    source_repo=self.repo,
                    source_commit=commit,
                    source_files=[
                        {
                            "local_path": str(artifact),
                            "repo_path": "artifact.txt",
                        }
                    ],
                )
        self.assertFalse(
            (self.workspace.submissions_dir / "PROXY-HANDOFF").exists(),
            "stale proxy authority archived evidence before rejection",
        )

    def test_proxy_cannot_forge_a_different_author(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="FORGE",
            title="Forged author",
            description="Must fail before delivery checks.",
            owner="claude",
            delivery_policy={
                "allow_proxy": True,
                "git_remote_name": "origin",
                "git_remote_url": self.REMOTE_URL,
                "git_ref": "refs/heads/main",
                "required_repo_paths": ["artifact.txt"],
            },
        )
        report, manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="FORGE",
            suffix="-proxy",
        )
        with self.assertRaisesRegex(AuthorizationError, "registered owner"):
            self.workspace.proxy_submit(
                actor="antigravity",
                task_id="FORGE",
                author="codex",
                report_path=report,
                manifest_path=manifest,
                source_repo=self.repo,
                source_commit="0" * 40,
                source_files=[],
            )

    def test_proxy_submitter_cannot_be_the_work_author(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="SELF-PROXY",
            title="Self proxy bypass",
            description="The delivery proxy and author must be distinct.",
            owner="antigravity",
            delivery_policy={
                "allow_proxy": True,
                "git_remote_name": "origin",
                "git_remote_url": self.REMOTE_URL,
                "git_ref": "refs/heads/main",
                "required_repo_paths": ["artifact.txt"],
            },
        )
        report, manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="SELF-PROXY",
            suffix="-proxy",
        )
        with self.assertRaisesRegex(AuthorizationError, "different identity"):
            self.workspace.proxy_submit(
                actor="antigravity",
                task_id="SELF-PROXY",
                author="antigravity",
                report_path=report,
                manifest_path=manifest,
                source_repo=self.repo,
                source_commit="0" * 40,
                source_files=[],
            )

    def test_proxy_submission_respects_live_resource_locks(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="ACTIVE",
            title="Active shared resource",
            description="Hold the repository resource.",
            owner="codex",
            resource_locks=["repo:shared"],
        )
        self.workspace.claim(actor="codex", task_id="ACTIVE")
        self.workspace.create_task(
            actor="antigravity",
            task_id="PROXY-LOCK",
            title="Conflicting proxy delivery",
            description="Must not bypass resource ownership.",
            owner="claude",
            resource_locks=["repo:shared"],
            delivery_policy={
                "allow_proxy": True,
                "git_remote_name": "origin",
                "git_remote_url": self.REMOTE_URL,
                "git_ref": "refs/heads/main",
                "required_repo_paths": ["artifact.txt"],
            },
        )
        report, manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="PROXY-LOCK",
            suffix="-proxy",
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        artifact = (manifest.parent / payload["artifacts"][0]["path"]).resolve()
        commit = self._commit_file(artifact.read_bytes())
        with self.assertRaisesRegex(TransitionError, "repo:shared"):
            self.workspace.proxy_submit(
                actor="antigravity",
                task_id="PROXY-LOCK",
                author="claude",
                report_path=report,
                manifest_path=manifest,
                source_repo=self.repo,
                source_commit=commit,
                source_files=[
                    {
                        "local_path": str(artifact),
                        "repo_path": "artifact.txt",
                    }
                ],
            )

    def test_proxy_scope_must_match_preregistered_repository_paths(self) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id="PROXY-SCOPE",
            title="Preregistered proxy scope",
            description="A partial source list must fail.",
            owner="claude",
            delivery_policy={
                "allow_proxy": True,
                "git_remote_name": "origin",
                "git_remote_url": self.REMOTE_URL,
                "git_ref": "refs/heads/main",
                "required_repo_paths": ["artifact.txt", "required.py"],
            },
        )
        report, manifest = write_submission(
            self.workspace,
            actor="antigravity",
            task_id="PROXY-SCOPE",
            suffix="-proxy",
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        artifact = (manifest.parent / payload["artifacts"][0]["path"]).resolve()
        commit = self._commit_file(artifact.read_bytes())
        with self.assertRaisesRegex(EvidenceError, "preregistered repository paths"):
            self.workspace.proxy_submit(
                actor="antigravity",
                task_id="PROXY-SCOPE",
                author="claude",
                report_path=report,
                manifest_path=manifest,
                source_repo=self.repo,
                source_commit=commit,
                source_files=[
                    {
                        "local_path": str(artifact),
                        "repo_path": "artifact.txt",
                    }
                ],
            )

    def test_crlf_conversion_is_detected(self) -> None:
        commit = self._commit_file(b"line one\nline two\n")
        delivered = Path(self.temp.name) / "converted.txt"
        delivered.write_bytes(b"line one\r\nline two\r\n")
        with self.assertRaisesRegex(EvidenceError, "bytes differ"):
            verify_git_delivery(
                repo_path=self.repo,
                remote_name="origin",
                expected_remote_url=self.REMOTE_URL,
                source_ref="refs/heads/main",
                source_commit=commit,
                files=[
                    {
                        "local_path": str(delivered),
                        "repo_path": "artifact.txt",
                    }
                ],
            )

    def test_unexpected_remote_url_is_rejected(self) -> None:
        commit = self._commit_file(b"trusted bytes\n")
        delivered = self.repo / "artifact.txt"
        with self.assertRaisesRegex(EvidenceError, "remote URL mismatch"):
            verify_git_delivery(
                repo_path=self.repo,
                remote_name="origin",
                expected_remote_url="https://example.invalid/other/repo.git",
                source_ref="refs/heads/main",
                source_commit=commit,
                files=[
                    {
                        "local_path": str(delivered),
                        "repo_path": "artifact.txt",
                    }
                ],
            )

    def test_unpushed_local_commit_is_rejected(self) -> None:
        self._commit_file(b"published\n")
        local_only = self._commit_file(b"local only\n", push=False)
        delivered = self.repo / "artifact.txt"
        with self.assertRaisesRegex(EvidenceError, "advertises"):
            verify_git_delivery(
                repo_path=self.repo,
                remote_name="origin",
                expected_remote_url=self.REMOTE_URL,
                source_ref="refs/heads/main",
                source_commit=local_only,
                files=[
                    {
                        "local_path": str(delivered),
                        "repo_path": "artifact.txt",
                    }
                ],
            )

    def test_local_replace_ref_cannot_substitute_remote_commit_tree(self) -> None:
        published = self._commit_file(b"published bytes\n")
        replacement = self._commit_file(b"replacement bytes\n", push=False)
        subprocess.run(
            ["git", "-C", str(self.repo), "replace", published, replacement],
            check=True,
            capture_output=True,
        )
        delivered = self.repo / "artifact.txt"
        with self.assertRaisesRegex(EvidenceError, "bytes differ"):
            verify_git_delivery(
                repo_path=self.repo,
                remote_name="origin",
                expected_remote_url=self.REMOTE_URL,
                source_ref="refs/heads/main",
                source_commit=published,
                files=[
                    {
                        "local_path": str(delivered),
                        "repo_path": "artifact.txt",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
