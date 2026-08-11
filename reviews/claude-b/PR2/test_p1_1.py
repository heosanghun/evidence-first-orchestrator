"""Regression test pinning finding P1-1 from the Claude B review of PR #2.

**This test is expected to FAIL against `cef5623`.** That is the point: it
encodes the behaviour the design already promises, which the shipped code does
not yet deliver. It is deliberately kept out of `tests/` so it cannot turn the
suite red; move it there once `audit_independence` is fixed.

Run it from the repository root:

    PYTHONPATH=src python3 -m unittest \
        reviews.claude-b.PR2.test_p1_1 -v

or directly:

    PYTHONPATH=src python3 reviews/claude-b/PR2/test_p1_1.py

What it pins
------------
`docs/META_ORCHESTRATION_V2.md:69-72` states:

    "Identity metadata is declarative. EFO can prove that the signed
    declaration did not change silently; it cannot prove that an operator
    told the truth about the underlying model."

The second clause is honoured. The first is not, operationally. A `critical`
task with three-dimension independence is correctly refused when author and
verifier share a `model_family`; one `update_agent` call changes the declared
`model_family` and the byte-identical task is accepted, runs to
`task.verified`, and `audit_independence` then reports it `independent` with
`action_required: 0` — even though the mutation sits in the ledger six events
before the verification.

`test_the_bypass_itself_reproduces` documents the bypass and passes today.
`test_audit_flags_independence_that_rested_on_a_mutated_declaration` asserts
the fix and fails today.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.errors import ConfigurationError
from evidence_orchestrator.workspace import Workspace

SIX_SECTION_REPORT = "\n".join(
    [
        "# T1 report",
        "",
        "## 1. Files changed",
        "See evidence manifest.",
        "",
        "## 2. Validation and raw output",
        "Recorded in the evidence manifest.",
        "",
        "## 3. Pass, fail, and skip counts",
        "Recorded in the evidence manifest.",
        "",
        "## 4. Known-answer comparison",
        "Expected and observed values are recorded.",
        "",
        "## 5. Proposed changes outside ownership",
        "None.",
        "",
        "## 6. Unmeasured items",
        "[FILL]",
        "",
    ]
)

CRITICAL_TASK = {
    "task_id": "T1",
    "title": "critical work",
    "description": "work whose verification must be independent",
    "owner": "claude-a",
    "risk_tier": "critical",
    "verification_policy": {
        "allowed_verifiers": ["claude-b"],
        "independence_dimensions": ["actor", "controller", "model_family"],
    },
}


def _write_bundle(directory: Path, stem: str) -> tuple[Path, Path]:
    """Write a minimal passing report + evidence manifest, return both paths."""

    directory.mkdir(parents=True, exist_ok=True)
    artifact = directory / f"{stem}.artifact.txt"
    artifact.write_text(f"{stem} artifact\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    report = directory / f"{stem}.md"
    report.write_text(SIX_SECTION_REPORT, encoding="utf-8")

    manifest = directory / f"{stem}.evidence.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifacts": [{"path": artifact.name, "sha256": digest}],
                "validations": [
                    {
                        "command": f"known-test-{stem}",
                        "exit_code": 0,
                        "passed": 1,
                        "failed": 0,
                        "skipped": 0,
                        "skip_reasons": [],
                    }
                ],
                "known_answer_checks": [
                    {
                        "name": "two plus two",
                        "expected": 4,
                        "observed": 4,
                        "passed": True,
                    }
                ],
                "claims": [
                    {
                        "name": "functional behavior",
                        "kind": "functional",
                        "measured": True,
                        "value": "pass",
                        "evidence": [artifact.name],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return report, manifest


class ForgedIndependenceRegressionTest(unittest.TestCase):
    """Independence must not be forgeable by editing the declaration."""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="efo-p1-1-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.workspace = Workspace.initialize(
            self.root / "ws",
            name="p1-1-regression",
            orchestrator="antigravity",
            preset="meta-4-agent",
        )

    # -- helpers ---------------------------------------------------------

    def _add_critical_task(self) -> dict:
        return self.workspace.create_task(actor="antigravity", **CRITICAL_TASK)

    def _forge_claude_b_model_family(self) -> None:
        """The whole attack: one declared field, changed by the orchestrator."""

        self.workspace.update_agent(
            actor="antigravity",
            agent_id="claude-b",
            controller_id="claude-b",
            provider="anthropic",
            model_family="gpt",
        )

    def _drive_to_verified(self) -> None:
        reports = self.workspace.reports_dir
        report, manifest = _write_bundle(reports / "claude-a", "T1")

        lease = self.workspace.claim(actor="claude-a", task_id="T1")
        token = lease["lease_token"]
        self.workspace.start(actor="claude-a", task_id="T1", lease_token=token)
        self.workspace.submit(
            actor="claude-a",
            task_id="T1",
            lease_token=token,
            report_path=report,
            manifest_path=manifest,
        )

        _, attest_manifest = _write_bundle(reports / "claude-b", "T1.attest")
        self.workspace.attest(
            actor="claude-b",
            task_id="T1",
            decision="accept",
            note="reproduced",
            verification_manifest=attest_manifest,
        )
        _, verify_manifest = _write_bundle(reports / "claude-b", "T1.verify")
        self.workspace.verify(
            actor="claude-b",
            task_id="T1",
            decision="accept",
            note="reproduced",
            verification_manifest=verify_manifest,
        )

    # -- tests -----------------------------------------------------------

    def test_the_bypass_itself_reproduces(self) -> None:
        """Passes today. Documents the bypass the audit must later catch."""

        # The preset ships claude-a and claude-b as the same model family, so
        # a critical three-dimension task is correctly refused.
        with self.assertRaises(ConfigurationError) as refusal:
            self._add_critical_task()
        self.assertIn("independent", str(refusal.exception))

        self._forge_claude_b_model_family()

        # The byte-identical request now succeeds.
        task = self._add_critical_task()
        self.assertEqual(task["risk_tier"], "critical")
        self.assertEqual(
            task["verification_policy"]["independence_dimensions"],
            ["actor", "controller", "model_family"],
        )

        self._drive_to_verified()
        self.assertEqual(self.workspace.get_task("T1")["state"], "verified")

        # And the mutation really is in the ledger, before the verification.
        events = self.workspace.ledger.read()
        mutation = next(
            event["sequence"]
            for event in events
            if event.get("action") == "agent.updated"
            and event.get("payload", {}).get("agent", {}).get("id") == "claude-b"
        )
        verification = next(
            event["sequence"]
            for event in events
            if event.get("action") == "task.verified"
        )
        self.assertLess(
            mutation,
            verification,
            "the declaration change must precede the verification it enabled",
        )

    def test_audit_flags_independence_that_rested_on_a_mutated_declaration(
        self,
    ) -> None:
        """FAILS at cef5623. This is finding P1-1.

        The audit is the one command whose purpose is retrospective
        independence review. When the passing verdict rests on a declaration
        that was rewritten before the task existed, a clean report is worse
        than no report: an auditor receives an affirmative all-clear.
        """

        with self.assertRaises(ConfigurationError):
            self._add_critical_task()
        self._forge_claude_b_model_family()
        self._add_critical_task()
        self._drive_to_verified()

        audit = self.workspace.audit_independence()
        (record,) = audit["records"]

        self.assertNotEqual(
            record["status"],
            "independent",
            "a verification whose independence was created by editing the "
            "declaration must not be reported as independent",
        )
        self.assertGreaterEqual(
            audit["summary"]["action_required"],
            1,
            "the summary must not read clean when a declaration was mutated "
            "into independence",
        )
        self.assertTrue(
            any("mutat" in reason or "changed" in reason
                for reason in record["result"]["reasons"]),
            "the audit should name the declaration change as the reason; "
            f"got {record['result']['reasons']}",
        )

    def test_reverting_the_declaration_does_not_launder_the_record(self) -> None:
        """FAILS at cef5623, for the same root cause.

        `audit_independence` prefers the frozen verification profile
        (`workspace.py:2366`), so restoring the true declaration afterwards
        leaves the forged verdict looking clean either way.
        """

        with self.assertRaises(ConfigurationError):
            self._add_critical_task()
        self._forge_claude_b_model_family()
        self._add_critical_task()
        self._drive_to_verified()

        # Put the truthful declaration back.
        self.workspace.update_agent(
            actor="antigravity",
            agent_id="claude-b",
            controller_id="claude-b",
            provider="anthropic",
            model_family="claude-code",
        )

        audit = self.workspace.audit_independence()
        self.assertGreaterEqual(audit["summary"]["action_required"], 1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
