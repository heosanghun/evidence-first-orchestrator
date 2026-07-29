"""Safe command adapters for non-interactive agent CLIs."""

from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, EFOError, LeaseError, TransitionError
from .job_runner import COMMAND_ENV
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


class _WindowsJob:
    """Track one adapter process tree with a kill-on-close Windows Job Object."""

    KILL_ON_JOB_CLOSE = 0x00002000

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("Windows Job Objects are available only on Windows")
        import ctypes
        from ctypes import wintypes

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        class BasicAccountingInformation(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD),
                ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD),
                ("TotalTerminatedProcesses", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = self.KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            handle,
            9,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(handle)
            raise ctypes.WinError(error)
        self._ctypes = ctypes
        self._wintypes = wintypes
        self._kernel32 = kernel32
        self._accounting_type = BasicAccountingInformation
        self._handle = handle

    def assign(self, process: subprocess.Popen[bytes]) -> None:
        """Assign a gated supervisor before it can launch the worker."""

        process_handle = self._wintypes.HANDLE(int(process._handle))  # type: ignore[attr-defined]
        if not self._kernel32.AssignProcessToJobObject(
            self._handle,
            process_handle,
        ):
            raise self._ctypes.WinError(self._ctypes.get_last_error())

    def active_processes(self) -> int:
        """Return the number of live processes still assigned to the job."""

        accounting = self._accounting_type()
        if not self._kernel32.QueryInformationJobObject(
            self._handle,
            1,
            self._ctypes.byref(accounting),
            self._ctypes.sizeof(accounting),
            None,
        ):
            raise self._ctypes.WinError(self._ctypes.get_last_error())
        return int(accounting.ActiveProcesses)

    def terminate(self, *, timeout_seconds: float = 5.0) -> tuple[bool, str]:
        """Terminate every assigned process and wait for an empty job."""

        if not self._kernel32.TerminateJobObject(self._handle, 1):
            return (
                False,
                f"TerminateJobObject failed with error "
                f"{self._ctypes.get_last_error()}",
            )
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                if self.active_processes() == 0:
                    return True, "Windows Job Object reports zero active processes"
            except OSError as exc:
                return False, f"Unable to query Windows Job Object: {exc}"
            time.sleep(0.05)
        return False, "Windows Job Object still contains active processes"

    def close(self) -> None:
        """Close the job handle; kill-on-close is a final safety backstop."""

        handle = getattr(self, "_handle", None)
        if handle:
            self._kernel32.CloseHandle(handle)
            self._handle = None

    def __del__(self) -> None:
        self.close()


class _LinuxSubreaper:
    """Keep daemonized descendants attributable to one serialized adapter."""

    PR_SET_CHILD_SUBREAPER = 36

    def __init__(self) -> None:
        if not sys.platform.startswith("linux") or not Path("/proc/self/task").is_dir():
            raise OSError(
                "POSIX command adapters require Linux subreaper and /proc support"
            )
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(self.PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
            raise OSError(
                ctypes.get_errno(),
                "Unable to enable Linux child-subreaper containment",
            )
        self._baseline = self._direct_children(os.getpid())
        self.root_pid: int | None = None

    @staticmethod
    def _direct_children(pid: int) -> set[int]:
        children: set[int] = set()
        task_root = Path(f"/proc/{pid}/task")
        try:
            task_dirs = list(task_root.iterdir())
        except FileNotFoundError as exc:
            if pid == os.getpid() or Path(f"/proc/{pid}").exists():
                raise OSError(
                    f"Linux process {pid} has no readable task telemetry"
                ) from exc
            return children
        except OSError as exc:
            raise OSError(
                f"Unable to enumerate Linux process {pid} tasks: {exc}"
            ) from exc
        successful_reads = 0
        for task_dir in task_dirs:
            try:
                raw = (task_dir / "children").read_text(encoding="ascii")
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise OSError(
                    f"Unable to inspect Linux process {pid} children: {exc}"
                ) from exc
            successful_reads += 1
            children.update(int(value) for value in raw.split() if value.isdigit())
        if successful_reads == 0 and (
            pid == os.getpid() or Path(f"/proc/{pid}").exists()
        ):
            raise OSError(
                f"Linux process {pid} has no readable children telemetry"
            )
        return children

    def active_pids(self) -> set[int]:
        """Return descendants plus detached children reparented to EFO."""

        direct = self._direct_children(os.getpid()) - self._baseline
        pending = list(direct)
        if self.root_pid is not None and Path(f"/proc/{self.root_pid}").exists():
            pending.append(self.root_pid)
        observed: set[int] = set()
        while pending:
            pid = pending.pop()
            if pid in observed or pid == os.getpid():
                continue
            if not Path(f"/proc/{pid}").exists():
                continue
            observed.add(pid)
            pending.extend(self._direct_children(pid) - observed)
        return observed

    def _reap_detached(self) -> None:
        for pid in self._direct_children(os.getpid()) - self._baseline:
            if pid == self.root_pid:
                continue
            try:
                os.waitpid(pid, os.WNOHANG)
            except (ChildProcessError, OSError):
                continue

    def terminate(
        self,
        process: subprocess.Popen[bytes],
        *,
        timeout_seconds: float = 5.0,
    ) -> tuple[bool, str]:
        """Terminate tracked descendants, including new sessions and daemons."""

        pids = self.active_pids()
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for pid in sorted(pids, reverse=True):
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    continue
                except OSError as exc:
                    return False, f"Unable to signal tracked process {pid}: {exc}"
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            deadline = time.monotonic() + timeout_seconds
            while time.monotonic() < deadline:
                self._reap_detached()
                pids = self.active_pids()
                if not pids:
                    return True, "Linux subreaper reports zero tracked descendants"
                time.sleep(0.05)
        return (
            False,
            "Linux subreaper still tracks live processes: "
            + ", ".join(str(pid) for pid in sorted(pids)),
        )


_ADAPTER_PROCESS_LOCK = threading.Lock()
_ADAPTER_CONTAINMENT_BROKEN: str | None = None
_ADAPTER_PROCESS_ACTIVE = False


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
    verification_policy = json.dumps(
        task.get("verification_policy", {}),
        indent=2,
        sort_keys=True,
    )
    delivery_policy = json.dumps(
        task.get("delivery_policy", {}),
        indent=2,
        sort_keys=True,
    )
    return (
        f"# Task {task['id']}: {task['title']}\n\n"
        f"{task['description']}\n\n"
        "## Ownership\n"
        f"- Agent: {task['owner']}\n"
        f"- Task type: {task.get('task_type', 'general')}\n"
        f"- Risk tier: {task.get('risk_tier', 'medium')}\n"
        f"- Required capabilities: {json.dumps(task.get('required_capabilities', []))}\n"
        f"- Resource locks: {json.dumps(task.get('resource_locks', []))}\n"
        f"- Allowed write roots: {json.dumps(task['allowed_write_roots'])}\n"
        f"- Report: {report_path}\n"
        f"- Evidence manifest: {evidence_path}\n\n"
        "## Permissions\n"
        f"```json\n{permissions}\n```\n\n"
        "## Preregistered gates\n"
        f"```json\n{gates}\n```\n\n"
        "## Verification policy\n"
        f"```json\n{verification_policy}\n```\n\n"
        "## Delivery policy\n"
        f"```json\n{delivery_policy}\n```\n\n"
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


def _process_group_options() -> dict[str, Any]:
    if os.name == "nt":
        return {
            "creationflags": getattr(
                subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0,
            )
        }
    return {"start_new_session": True}


def _launch_controlled_process(
    argv: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    stdout: Any,
    stderr: Any,
) -> tuple[
    subprocess.Popen[bytes],
    _WindowsJob | None,
    _LinuxSubreaper | None,
]:
    """Launch a gated supervisor and bind its tree before worker execution."""

    job = _WindowsJob() if os.name == "nt" else None
    linux_tree = _LinuxSubreaper() if os.name != "nt" else None
    supervisor_environment = {
        **environment,
        COMMAND_ENV: json.dumps(argv),
    }
    try:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("job_runner.py"))],
            cwd=cwd,
            env=supervisor_environment,
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=stderr,
            shell=False,
            **_process_group_options(),
        )
        if job is not None:
            job.assign(process)
        if linux_tree is not None:
            linux_tree.root_pid = process.pid
    except BaseException:
        if "process" in locals() and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if job is not None:
            job.close()
        raise
    return process, job, linux_tree


