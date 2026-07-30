from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from evidence_orchestrator import adapter as adapter_module
from evidence_orchestrator.adapter import run_once
from evidence_orchestrator.errors import TransitionError
from evidence_orchestrator.workspace import Workspace


def _pid_is_running(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(0x00100000, False, pid)
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
    finally:
        kernel32.CloseHandle(handle)


def _wait_for_windows_file_release(path: Path) -> None:
    if os.name != "nt" or not path.exists():
        return
    probe = path.with_name(path.name + ".efo-release-probe")
    deadline = time.monotonic() + 5
    while True:
        try:
            path.replace(probe)
            probe.replace(path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.05)


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
                    import sys
                    from pathlib import Path

                    prompt = sys.stdin.read()
                    required_prompt_text = (
                        "# Task AUTO: Automated worker",
                        "## Signed identity boundary",
                        '"id": "codex"',
                        "Workspace orchestrator:",
                        "You are only the registered EFO actor `codex`",
                    )
                    missing = [
                        item for item in required_prompt_text if item not in prompt
                    ]
                    if missing:
                        raise RuntimeError(f"missing prompt identity fields: {missing}")

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
                prompt_stdin=True,
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
            if result["state"] != "submitted" and "stderr" in result:
                result["stderr_text"] = Path(str(result["stderr"])).read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            self.assertEqual(result["state"], "submitted", result)
            self.assertEqual(workspace.get_task("AUTO")["state"], "submitted")
            prompt_paths = list((root / "runs" / "codex" / "AUTO").glob("*/prompt.md"))
            self.assertEqual(len(prompt_paths), 1)
            prompt_text = prompt_paths[0].read_text(encoding="utf-8")
            self.assertIn('"role": "worker"', prompt_text)
            self.assertIn('"id": "antigravity"', prompt_text)

    def test_revocation_stops_process_before_releasing_resource_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "workspace"
            helper = base / "long_worker.py"
            pid_path = base / "long_worker.pid"
            helper.write_text(
                textwrap.dedent(
                    """
                    import os
                    import sys
                    import time
                    from pathlib import Path

                    Path(sys.argv[1]).write_text(str(os.getpid()), encoding="utf-8")
                    time.sleep(60)
                    """
                ),
                encoding="utf-8",
            )
            workspace = Workspace.initialize(
                root,
                name="adapter-revocation-test",
                orchestrator="antigravity",
            )
            workspace.add_agent(
                actor="antigravity",
                agent_id="codex",
                role="worker",
                mode="command",
                command=[sys.executable, str(helper), str(pid_path)],
            )
            workspace.add_agent(
                actor="antigravity",
                agent_id="claude",
                role="worker",
            )
            workspace.create_task(
                actor="antigravity",
                task_id="LONG",
                title="Long adapter worker",
                description="Must be terminated before its lock is released.",
                owner="codex",
                resource_locks=["gpu:0"],
            )
            workspace.create_task(
                actor="antigravity",
                task_id="AFTER-LONG",
                title="Successor task",
                description="Must wait for confirmed process termination.",
                owner="claude",
                resource_locks=["gpu:0"],
            )
            result: dict[str, object] = {}

            def run_worker() -> None:
                try:
                    result.update(
                        run_once(
                            workspace,
                            agent_id="codex",
                            task_id="LONG",
                            timeout_seconds=30,
                        )
                    )
                except BaseException as exc:  # pragma: no cover - surfaced below
                    result["exception"] = exc

            thread = threading.Thread(target=run_worker, daemon=True)
            thread.start()
            deadline = time.monotonic() + 10
            while not pid_path.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(pid_path.exists(), "adapter child did not start")
            requested = workspace.revoke_lease(
                actor="antigravity",
                task_id="LONG",
                reason="Test-controlled shutdown.",
            )
            self.assertEqual(requested["state"], "revoking")
            thread.join(timeout=15)
            self.assertFalse(thread.is_alive(), "adapter did not stop its child")
            exception = result.get("exception")
            if isinstance(exception, BaseException):
                raise exception
            self.assertTrue(result["revoked"])
            if result["state"] == "revoking":
                self.assertTrue(result["termination_unconfirmed"])
                with self.assertRaisesRegex(TransitionError, "gpu:0"):
                    workspace.claim(actor="claude", task_id="AFTER-LONG")
                workspace.confirm_revocation(
                    actor="antigravity",
                    task_id="LONG",
                    termination_evidence=(
                        "Adapter thread joined and owned parent process exited; "
                        "test worker spawned no descendants."
                    ),
                )
            else:
                self.assertEqual(result["state"], "blocked", result)
                self.assertTrue(
                    str(result["termination_evidence"]).strip(),
                    "adapter returned no termination evidence",
                )
            task = workspace.get_task("LONG")
            self.assertEqual(task["state"], "blocked")
            self.assertIsNone(task["lease"])
            successor = workspace.claim(
                actor="claude",
                task_id="AFTER-LONG",
            )
            self.assertEqual(successor["task"]["state"], "claimed")
            for output in root.glob("runs/codex/LONG/**/*.txt"):
                _wait_for_windows_file_release(output)

    def test_detached_descendant_is_killed_and_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "workspace"
            child = base / "child.py"
            child_pid_path = base / "child.pid"
            worker = base / "orphan_worker.py"
            child.write_text(
                "import time\ntime.sleep(60)\n",
                encoding="utf-8",
            )
            worker.write_text(
                textwrap.dedent(
                    """
                    import os
                    import subprocess
                    import sys
                    from pathlib import Path

                    if os.name == "nt":
                        process = subprocess.Popen([sys.executable, sys.argv[1]])
                        Path(sys.argv[2]).write_text(
                            str(process.pid),
                            encoding="utf-8",
                        )
                    else:
                        first = os.fork()
                        if first > 0:
                            os.waitpid(first, 0)
                        else:
                            os.setsid()
                            second = os.fork()
                            if second > 0:
                                os._exit(0)
                            Path(sys.argv[2]).write_text(
                                str(os.getpid()),
                                encoding="utf-8",
                            )
                            import time
                            time.sleep(60)
                            os._exit(0)
                    """
                ),
                encoding="utf-8",
            )
            workspace = Workspace.initialize(
                root,
                name="adapter-orphan-test",
                orchestrator="antigravity",
            )
            workspace.add_agent(
                actor="antigravity",
                agent_id="codex",
                role="worker",
                mode="command",
                command=[
                    sys.executable,
                    str(worker),
                    str(child),
                    str(child_pid_path),
                ],
            )
            workspace.add_agent(
                actor="antigravity",
                agent_id="claude",
                role="worker",
            )
            workspace.create_task(
                actor="antigravity",
                task_id="ORPHAN",
                title="Orphan descendant",
                description="A child must not outlive its adapter parent.",
                owner="codex",
                resource_locks=["gpu:0"],
            )
            workspace.create_task(
                actor="antigravity",
                task_id="AFTER-ORPHAN",
                title="Orphan successor",
                description="Claim only after the descendant is gone.",
                owner="claude",
                resource_locks=["gpu:0"],
            )
            result = run_once(
                workspace,
                agent_id="codex",
                task_id="ORPHAN",
                timeout_seconds=30,
            )
            self.assertEqual(result["state"], "blocked", result)
            self.assertTrue(result["orphaned_descendants"], result)
            self.assertTrue(child_pid_path.exists())
            child_pid = int(child_pid_path.read_text(encoding="utf-8"))
            deadline = time.monotonic() + 5
            while _pid_is_running(child_pid) and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertFalse(
                _pid_is_running(child_pid),
                "descendant remained live after process-tree termination",
            )
            successor = workspace.claim(
                actor="claude",
                task_id="AFTER-ORPHAN",
            )
            self.assertEqual(successor["task"]["state"], "claimed")

    def test_procfs_inspection_failure_is_not_empty_tree_confirmation(self) -> None:
        with self.subTest("missing self task directory"):
            with mock.patch.object(
                Path,
                "iterdir",
                side_effect=FileNotFoundError("synthetic missing task directory"),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "no readable task telemetry",
                ):
                    adapter_module._LinuxSubreaper._direct_children(os.getpid())

        with self.subTest("missing self children interface"):
            task_dir = Path("/synthetic/proc/self/task/self")
            with (
                mock.patch.object(Path, "iterdir", return_value=iter([task_dir])),
                mock.patch.object(
                    Path,
                    "read_text",
                    side_effect=FileNotFoundError(
                        "synthetic missing children interface"
                    ),
                ),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "no readable children telemetry",
                ):
                    adapter_module._LinuxSubreaper._direct_children(os.getpid())

        with self.subTest("task enumeration"):
            with mock.patch.object(
                Path,
                "iterdir",
                side_effect=PermissionError("synthetic task denial"),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "Unable to enumerate Linux process",
                ):
                    adapter_module._LinuxSubreaper._direct_children(4242)

        with self.subTest("children read"):
            task_dir = Path("/synthetic/proc/4242/task/4242")
            with (
                mock.patch.object(Path, "iterdir", return_value=iter([task_dir])),
                mock.patch.object(
                    Path,
                    "read_text",
                    side_effect=PermissionError("synthetic children denial"),
                ),
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "Unable to inspect Linux process",
                ):
                    adapter_module._LinuxSubreaper._direct_children(4242)

        class BrokenLinuxTree:
            def active_pids(self) -> set[int]:
                raise OSError("synthetic procfs denial")

        process = mock.Mock()
        process.pid = 4242
        with mock.patch.object(adapter_module.os, "name", "posix"):
            confirmed, orphaned, evidence = (
                adapter_module._confirm_completed_process_tree(
                    process,
                    windows_job=None,
                    linux_tree=BrokenLinuxTree(),  # type: ignore[arg-type]
                )
            )
        self.assertFalse(confirmed)
        self.assertFalse(orphaned)
        self.assertIn("synthetic procfs denial", evidence)

    def test_revocation_race_keeps_lock_and_disables_broker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "workspace"
            helper = base / "worker.py"
            helper.write_text("pass\n", encoding="utf-8")
            workspace = Workspace.initialize(
                root,
                name="adapter-containment-race-test",
                orchestrator="antigravity",
            )
            workspace.add_agent(
                actor="antigravity",
                agent_id="codex",
                role="worker",
                mode="command",
                command=[sys.executable, str(helper)],
            )
            workspace.create_task(
                actor="antigravity",
                task_id="RACE",
                title="Containment race",
                description="Retain the lock when confirmation races revocation.",
                owner="codex",
                resource_locks=["gpu:0"],
            )
            original_hold = workspace.hold_for_termination
            raced = False

            def race_hold(**kwargs: object) -> dict[str, object]:
                nonlocal raced
                if not raced:
                    raced = True
                    workspace.revoke_lease(
                        actor="antigravity",
                        task_id="RACE",
                        reason="Synthetic revocation race.",
                    )
                return original_hold(**kwargs)  # type: ignore[arg-type]

            with (
                mock.patch.object(
                    adapter_module,
                    "_confirm_completed_process_tree",
                    return_value=(
                        False,
                        False,
                        "synthetic containment confirmation failure",
                    ),
                ),
                mock.patch.object(
                    workspace,
                    "hold_for_termination",
                    side_effect=race_hold,
                ),
                mock.patch.object(
                    adapter_module,
                    "_ADAPTER_CONTAINMENT_BROKEN",
                    None,
                ),
                mock.patch.object(
                    adapter_module,
                    "_ADAPTER_PROCESS_ACTIVE",
                    False,
                ),
            ):
                result = run_once(
                    workspace,
                    agent_id="codex",
                    task_id="RACE",
                    timeout_seconds=30,
                )
                self.assertEqual(result["state"], "revoking", result)
                self.assertTrue(result["termination_unconfirmed"], result)
                self.assertIn(
                    "synthetic containment confirmation failure",
                    str(adapter_module._ADAPTER_CONTAINMENT_BROKEN),
                )
                with self.assertRaisesRegex(
                    adapter_module.ConfigurationError,
                    "disabled until this broker restarts",
                ):
                    run_once(
                        workspace,
                        agent_id="codex",
                        task_id="RACE",
                        timeout_seconds=30,
                    )
            self.assertEqual(workspace.get_task("RACE")["state"], "revoking")

    def test_unexpected_active_execution_error_disables_broker(self) -> None:
        def fail_after_launch(*args: object, **kwargs: object) -> dict[str, object]:
            adapter_module._ADAPTER_PROCESS_ACTIVE = True
            raise RuntimeError("synthetic post-launch failure")

        workspace = mock.Mock()
        with (
            mock.patch.object(
                adapter_module,
                "_ADAPTER_CONTAINMENT_BROKEN",
                None,
            ),
            mock.patch.object(
                adapter_module,
                "_ADAPTER_PROCESS_ACTIVE",
                False,
            ),
            mock.patch.object(
                adapter_module,
                "_run_once_serialized",
                side_effect=fail_after_launch,
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "synthetic post-launch failure",
            ):
                run_once(
                    workspace,
                    agent_id="codex",
                    task_id="ACTIVE-ERROR",
                )
            self.assertIn(
                "synthetic post-launch failure",
                str(adapter_module._ADAPTER_CONTAINMENT_BROKEN),
            )
            with self.assertRaisesRegex(
                adapter_module.ConfigurationError,
                "disabled until this broker restarts",
            ):
                run_once(
                    workspace,
                    agent_id="codex",
                    task_id="AFTER-ACTIVE-ERROR",
                )


if __name__ == "__main__":
    unittest.main()
