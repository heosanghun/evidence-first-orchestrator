from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.doctor import LEGACY_REQUIRED, audit_legacy_workspace


class LegacyDoctorTests(unittest.TestCase):
    def test_legacy_audit_is_readable_and_redacts_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "legacy"
            for relative in LEGACY_REQUIRED:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# file\n", encoding="utf-8")
            (root / "shared" / "ENV.md").write_text(
                "host example.invalid\npassword super-secret-value\n",
                encoding="utf-8",
            )
            (root / "logs" / "EVENTS.md").write_text(
                "# events\n[2026-07-29 14:00] antigravity NOTE INIT created\n",
                encoding="utf-8",
            )
            result = audit_legacy_workspace(root)
            rendered = json.dumps(result)
            self.assertTrue(result["compatible"])
            self.assertEqual(len(result["secret_findings"]), 1)
            self.assertNotIn("super-secret-value", rendered)
            self.assertEqual(
                result["secret_findings"][0]["value"],
                "[REDACTED]",
            )

    def test_malformed_event_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "legacy"
            for relative in LEGACY_REQUIRED:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# file\n", encoding="utf-8")
            (root / "logs" / "EVENTS.md").write_text(
                "[2026-07-29] broken\n",
                encoding="utf-8",
            )
            result = audit_legacy_workspace(root)
            self.assertFalse(result["compatible"])
            self.assertEqual(result["malformed_events"][0]["line"], 1)


if __name__ == "__main__":
    unittest.main()