def _terminate_process_tree(
    process: subprocess.Popen[bytes],
    *,
    windows_job: _WindowsJob | None = None,
    linux_tree: _LinuxSubreaper | None = None,
) -> tuple[bool, str]:
    """Terminate the adapter-owned process tree and report confirmation."""

    pid = process.pid
    if os.name == "nt":
        try:
            if windows_job is None:
                return False, "Windows process tree has no assigned Job Object"
            confirmed, evidence = windows_job.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return False, f"Job supervisor {pid} did not exit"
            return confirmed, evidence
        except OSError as exc:
            return False, f"Unable to terminate Windows Job Object: {exc}"
        finally:
            if windows_job is not None:
                windows_job.close()

    if linux_tree is None:
        return False, "Linux process tree has no subreaper containment"
    try:
        return linux_tree.terminate(process)
    except OSError as exc:
        return False, f"Unable to inspect Linux subreaper descendants: {exc}"


def _confirm_completed_process_tree(
    process: subprocess.Popen[bytes],
    *,
    windows_job: _WindowsJob | None,
    linux_tree: _LinuxSubreaper | None,
) -> tuple[bool, bool, str]:
    """Confirm that normal parent exit left no live descendants."""

    pid = process.pid
    if os.name == "nt":
        if windows_job is None:
            return False, False, "Windows process tree has no assigned Job Object"
        try:
            active = windows_job.active_processes()
        except OSError as exc:
            windows_job.close()
            return False, False, f"Unable to query Windows Job Object: {exc}"
        if active == 0:
            windows_job.close()
            return True, False, "Windows Job Object reports zero active processes"
        confirmed, evidence = _terminate_process_tree(
            process,
            windows_job=windows_job,
        )
        return confirmed, True, (
            f"Worker parent exited with {active} live Job Object process(es); "
            + evidence
        )

    if linux_tree is None:
        return False, False, "Linux process tree has no subreaper containment"
    try:
        active = linux_tree.active_pids()
    except OSError as exc:
        return (
            False,
            False,
            f"Unable to inspect Linux subreaper descendants: {exc}",
        )
    if not active:
        return True, False, "Linux subreaper reports zero tracked descendants"
    confirmed, evidence = _terminate_process_tree(
        process,
        linux_tree=linux_tree,
    )
    return confirmed, True, (
        "Worker parent exited with tracked descendant process(es) "
        f"{sorted(active)}; {evidence}"
    )


