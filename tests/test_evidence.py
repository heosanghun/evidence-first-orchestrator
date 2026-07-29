from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.errors import EvidenceError
from evidence_orchestrator.evidence import validate_submission

from .helpers import make_workspace, write_submission


class EvidenceGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.workspace = make_workspace(self.root)
        self.task = self.workspace.create_task(
            actor="antigravity",
            task_id="E1",
            title="Evidence gate",
            description="Validate evidence.",
            owner="codex",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self, report: Path, manifest: Path) -> dict:
        return validate_submission(
            report,
            manifest,
            permissions=self.task["permissions"],
            gates=self.task["gates"],
        )

    def test_valid_bundle_passes(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
        )
        result = self.validate(report, manifest)
        self.assertEqual(result["manifest"]["passed"], 1)
        self.assertEqual(result["manifest"]["skipped"], 0)
        self.assertEqual(result["manifest"]["unmeasured_claims"], 1)

    def test_skip_is_not_pass(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-skip",
            skipped=1,
        )
        with self.assertRaisesRegex(EvidenceError, "skip is not pass"):
            self.validate(report, manifest)

    def test_failed_validation_is_rejected(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-failed",
            failed=1,
            exit_code=1,
        )
        with self.assertRaisesRegex(EvidenceError, "did not pass"):
            self.validate(report, manifest)

    def test_performance_claim_requires_permission(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-metric",
            performance_claim=True,
        )
        with self.assertRaisesRegex(EvidenceError, "performance claims are forbidden"):
            self.validate(report, manifest)

    def test_unmeasured_claim_requires_fill(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-fabricated",
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["claims"][-1]["value"] = 0.7
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "exact value \\[FILL\\]"):
            self.validate(report, manifest)

    def test_artifact_hash_mismatch_is_rejected(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-hash",
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["artifacts"][0]["sha256"] = "0" * 64
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "SHA mismatch"):
            self.validate(report, manifest)

    def test_missing_report_section_is_rejected(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-section",
        )
        report.write_text("# Report\n\n## 1. Files changed\n", encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "missing required"):
            self.validate(report, manifest)

    def test_empty_or_duplicate_report_section_is_rejected(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-duplicate",
        )
        text = report.read_text(encoding="utf-8")
        report.write_text(text + "\n## 6. Duplicate\nvalue\n", encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "exactly once"):
            self.validate(report, manifest)

    def test_non_finite_number_is_rejected(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-nan",
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["claims"][0]["value"] = math.nan
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "non-finite"):
            self.validate(report, manifest)

    def test_measured_claim_must_reference_bound_evidence(self) -> None:
        report, manifest = write_submission(
            self.workspace,
            task_id="E1",
            suffix="-unbound",
        )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["claims"][0]["evidence"] = ["not-in-artifacts.txt"]
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(EvidenceError, "not bound"):
            self.validate(report, manifest)


if __name__ == "__main__":
    unittest.main()
