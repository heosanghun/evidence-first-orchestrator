from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.errors import IntegrityError

from .helpers import make_workspace


class LedgerTests(unittest.TestCase):
    def test_tampering_breaks_hash_and_signature_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workspace = make_workspace(Path(temp) / "workspace")
            workspace.create_task(
                actor="antigravity",
                task_id="TAMPER",
                title="Ledger test",
                description="Detect mutation.",
                owner="codex",
            )
            ledger_path = workspace.ledger.path
            text = ledger_path.read_text(encoding="utf-8")
            ledger_path.write_text(
                text.replace("task.created", "task.changed", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(IntegrityError, "hash mismatch"):
                workspace.ledger.verify()
            with self.assertRaises(IntegrityError):
                workspace.ledger.append(
                    actor="antigravity",
                    action="should.fail",
                    task_id=None,
                    payload={},
                )


if __name__ == "__main__":
    unittest.main()