def _acknowledge_adapter_revocation(
    *,
    workspace: Workspace,
    agent_id: str,
    task_id: str,
    lease_token: str,
    execution_token: str,
    termination_evidence: str,
    exit_code: int | None,
) -> dict[str, Any]:
    acknowledged = workspace.acknowledge_revocation(
        actor=agent_id,
        task_id=task_id,
        lease_token=lease_token,
        termination_evidence=termination_evidence,
        execution_token=execution_token,
    )
    return {
        "task_id": task_id,
        "state": acknowledged["state"],
        "exit_code": exit_code,
        "revoked": True,
        "termination_evidence": termination_evidence,
    }


def _hold_for_unconfirmed_termination(
    *,
    workspace: Workspace,
    agent_id: str,
    task_id: str,
    lease_token: str,
    reason: str,
) -> dict[str, Any]:
    """Retain locks even when revocation races with containment failure."""

    try:
        return workspace.hold_for_termination(
            actor=agent_id,
            task_id=task_id,
            lease_token=lease_token,
            reason=reason,
        )
    except (LeaseError, TransitionError):
        current = workspace.get_task(task_id)
        if current["state"] == "revoking":
            return current
        raise


def _block_after_process_exit(
    *,
    workspace: Workspace,
    agent_id: str,
    task_id: str,
    lease_token: str,
    execution_token: str,
    reason: str,
    process: subprocess.Popen[bytes] | None,
    exit_code: int | None,
    termination_evidence: str | None = None,
) -> dict[str, Any]:
    """Record a blocker and release locks only with adapter-owned exit evidence."""

    try:
        blocked_or_revoking = workspace.block(
            actor=agent_id,
            task_id=task_id,
            lease_token=lease_token,
            reason=reason,
        )
    except (LeaseError, TransitionError):
        current = workspace.get_task(task_id)
        if current["state"] == "revoking":
            blocked_or_revoking = current
        elif current["state"] == "running":
            blocked_or_revoking = workspace.hold_for_termination(
                actor=agent_id,
                task_id=task_id,
                lease_token=lease_token,
                reason=f"Adapter process exited after control failure: {reason}",
            )
        else:
            raise
    if blocked_or_revoking["state"] != "revoking":
        return blocked_or_revoking
    pid = process.pid if process is not None else "not-started"
    return workspace.acknowledge_revocation(
        actor=agent_id,
        task_id=task_id,
        lease_token=lease_token,
        termination_evidence=(
            termination_evidence
            or f"Adapter-owned process {pid} exited with code {exit_code}"
        ),
        execution_token=execution_token,
    )


