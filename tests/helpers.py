"""Shared fixtures built only from the Python standard library."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from evidence_orchestrator.workspace import Workspace


def make_workspace(root: Path, *, preset: bool = True) -> Workspace:
    return Workspace.initialize(
        root,
        name="test-workspace",
        orchestrator="antigravity",
        orchestrator_control_principal="antigravity-control",
        orchestrator_model_family="antigravity-model",
        preset="antigravity-codex-claude" if preset else None,
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_evidence_manifest(
    workspace: Workspace,
    *,
    actor: str,
    task_id: str,
    suffix: str,
    skipped: int = 0,
    failed: int = 0,
    exit_code: int = 0,
    performance_claim: bool = False,
    unmeasured_claim: bool = True,
    known_answer_passed: bool = True,
) -> Path:
    report_dir = workspace.reports_dir / actor
    artifact = report_dir / f"{task_id}{suffix}.artifact.txt"
    artifact.write_text(f"artifact-{actor}-{suffix}\n", encoding="utf-8")
    claims: list[dict[str, Any]] = [
        {
            "name": "functional behavior",
            "kind": "functional",
            "measured": True,
            "value": "pass",
            "evidence": [artifact.name],
        }
    ]
    if performance_claim:
        claims.append(
            {
                "name": "accuracy",
                "kind": "performance",
                "measured": True,
                "value": 0.9,
                "evidence": [artifact.name],
            }
        )
    if unmeasured_claim:
        claims.append(
            {
                "name": "future metric",
                "kind": "performance",
                "measured": False,
                "value": "[FILL]",
                "evidence": [],
            }
        )
    manifest = {
        "schema_version": 1,
        "artifacts": [{"path": artifact.name, "sha256": _sha(artifact)}],
        "validations": [
            {
                "command": f"known-test-{suffix}",
                "exit_code": exit_code,
                "passed": 1 if not failed else 0,
                "failed": failed,
                "skipped": skipped,
                "skip_reasons": [f"reason-{index}" for index in range(skipped)],
            }
        ],
        "known_answer_checks": [
            {
                "name": "two plus two",
                "expected": 4,
                "observed": 4 if known_answer_passed else 5,
                "passed": known_answer_passed,
            }
        ],
        "claims": claims,
    }
    path = report_dir / f"{task_id}{suffix}.evidence.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_submission(
    workspace: Workspace,
    *,
    actor: str = "codex",
    task_id: str = "T1",
    suffix: str = "",
    **manifest_options: Any,
) -> tuple[Path, Path]:
    report_dir = workspace.reports_dir / actor
    report = report_dir / f"{task_id}{suffix}.md"
    report.write_text(
        "\n".join(
            [
                f"# {task_id} report",
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
        ),
        encoding="utf-8",
    )
    manifest = write_evidence_manifest(
        workspace,
        actor=actor,
        task_id=task_id,
        suffix=suffix,
        **manifest_options,
    )
    return report, manifest
