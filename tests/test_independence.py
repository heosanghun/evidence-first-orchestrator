from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.errors import AuthorizationError, ConfigurationError
from evidence_orchestrator.independence import (
    audit_verification_events,
    build_identity,
    evaluate_independence,
    identity_snapshot,
    resolve_identity_registry,
)

from .helpers import make_workspace, write_evidence_manifest, write_submission


def snapshot(actor: str, principal: str, model: str) -> dict:
    return identity_snapshot(
        actor,
        build_identity(
            control_principal=principal,
            model_family=model,
        ),
    )


class IndependenceKnownAnswerTests(unittest.TestCase):
    def test_same_actor_is_not_independent(self) -> None:
        worker = snapshot("codex", "codex-control", "openai-codex")
        result = evaluate_independence(worker, worker)
        self.assertFalse(result["independent"])
        self.assertIn("same_actor", result["reasons"])

    def test_aliases_with_one_control_principal_are_not_independent(self) -> None:
        worker = snapshot(
            "antigravity-worker",
            "antigravity-control",
            "anthropic-claude",
        )
        verifier = snapshot(
            "antigravity",
            "antigravity-control",
            "anthropic-claude",
        )
        result = evaluate_independence(worker, verifier)
        self.assertFalse(result["independent"])
        self.assertIn("same_control_principal", result["reasons"])

    def test_same_model_family_is_not_independent(self) -> None:
        worker = snapshot("claude-a", "controller-a", "anthropic-claude")
        verifier = snapshot("claude-b", "controller-b", "anthropic-claude")
        result = evaluate_independence(worker, verifier)
        self.assertFalse(result["independent"])
        self.assertIn("same_model_family", result["reasons"])

    def test_codex_and_claude_are_independent(self) -> None:
        worker = snapshot("codex", "codex-control", "openai-codex")
        verifier = snapshot("claude", "claude-control", "anthropic-claude")
        self.assertTrue(evaluate_independence(worker, verifier)["independent"])


class WorkspaceIndependenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.workspace = make_workspace(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def submit(self, *, owner: str, task_id: str) -> None:
        self.workspace.create_task(
            actor="antigravity",
            task_id=task_id,
            title="Identity-gated task",
            description="Exercise independent verification.",
            owner=owner,
        )
        claim = self.workspace.claim(actor=owner, task_id=task_id)
        token = claim["lease_token"]
        self.workspace.start(actor=owner, task_id=task_id, lease_token=token)
        report, manifest = write_submission(
            self.workspace,
            actor=owner,
            task_id=task_id,
        )
        self.workspace.submit(
            actor=owner,
            task_id=task_id,
            lease_token=token,
            report_path=report,
            manifest_path=manifest,
        )

    def verify_manifest(self, *, actor: str, task_id: str) -> Path:
        return write_evidence_manifest(
            self.workspace,
            actor=actor,
            task_id=task_id,
            suffix="-verification",
        )

    def test_registered_verifier_can_cross_verify(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="claude-verifier",
            role="verifier",
            alias_of="claude",
        )
        self.submit(owner="codex", task_id="CROSS")
        result = self.workspace.verify(
            actor="claude-verifier",
            task_id="CROSS",
            decision="accept",
            note="Reproduced independently.",
            verification_manifest=self.verify_manifest(
                actor="claude-verifier",
                task_id="CROSS",
            ),
        )
        self.assertEqual(result["state"], "verified")
        self.assertTrue(result["verification"]["independence"]["independent"])

    def test_same_model_verifier_is_rejected(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="codex-verifier",
            role="verifier",
            control_principal="other-controller",
            model_family="openai-codex",
        )
        self.submit(owner="codex", task_id="SAME-MODEL")
        with self.assertRaisesRegex(AuthorizationError, "same_model_family"):
            self.workspace.verify(
                actor="codex-verifier",
                task_id="SAME-MODEL",
                decision="accept",
                note="Not actually independent.",
                verification_manifest=self.verify_manifest(
                    actor="codex-verifier",
                    task_id="SAME-MODEL",
                ),
            )

    def test_nested_aliases_cannot_bypass_control_principal_check(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="alias-one",
            role="worker",
            alias_of="antigravity",
        )
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="alias-two",
            role="worker",
            alias_of="alias-one",
        )
        self.submit(owner="alias-two", task_id="NESTED")
        self.workspace.attest_agent_identity(
            actor="antigravity",
            agent_id="antigravity",
            control_principal="changed-root-controller",
            model_family="changed-root-model",
        )
        with self.assertRaisesRegex(
            AuthorizationError,
            "shared_alias_lineage",
        ):
            self.workspace.verify(
                actor="antigravity",
                task_id="NESTED",
                decision="accept",
                note="Alias attack.",
                verification_manifest=self.verify_manifest(
                    actor="antigravity",
                    task_id="NESTED",
                ),
            )

    def test_attested_alias_lineage_cannot_be_removed(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="alias-one",
            role="worker",
            alias_of="antigravity",
        )
        with self.assertRaisesRegex(
            ConfigurationError,
            "alias lineage cannot be removed",
        ):
            self.workspace.attest_agent_identity(
                actor="antigravity",
                agent_id="alias-one",
                control_principal="laundered-controller",
                model_family="laundered-model",
            )

    def test_worker_role_cannot_verify(self) -> None:
        self.submit(owner="codex", task_id="ROLE")
        with self.assertRaisesRegex(
            AuthorizationError,
            "registered verifier",
        ):
            self.workspace.verify(
                actor="claude",
                task_id="ROLE",
                decision="reject",
                note="Worker role is not verifier authority.",
            )

    def test_same_agent_cannot_submit_and_verify(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="dual",
            role="verifier",
            control_principal="dual-controller",
            model_family="dual-model",
        )
        self.submit(owner="dual", task_id="SELF")
        with self.assertRaisesRegex(AuthorizationError, "same_actor"):
            self.workspace.verify(
                actor="dual",
                task_id="SELF",
                decision="accept",
                note="Self review.",
                verification_manifest=self.verify_manifest(
                    actor="dual",
                    task_id="SELF",
                ),
            )

    def test_submission_snapshot_prevents_identity_laundering(self) -> None:
        self.workspace.add_agent(
            actor="antigravity",
            agent_id="codex-verifier",
            role="verifier",
            control_principal="other-controller",
            model_family="openai-codex",
        )
        self.submit(owner="codex", task_id="SNAPSHOT")
        self.workspace.attest_agent_identity(
            actor="antigravity",
            agent_id="codex",
            control_principal="codex-control",
            model_family="different-model-after-submit",
        )
        with self.assertRaisesRegex(AuthorizationError, "same_model_family"):
            self.workspace.verify(
                actor="codex-verifier",
                task_id="SNAPSHOT",
                decision="accept",
                note="Post-submit identity change must not alter authorship.",
                verification_manifest=self.verify_manifest(
                    actor="codex-verifier",
                    task_id="SNAPSHOT",
                ),
            )