def _run_once_serialized(
    workspace: Workspace,
    *,
    agent_id: str,
    task_id: str | None = None,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Execute one task while the adapter process lock is held."""

    global _ADAPTER_PROCESS_ACTIVE
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
    revocation_seen = False
    termination_evidence = ""
    process: subprocess.Popen[bytes] | None = None
    windows_job: _WindowsJob | None = None
    linux_tree: _LinuxSubreaper | None = None
    execution_token = secrets.token_urlsafe(32)
    started = time.monotonic()
    heartbeat_interval = max(5, int(task["lease"]["duration_seconds"]) // 3)
    next_heartbeat = started + heartbeat_interval
    next_control_check = started
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process, windows_job, linux_tree = _launch_controlled_process(
                argv,
                cwd=workspace.root,
                environment=environment,
                stdout=stdout,
                stderr=stderr,
            )
            _ADAPTER_PROCESS_ACTIVE = True
            workspace.register_execution(
                actor=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                execution_token=execution_token,
                pid=process.pid,
                isolation="windows-job" if os.name == "nt" else "linux-subreaper",
            )
            if process.stdin is None:
                raise OSError("Adapter supervisor has no control pipe")
            process.stdin.write(b"start\n")
            process.stdin.flush()
            process.stdin.close()
            while process.poll() is None:
                now = time.monotonic()
                if now >= next_control_check:
                    current = workspace.get_task(task["id"])
                    if current["state"] == "revoking":
                        revocation_seen = True
                        confirmed, termination_evidence = _terminate_process_tree(
                            process,
                            windows_job=windows_job,
                            linux_tree=linux_tree,
                        )
                        if not confirmed:
                            return {
                                "task_id": task["id"],
                                "state": "revoking",
                                "error": termination_evidence,
                                "revoked": True,
                                "termination_unconfirmed": True,
                            }
                        break
                    next_control_check = now + 0.5
                if now - started > timeout_seconds:
                    timed_out = True
                    confirmed, termination_evidence = _terminate_process_tree(
                        process,
                        windows_job=windows_job,
                        linux_tree=linux_tree,
                    )
                    if not confirmed:
                        held = _hold_for_unconfirmed_termination(
                            workspace=workspace,
                            agent_id=agent_id,
                            task_id=task["id"],
                            lease_token=lease_token,
                            reason=termination_evidence,
                        )
                        return {
                            "task_id": task["id"],
                            "state": held["state"],
                            "error": termination_evidence,
                            "termination_unconfirmed": True,
                        }
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
        confirmed = True
        if process is not None:
            confirmed, termination_evidence = _terminate_process_tree(
                process,
                windows_job=windows_job,
                linux_tree=linux_tree,
            )
        current = workspace.get_task(task["id"])
        if current["state"] == "revoking":
            if confirmed and isinstance(current.get("execution"), dict):
                return _acknowledge_adapter_revocation(
                    workspace=workspace,
                    agent_id=agent_id,
                    task_id=task["id"],
                    lease_token=lease_token,
                    execution_token=execution_token,
                    termination_evidence=(
                        termination_evidence
                        or f"Adapter process was not running after error: {exc}"
                    ),
                    exit_code=process.returncode if process is not None else None,
                )
            return {
                "task_id": task["id"],
                "state": "revoking",
                "error": termination_evidence,
                "revoked": True,
                "termination_unconfirmed": True,
            }
        if not confirmed:
            held = _hold_for_unconfirmed_termination(
                workspace=workspace,
                agent_id=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                reason=termination_evidence,
            )
            return {
                "task_id": task["id"],
                "state": held["state"],
                "error": termination_evidence,
                "termination_unconfirmed": True,
            }
        if not isinstance(current.get("execution"), dict):
            held = _hold_for_unconfirmed_termination(
                workspace=workspace,
                agent_id=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                reason=(
                    "Adapter setup failed before a signed execution binding; "
                    f"external confirmation required: {exc}"
                ),
            )
            return {
                "task_id": task["id"],
                "state": held["state"],
                "error": str(exc),
                "termination_unconfirmed": True,
            }
        _block_after_process_exit(
            workspace=workspace,
            agent_id=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            execution_token=execution_token,
            reason=f"Command adapter failed: {exc}",
            process=process,
            exit_code=process.returncode if process is not None else None,
            termination_evidence=termination_evidence or None,
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "error": str(exc),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
        }

    if revocation_seen:
        return _acknowledge_adapter_revocation(
            workspace=workspace,
            agent_id=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            execution_token=execution_token,
            termination_evidence=termination_evidence,
            exit_code=exit_code,
        )

    if not timed_out:
        tree_confirmed, orphaned, tree_evidence = _confirm_completed_process_tree(
            process,
            windows_job=windows_job,
            linux_tree=linux_tree,
        )
        if not tree_confirmed:
            held = _hold_for_unconfirmed_termination(
                workspace=workspace,
                agent_id=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                reason=tree_evidence,
            )
            return {
                "task_id": task["id"],
                "state": held["state"],
                "error": tree_evidence,
                "termination_unconfirmed": True,
            }
        if orphaned:
            blocked = _block_after_process_exit(
                workspace=workspace,
                agent_id=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                execution_token=execution_token,
                reason="Worker parent exited with live descendant processes.",
                process=process,
                exit_code=exit_code,
                termination_evidence=tree_evidence,
            )
            return {
                "task_id": task["id"],
                "state": blocked["state"],
                "exit_code": exit_code,
                "orphaned_descendants": True,
                "termination_evidence": tree_evidence,
            }
        try:
            workspace.record_execution_exit(
                actor=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                execution_token=execution_token,
                exit_code=int(exit_code),
                termination_evidence=tree_evidence,
            )
        except TransitionError:
            current = workspace.get_task(task["id"])
            if current["state"] != "revoking":
                raise
            return _acknowledge_adapter_revocation(
                workspace=workspace,
                agent_id=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                execution_token=execution_token,
                termination_evidence=tree_evidence,
                exit_code=exit_code,
            )

    after = _workspace_snapshot(workspace.root)
    unauthorized = _unauthorized_changes(
        before,
        after,
        allowed_prefixes=allowed,
    )
    if unauthorized:
        _block_after_process_exit(
            workspace=workspace,
            agent_id=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            execution_token=execution_token,
            reason="Unauthorized workspace changes: " + ", ".join(unauthorized),
            process=process,
            exit_code=exit_code,
            termination_evidence=termination_evidence or None,
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "exit_code": exit_code,
            "unauthorized_changes": unauthorized,
        }
    if timed_out or exit_code != 0:
        _block_after_process_exit(
            workspace=workspace,
            agent_id=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            execution_token=execution_token,
            reason=(
                f"Agent command timed out after {timeout_seconds}s"
                if timed_out
                else f"Agent command exited with code {exit_code}"
            ),
            process=process,
            exit_code=exit_code,
            termination_evidence=termination_evidence or None,
        )
        return {
            "task_id": task["id"],
            "state": "blocked",
            "exit_code": exit_code,
            "timed_out": timed_out,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
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
        current = workspace.get_task(task["id"])
        if current["state"] == "revoking":
            return _acknowledge_adapter_revocation(
                workspace=workspace,
                agent_id=agent_id,
                task_id=task["id"],
                lease_token=lease_token,
                execution_token=execution_token,
                termination_evidence=(
                    f"Adapter process {process.pid if process else 'unknown'} "
                    f"had exited with code {exit_code}"
                ),
                exit_code=exit_code,
            )
        _block_after_process_exit(
            workspace=workspace,
            agent_id=agent_id,
            task_id=task["id"],
            lease_token=lease_token,
            execution_token=execution_token,
            reason=f"Evidence gate rejected output: {exc}",
            process=process,
            exit_code=exit_code,
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


def run_once(
    workspace: Workspace,
    *,
    agent_id: str,
    task_id: str | None = None,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Claim and execute one task through a serialized command adapter."""

    global _ADAPTER_CONTAINMENT_BROKEN, _ADAPTER_PROCESS_ACTIVE
    with _ADAPTER_PROCESS_LOCK:
        if _ADAPTER_CONTAINMENT_BROKEN is not None:
            raise ConfigurationError(
                "Command adapters are disabled until this broker restarts: "
                + _ADAPTER_CONTAINMENT_BROKEN
            )
        _ADAPTER_PROCESS_ACTIVE = False
        try:
            result = _run_once_serialized(
                workspace,
                agent_id=agent_id,
                task_id=task_id,
                timeout_seconds=timeout_seconds,
            )
        except BaseException as exc:
            if _ADAPTER_PROCESS_ACTIVE:
                _ADAPTER_CONTAINMENT_BROKEN = (
                    "adapter execution raised before containment was confirmed: "
                    f"{type(exc).__name__}: {exc}"
                )
            raise
        finally:
            _ADAPTER_PROCESS_ACTIVE = False
        if result.get("termination_unconfirmed"):
            _ADAPTER_CONTAINMENT_BROKEN = str(
                result.get("error", "process-tree termination was not confirmed")
            )
        return result


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
