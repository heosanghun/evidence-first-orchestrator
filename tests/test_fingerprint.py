from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evidence_orchestrator.cli import main
from evidence_orchestrator.fingerprint import workspace_fingerprint

from .helpers import make_workspace


def _files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class WorkspaceFingerprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.workspace = make_workspace(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_fingerprint_binds_workspace_ledger_host_and_runtime(self) -> None:
        result = workspace_fingerprint(self.workspace)

        self.assertEqual(
            result["workspace"]["workspace_id"],
            self.workspace.config["workspace_id"],
        )
        self.assertEqual(
            result["workspace"]["root"]["path"],
            str(self.root.resolve()),
        )
        self.assertEqual(result["workspace"]["orchestrator"], "antigravity")
        self.assertEqual(
            result["workspace"]["agents"]["ids"],
            ["antigravity", "claude", "codex"],
        )
        self.assertEqual(result["workspace"]["tasks"]["count"], 0)
        self.assertEqual(result["workspace"]["ledger"]["events"], 4)
        self.assertTrue(result["workspace"]["ledger"]["valid"])
        self.assertTrue(result["workspace"]["ledger"]["signed"])
        self.assertEqual(
            result["workspace"]["ledger"]["sha256"],
            hashlib.sha256(self.workspace.ledger.path.read_bytes()).hexdigest(),
        )
        self.assertTrue(result["host"]["hostname"])
        self.assertTrue(result["runtime"]["efo_version"])
        self.assertTrue(result["runtime"]["package_path"])

    def test_fingerprint_does_not_modify_workspace_files(self) -> None:
        before = _files(self.root)
        workspace_fingerprint(self.workspace)
        self.assertEqual(_files(self.root), before)

    def test_cli_emits_fingerprint_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["workspace", "fingerprint", str(self.root)])

        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(
            result["workspace"]["workspace_id"],
            self.workspace.config["workspace_id"],
        )
        self.assertEqual(result["workspace"]["ledger"]["events"], 4)
        self.assertEqual(result["workspace"]["tasks"]["states"], {})

    def test_module_entrypoint_emits_fingerprint_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "evidence_orchestrator",
                "workspace",
                "fingerprint",
                str(self.root),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=os.environ,
        )

        result = json.loads(completed.stdout)
        self.assertEqual(
            result["workspace"]["workspace_id"],
            self.workspace.config["workspace_id"],
        )


if __name__ == "__main__":
    unittest.main()
