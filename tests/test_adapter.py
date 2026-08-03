from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from evidence_orchestrator.adapter import run_once
from evidence_orchestrator.workspace import Workspace


class CommandAdapterTests(unittest.TestCase):
    def test_command_adapter_submits_valid_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "workspace"
            helper = base / "worker.py"
            helper.write_text(
                textwrap.dedent(
                    """
                    import hashlib
                    import json
                    import os
                    from pathlib import Path

                    report = Path(os.environ["EFO_REPORT"])
                    evidence = Path(os.environ["EFO_EVIDENCE"])
                    artifact = report.parent / "adapter-artifact.txt"
                    artifact.write_text("known-output\\n", encoding="utf-8")
                    report.write_text(
                        "# Adapter report\\n\\n"
                        "## 1. Files changed\\nArtifact.\\n\\n"
                        "## 2. Validation and raw output\\nManifest.\\n\\n"
                        "## 3. Pass, fail, and skip counts\\n1/0/0.\\n\\n"
                        "## 4. Known-answer comparison\\nMatched.\\n\\n"
                        "## 5. Proposed changes outside ownership\\nNone.\\n\\n"
                        "## 6. Unmeasured items\\n[FILL]\\n",
                        encoding="utf-8",
                    )
                    payload = {
                        "schema_version": 1,
                        "artifacts": [{
                            "path": artifact.name,
                            "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                        }],
                        "validations": [{
                            "command": "synthetic known-answer check",
                            "exit_code": 0,
                            "passed": 1,
                            "failed": 0,
                            "skipped": 0,
                            "skip_reasons": [],
                        }],
                        "known_answer_checks": [{
                            "name": "fixed output",
                            "expected": "known-output",
                            "observed": "known-output",
                            "passed": True,
                        }],
                        "claims": [{
                            "name": "adapter execution",
                            "kind": "functional",
                            "measured": True,
                            "value": "pass",
                            "evidence": [artifact.name],
                        }, {
                            "name": "performance",
                            "kind": "performance",
                            "measured": False,
                            "value": "[FILL]",
                            "evidence": [],
                        }],
                    }
                    evidence.write_text(json.dumps(payload), encoding="utf-8")
                    """
                ),
                encoding="utf-8",
            )
            workspace = Workspace.initialize(
                root,
                name="adapter-test",
                orchestrator="antigravity",
            )
            workspace.add_agent(
                actor="antigravity",
                agent_id="codex",
                role="worker",
                mode="command",
                command=[sys.executable, str(helper)],
                control_principal="codex-control",
                model_family="openai-codex",
            )
            workspace.create_task(
                actor="antigravity",
                task_id="AUTO",
                title="Automated worker",
                description="Create a valid evidence bundle.",
                owner="codex",
            )
            result = run_once(
                workspace,
                agent_id="codex",
                task_id="AUTO",
                timeout_seconds=30,
            )
            self.assertEqual(result["state"], "submitted")
            self.assertEqual(workspace.get_task("AUTO")["state"], "submitted")


if __name__ == "__main__":
    unittest.main()