class RetrospectiveAuditTests(unittest.TestCase):
    def test_audit_policy_cannot_override_signed_identity(self) -> None:
        agents = {
            "codex": {
                "id": "codex",
                "identity": build_identity(
                    control_principal="signed-controller",
                    model_family="openai-codex",
                ),
            }
        }
        policy = {
            "agents": {
                "codex": {
                    "control_principal": "forged-controller",
                    "model_family": "forged-model",
                }
            }
        }
        resolved = resolve_identity_registry(agents, policy=policy)
        self.assertEqual(
            resolved["codex"]["control_principal"],
            "signed-controller",
        )
        self.assertEqual(resolved["codex"]["model_family"], "openai-codex")

    def test_known_historical_cases_and_nested_alias_policy(self) -> None:
        agents = {
            agent_id: {"id": agent_id, "identity": None}
            for agent_id in (
                "antigravity",
                "antigravity-worker",
                "alias-two",
                "claude",
                "codex",
            )
        }
        policy = {
            "agents": {
                "antigravity": {
                    "control_principal": "antigravity-control",
                    "model_family": "anthropic-claude",
                },
                "antigravity-worker": {"alias_of": "antigravity"},
                "alias-two": {"alias_of": "antigravity-worker"},
                "claude": {
                    "control_principal": "claude-control",
                    "model_family": "anthropic-claude",
                },
                "codex": {
                    "control_principal": "codex-control",
                    "model_family": "openai-codex",
                },
            }
        }
        events: list[dict] = []

        def add_history(
            task_id: str,
            worker: str,
            verifier: str,
            sequence: int,
        ) -> None:
            submitted = {
                "id": task_id,
                "owner": worker,
                "attempt": 1,
                "result": {},
                "verification": None,
            }
            verified = {
                **submitted,
                "verification": {"actor": verifier},
            }
            events.extend(
                [
                    {
                        "sequence": sequence,
                        "actor": worker,
                        "action": "task.submitted",
                        "task_id": task_id,
                        "payload": {"task": submitted},
                    },
                    {
                        "sequence": sequence + 1,
                        "actor": verifier,
                        "action": "task.verified",
                        "task_id": task_id,
                        "payload": {"task": verified},
                    },
                ]
            )

        add_history("GATE-PROBE", "alias-two", "antigravity", 1)
        add_history("C1", "claude", "antigravity", 3)
        add_history("P1B", "codex", "antigravity", 5)

        result = audit_verification_events(events, agents, policy=policy)
        by_id = {item["task_id"]: item for item in result["findings"]}
        self.assertFalse(by_id["GATE-PROBE"]["independent"])
        self.assertFalse(by_id["C1"]["independent"])
        self.assertTrue(by_id["P1B"]["independent"])
        self.assertEqual(result["non_independent"], 2)
        self.assertTrue(result["read_only"])
        self.assertEqual(
            by_id["GATE-PROBE"]["worker_identity_source"],
            "audit_policy",
        )


if __name__ == "__main__":
    unittest.main()
