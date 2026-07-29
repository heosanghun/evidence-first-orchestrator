"""Safe command adapters for non-interactive agent CLIs."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, EFOError, TransitionError
from .util import sha256_file, utc_now
from .workspace import Workspace

PLACEHOLDERS = {
    "workspace",
    "task_id",
    "task_file",
    "prompt",
    "report",
    "evidence",
}


def render_task_prompt(
    *,
    workspace: Workspace,
    task: dict[str, Any],
    report_path: Path,
    evidence_path: Path,
) -> str:
    """Render a self-contained prompt for an external agent process."""

    permissions = json.dumps(task["permissions"], indent=2, sort_keys=True)
    gates = json.dumps(task["gates"], indent=2, sort_keys=True)
    return (
        f"# Task {task['id']}: {task['title']}\n\n"
        f"{task['description']}\n\n"
        "## Ownership\n"
        f"- Agent: {task['owner']}\n"
        f"- Allowed write roots: {json.dumps(task['allowed_write_roots'])}\n"
        f"- Report: {report_path}\n"
        f"- Evidence manifest: {evidence_path}\n\n"
        "## Permissions\n"
        f"```json\n{permissions}\n```\n\n"
        "## Preregistered gates\n"
        f"```json\n{gates}\n```\n\n"
        "Do not claim completion by process exit alone. Write the six-section report "
        "and schema_version=1 evidence manifest. Unmeasured values must be [FILL]. "
        "A skipped test is not a pass.\n"
    )


def _expand_command(command: list[str], values: dict[str, str]) -> list[str]:
    expanded: list[str] = []
    for item in command:
        value = item
        for key, replacement in values.items():
            value = value.replace("{" + key + "}", replacement)
        expanded.append(value)
    return expanded


def _workspace_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".efo/locks/"):
            continue
        try:
            snapshot[relative] = sha256_file(path)
        except OSError:
            continue
    return snapshot


def _unauthorized_changes(
    before: dict[str, str],
    after: dict[str, str],
    *,
    allowed_prefixes: list[str],
) -> list[str]:
    changed = {
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    }
    normalized = [prefix.replace("\\", "/").strip("/") for prefix in allowed_prefixes]
    return sorted(
        path
        for path in changed
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in normalized)
    )


def run_once(
    workspace: Workspace,
    *,
    agent_id: str,
    task_id: str | None = None,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Claim and execute one task through a configured command adapter."""

    agent = workspace.get_agent(agent_id)
    if agent["mode"] != "command":
        raise ConfigurationError(f"Agent {agent_id} is not configured in command mode")
    command = agent.get("command")
    if not isinstance(command, list) or not command:
        raise ConfigurationError(f"Agent {agent_id} has no command")

    claim = workspace.claim(actor=agent_id, task_id=task_id)
    task = claim["task"]
    lease_token = claim["lease_token"]
    workspace.start(actor=agent_id, task_id=task["id"], lease_token=lease_token)

    report_dir = workspace.reports_dir / agent_id
    run_dir = workspace.runs_dir / agent_id / task["id"] / utc_now().replace(":", "")
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{task['id']}.md"
    evidence_path = report_dir / f"{task['id']}.evidence.json"
    prompt_path = run_dir / "prompt.md"
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    prompt_path.write_text(
        render_task_prompt(
            workspace=workspace,
            task=task,
            report_path=report_path,
            evidence_path=evidence_path,
        ),
        encoding="utf-8",
    )

    values = {
        "workspace": str(workspace.root),
        "task_id": task["id"],
        "task_file": str(workspace._task_path(task["id"])),
        "prompt": str(prompt_path),
        "report": str(report_path),
        "evidence": str(evidence_path),
    }
    argv = _expand_command(command, values)
    allowed = list(agent.get("write_roots", []))
    allowed.extend(task.get("allowed_write_roots", []))
    allowed.extend(
        [
            f"reports/{agent_id}",
            f"runs/{agent_id}",
            f"tasks/{task['id']}.json",
            "ledger/events.jsonl",
        ]
    )
    before = _workspace_snapshot(workspace.root)
    environment = {
        **os.environ,
        "EFO_WORKSPACE": str(workspace.root),
        "EFO_TASK_ID": task["id"],
        "EFO_PROMPT": str(prompt_path),
        "EFO_REPORT": str(report_path),
        "EFO_EVIDENCE": str(evidence_path),
    }

    exit_code: int | None = None
    timed_out = False
    started = time.monotonic()
    heartbeat_interval = max(5, int(task["lease"]["duration_seconds"]) // 3)
    next_heartbeat = started + heartbeat_interval
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                argv,
                cwd=workspace.root,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                shell=False,
            )
            while process.poll() is None:
                now = time.monotonic()
                if now - started > timeout_seconds:
                    timed_out = True
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                if now >= next_heartbeat:
                    workspace.heartbeat(
                        actor=agent_id,
                        task_id=task["id"],
                        lease_token=lease_token,
                    )
                    next_heartbeat = now + heartbeat_interval
                time.sleep(0.2)
            exit_code = process.wait()
    except (OSError, EFOError) as exc:
        workspace.block(
            actor=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            reason=f"Command adapter failed: {exc}",
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "error": str(exc),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        }

    after = _workspace_snapshot(workspace.root)
    unauthorized = _unauthorized_changes(
        before,
        after,
        allowed_prefixes=allowed,
    )
    if unauthorized:
        workspace.block(
            actor=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            reason="Unauthorized workspace changes: " + ", ".join(unauthorized),
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "exit_code": exit_code,
            "unauthorized_changes": unauthorized,
        }
    if timed_out or exit_code != 0:
        workspace.block(
            actor=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            reason=(
                f"Agent command timed out after {timeout_seconds}s"
                if timed_out
                else f"Agent command exited with code {exit_code}"
            ),
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "exit_code": exit_code,
            "timed_out": timed_out,
        }
    try:
        submitted = workspace.submit(
            actor=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            report_path=report_path,
            manifest_path=evidence_path,
        )
    except EFOError as exc:
        workspace.block(
            actor=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            reason=f"Evidence gate rejected output: {exc}",
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "exit_code": exit_code,
            "error": str(exc),
        }
    return {
        "task_id": task["id"],
        "state": submitted["state"],
        "exit_code": exit_code,
        "report": str(report_path),
        "evidence": str(evidence_path),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def run_loop(
    workspace: Workspace,
    *,
    agent_id: str,
    poll_seconds: float = 5.0,
    timeout_seconds: int = 3600,
    max_tasks: int | None = None,
    idle_timeout_seconds: float | None = None,
) -> list[dict[str, Any]]:
    """Poll for work and execute tasks until a configured stopping condition."""

    if poll_seconds <= 0:
        raise ConfigurationError("poll_seconds must be positive")
    if max_tasks is not None and max_tasks < 1:
        raise ConfigurationError("max_tasks must be positive")
    results: list[dict[str, Any]] = []
    idle_started = time.monotonic()
    while max_tasks is None or len(results) < max_tasks:
        try:
            result = run_once(
                workspace,
                agent_id=agent_id,
                timeout_seconds=timeout_seconds,
            )
        except TransitionError as exc:
            if "No ready pending tasks" not in str(exc):
                raise
            if (
                idle_timeout_seconds is not None
                and time.monotonic() - idle_started >= idle_timeout_seconds
            ):
                break
            time.sleep(poll_seconds)
            continue
        results.append(result)
        idle_started = time.monotonic()
    return results
