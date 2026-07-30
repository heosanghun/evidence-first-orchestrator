"""Collect sanitized EFO, GPU, Docker, and host metrics without mutating the server."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = "1.0"
COLLECTOR_VERSION = "efo-monitor/1.2"
HISTORY_LIMIT = 60
ACTIVITY_LIMIT = 300
TASK_PROGRESS = {
    "pending": 10,
    "claimed": 25,
    "running": 55,
    "blocked": 45,
    "submitted": 80,
    "verified": 100,
    "rejected": 65,
    "archived": 100,
    "invalidated": 0,
}
EXTERNAL_PROGRESS = {
    "dispatched": 15,
    "working": 40,
    "reviewing": 70,
    "ready": 85,
    "blocked": 10,
}
EXTERNAL_NEXT = {
    "dispatched": "외부 작업자 수신 확인",
    "working": "외부 구현 결과 대기",
    "reviewing": "독립 검토 결과 대기",
    "ready": "대리 제출 및 증거 검증",
    "blocked": "운반자 보고 차단 사유 확인",
}
TASK_NEXT = {
    "pending": "작업을 claim하고 시작",
    "claimed": "작업 실행 시작",
    "running": "증거 번들 제출",
    "blocked": "차단 원인 해소",
    "submitted": "독립 검증",
    "verified": "검증 결과 보관",
    "rejected": "수정 후 재제출",
    "archived": "완료",
    "invalidated": "새 과제 재등록",
}
ACTIVE_STATES = {"claimed", "running"}
TERMINAL_STATES = {"verified", "archived"}
LIVE_CARD_STATES = {"pending", "claimed", "running", "submitted"}
AGENT_STATES = {"working", "waiting", "blocked", "offline"}
ACTIVITY_ACTIONS = {
    "workspace.initialized": ("워크스페이스 생성", "system"),
    "agent.added": ("에이전트 등록", "system"),
    "task.created": ("작업 생성", "planning"),
    "task.claimed": ("작업 할당", "work"),
    "task.started": ("작업 시작", "work"),
    "task.heartbeat": ("진행 신호", "work"),
    "task.blocked": ("작업 차단", "issue"),
    "task.submitted": ("증거 제출", "evidence"),
    "task.proxy_authorized": ("대리 제출 승인", "planning"),
    "task.proxy_status_reported": ("외부 진행상태 보고", "work"),
    "task.proxy_submitted": ("대리 증거 제출", "evidence"),
    "task.verified": ("검증 통과", "success"),
    "task.rejected": ("검증 반려", "issue"),
    "task.requeued": ("작업 재대기", "planning"),
    "task.archived": ("작업 완료·보관", "success"),
    "task.lease_expired": ("임대 만료", "issue"),
}
SAFE_LABEL_RE = re.compile(r"[^0-9A-Za-z가-힣._:+/@ -]+")
TQDM_RE = re.compile(
    r"(?P<percent>\d{1,3})%\|[^|]*\|\s*(?P<current>[\d,]+)"
    r"/(?P<total>[\d,]+).*?<(?P<eta>[^,\]\s]+)"
)
COUNTER_RE = re.compile(
    r"(?:step|steps|iter|iteration|epoch)?\s*[:=#]?\s*"
    r"(?P<current>\d[\d,]*)\s*/\s*(?P<total>\d[\d,]*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CommandResult:
    """Captured result of a read-only command."""

    returncode: int
    stdout: str
    stderr: str


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(args: Sequence[str], timeout: float = 12.0) -> CommandResult:
    """Run a command without a shell and capture bounded text output."""

    try:
        completed = subprocess.run(
            list(args),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", str(exc))
    return CommandResult(
        completed.returncode,
        completed.stdout[-1_500_000:],
        completed.stderr[-200_000:],
    )


def parse_number(value: Any, default: float = 0.0) -> float:
    """Parse common command output numbers, treating N/A as a default."""

    if value is None:
        return default
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"n/a", "[n/a]", "nan", "none"}:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def sanitize_label(value: Any, fallback: str = "unknown", limit: int = 80) -> str:
    """Return a short display label with control and shell punctuation removed."""

    text = SAFE_LABEL_RE.sub("", str(value or "")).strip()
    return (text or fallback)[:limit]


def parse_progress(text: str) -> dict[str, Any] | None:
    """Extract only a progress counter and ETA from recent logs."""

    matches = list(TQDM_RE.finditer(text))
    if matches:
        match = matches[-1]
        current = int(match.group("current").replace(",", ""))
        total = int(match.group("total").replace(",", ""))
        return {
            "current": current,
            "total": total,
            "percent": min(100.0, max(0.0, parse_number(match.group("percent")))),
            "eta": sanitize_label(match.group("eta"), "-", 24),
        }
    matches = list(COUNTER_RE.finditer(text))
    if not matches:
        return None
    match = matches[-1]
    current = int(match.group("current").replace(",", ""))
    total = int(match.group("total").replace(",", ""))
    if total <= 0 or current > total * 2:
        return None
    return {
        "current": current,
        "total": total,
        "percent": min(100.0, max(0.0, current / total * 100)),
        "eta": None,
    }


def query_gpus() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read all physical GPUs using nvidia-smi."""

    fields = (
        "index,uuid,name,utilization.gpu,memory.used,memory.total,"
        "temperature.gpu,power.draw"
    )
    result = run_command(
        ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"]
    )
    if result.returncode != 0:
        return [], [
            {
                "severity": "critical",
                "title": "GPU 상태 수집 실패",
                "message": sanitize_label(result.stderr, "nvidia-smi 실행 실패", 160),
                "at": utc_now(),
            }
        ]

    gpus: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 8:
            continue
        try:
            index = int(parts[0])
        except ValueError:
            continue
        gpus.append(
            {
                "index": index,
                "_uuid": parts[1],
                "name": sanitize_label(parts[2], "NVIDIA GPU"),
                "utilization_percent": parse_number(parts[3]),
                "memory_used_mib": parse_number(parts[4]),
                "memory_total_mib": parse_number(parts[5]),
                "temperature_c": parse_number(parts[6]),
                "power_w": parse_number(parts[7]),
                "projects": [],
            }
        )
    return sorted(gpus, key=lambda item: item["index"]), []


def query_compute_apps() -> list[dict[str, Any]]:
    """Read GPU process identifiers for internal container correlation."""

    result = run_command(
        [
            "nvidia-smi",
            "--query-compute-apps=gpu_uuid,pid,used_gpu_memory",
            "--format=csv,noheader,nounits",
        ]
    )
    if result.returncode != 0:
        return []
    applications: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            process_id = int(parts[1])
        except ValueError:
            continue
        applications.append(
            {
                "gpu_uuid": parts[0],
                "process_id": process_id,
                "memory_mib": parse_number(parts[2]),
            }
        )
    return applications


def query_containers() -> list[dict[str, Any]]:
    """Return running Docker container identifiers and names only."""

    result = run_command(["docker", "ps", "--format", "{{json .}}"])
    if result.returncode != 0:
        return []
    containers: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        container_id = sanitize_label(record.get("ID"), "", 32)
        name = sanitize_label(record.get("Names"), "container", 80)
        if container_id:
            containers.append(
                {
                    "id": container_id,
                    "name": name,
                    "status": sanitize_label(record.get("Status"), "running", 80),
                }
            )
    return containers


def container_process_ids(container_id: str) -> set[int]:
    """Return container PIDs for internal matching without exporting them."""

    result = run_command(["docker", "top", container_id, "-eo", "pid"], timeout=8)
    if result.returncode != 0:
        return set()
    process_ids: set[int] = set()
    for line in result.stdout.splitlines()[1:]:
        candidate = line.strip().split()[0] if line.strip() else ""
        if candidate.isdigit():
            process_ids.add(int(candidate))
    return process_ids


def container_device_indices(
    container_id: str,
    uuid_to_index: dict[str, int],
) -> set[int]:
    """Read explicit Docker GPU bindings, ignoring ambiguous all-device bindings."""

    result = run_command(
        [
            "docker",
            "inspect",
            "--format",
            "{{json .HostConfig.DeviceRequests}}",
            container_id,
        ],
        timeout=8,
    )
    if result.returncode != 0:
        return set()
    try:
        requests = json.loads(result.stdout.strip() or "[]") or []
    except json.JSONDecodeError:
        return set()
    indexes: set[int] = set()
    for request in requests:
        capabilities = request.get("Capabilities") or []
        if not any("gpu" in group for group in capabilities if isinstance(group, list)):
            continue
        for device_id in request.get("DeviceIDs") or []:
            text = str(device_id)
            if text.isdigit():
                indexes.add(int(text))
            elif text in uuid_to_index:
                indexes.add(uuid_to_index[text])
    return indexes


def project_name(container_name: str, aliases: Iterable[dict[str, Any]]) -> str:
    """Map a container name to a public project label."""

    for alias in aliases:
        pattern = str(alias.get("pattern") or "")
        if pattern and re.search(pattern, container_name, re.IGNORECASE):
            return sanitize_label(alias.get("name"), container_name)
    return sanitize_label(container_name, "Docker workload")


def container_progress(container_id: str) -> dict[str, Any] | None:
    """Parse recent Docker logs without retaining or returning raw text."""

    result = run_command(
        ["docker", "logs", "--tail", "160", container_id],
        timeout=10,
    )
    return parse_progress(f"{result.stdout}\n{result.stderr}")


def map_projects_to_gpus(
    gpus: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Correlate GPU processes and Docker containers, then discard identifiers."""

    if not gpus:
        return
    uuid_to_index = {str(gpu["_uuid"]): int(gpu["index"]) for gpu in gpus}
    gpu_by_index = {int(gpu["index"]): gpu for gpu in gpus}
    applications = query_compute_apps()
    containers = query_containers()
    aliases = config.get("project_aliases") or []
    collect_progress = bool(config.get("collect_container_progress", True))
    seen: dict[int, set[str]] = {index: set() for index in gpu_by_index}

    for container in containers:
        process_ids = container_process_ids(container["id"])
        active_indexes = {
            uuid_to_index[app["gpu_uuid"]]
            for app in applications
            if app["process_id"] in process_ids and app["gpu_uuid"] in uuid_to_index
        }
        indexes = set(active_indexes)
        indexes.update(container_device_indices(container["id"], uuid_to_index))
        if not indexes:
            continue
        label = project_name(container["name"], aliases)
        progress = (
            container_progress(container["id"])
            if collect_progress and active_indexes
            else None
        )
        project: dict[str, Any] = {"name": label}
        if progress:
            project["progress_percent"] = round(progress["percent"], 2)
            if progress.get("eta"):
                project["eta"] = progress["eta"]
        for index in sorted(indexes):
            if index not in gpu_by_index or label in seen[index]:
                continue
            gpu_by_index[index]["projects"].append(
                {**project, "active": index in active_indexes}
            )
            seen[index].add(label)

    matched_process_ids = {
        process_id
        for container in containers
        for process_id in container_process_ids(container["id"])
    }
    for app in applications:
        if app["process_id"] in matched_process_ids:
            continue
        index = uuid_to_index.get(app["gpu_uuid"])
        if index is None or "호스트 GPU 작업" in seen[index]:
            continue
        gpu_by_index[index]["projects"].append(
            {"name": "호스트 GPU 작업", "active": True}
        )
        seen[index].add("호스트 GPU 작업")


def read_meminfo() -> dict[str, float]:
    """Read Linux memory totals from procfs."""

    values: dict[str, float] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = parse_number(raw.strip().split()[0]) / (1024 * 1024)
    except (OSError, ValueError):
        return {"used_gib": 0.0, "total_gib": 0.0, "percent": 0.0}
    total = values.get("MemTotal", 0.0)
    available = values.get("MemAvailable", 0.0)
    used = max(0.0, total - available)
    return {
        "used_gib": round(used, 2),
        "total_gib": round(total, 2),
        "percent": round(used / total * 100, 2) if total else 0.0,
    }


def read_uptime() -> float:
    """Read host uptime from procfs."""

    try:
        return parse_number(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, IndexError):
        return 0.0


def collect_system(config: dict[str, Any]) -> dict[str, Any]:
    """Collect host memory, disk, load, and uptime."""

    disk_path = Path(config.get("disk_path") or "/home")
    try:
        usage = shutil.disk_usage(disk_path)
    except OSError:
        usage = shutil.disk_usage("/")
    gib = 1024**3
    disk_total = usage.total / gib
    disk_used = usage.used / gib
    disk_available = usage.free / gib
    usable_capacity = disk_used + disk_available
    try:
        load_1m = os.getloadavg()[0]
    except (AttributeError, OSError):
        load_1m = 0.0
    return {
        "hostname": sanitize_label(socket.gethostname(), "gpu-server"),
        "load_1m": round(load_1m, 2),
        "uptime_seconds": round(read_uptime()),
        "memory": read_meminfo(),
        "disk": {
            "used_gib": round(disk_used, 2),
            "total_gib": round(disk_total, 2),
            "free_gib": round(disk_available, 2),
            "percent": (
                round(disk_used / usable_capacity * 100, 2)
                if usable_capacity
                else 0.0
            ),
        },
    }


def efo_command(config: dict[str, Any], *arguments: str) -> list[str]:
    """Build the configured EFO command without invoking a shell."""

    base = config.get("efo_command") or ["efo"]
    if not isinstance(base, list) or not all(isinstance(item, str) for item in base):
        raise ValueError("efo_command must be a JSON string array")
    return [*base, *arguments]


def parse_json_command(args: Sequence[str]) -> Any:
    """Run a command expected to emit one JSON document."""

    result = run_command(args, timeout=20)
    if result.returncode != 0:
        raise RuntimeError(sanitize_label(result.stderr, "EFO command failed", 200))
    return json.loads(result.stdout)


def task_to_view(task: dict[str, Any]) -> dict[str, Any]:
    """Reduce an EFO task projection to public operational fields."""

    state = str(task.get("state") or "pending").lower()
    lease_active = lease_is_active(task.get("lease"))
    next_action = TASK_NEXT.get(state, "오케스트레이터 확인")
    external_phase: str | None = None
    external_status = task.get("external_status")
    if state == "pending" and isinstance(external_status, dict):
        candidate = str(external_status.get("phase") or "").lower()
        if candidate in EXTERNAL_PROGRESS:
            external_phase = candidate
            next_action = EXTERNAL_NEXT[candidate]
    if state in ACTIVE_STATES and not lease_active:
        next_action = "임대 만료 상태 확인"
    progress = (
        EXTERNAL_PROGRESS[external_phase]
        if external_phase is not None
        else TASK_PROGRESS.get(state, 0)
    )
    return {
        "id": sanitize_label(task.get("id"), "task"),
        "title": sanitize_label(task.get("title"), "Untitled task", 140),
        "owner": sanitize_label(task.get("owner"), "unassigned"),
        "state": state,
        "canonical_state": state,
        "external_phase": external_phase,
        "status_source": (
            "transport_assertion" if external_phase is not None else "canonical"
        ),
        "status_badge": "운반자 보고" if external_phase is not None else None,
        "lease_active": lease_active,
        "progress_percent": progress,
        "next": next_action,
        "updated_at": (
            external_status.get("reported_at")
            if external_phase is not None
            else task.get("updated_at")
        )
        or task.get("created_at")
        or utc_now(),
    }


def lease_is_active(
    lease: Any,
    now: datetime | None = None,
) -> bool:
    """Return whether an EFO lease exists and has not expired."""

    if not isinstance(lease, dict):
        return False
    expires_at = str(lease.get("expires_at") or "")
    try:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    current = now or datetime.now(timezone.utc)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return expires > current


def resolve_signed_identity_groups(
    registered_agents: list[dict[str, Any]],
    *,
    ledger_valid: bool,
) -> dict[str, frozenset[str]]:
    """Resolve only complete, signed alias declarations into identity groups."""

    if not ledger_valid:
        return {}
    records = {
        str(agent["id"]): agent
        for agent in registered_agents
        if isinstance(agent, dict)
        and isinstance(agent.get("id"), str)
        and agent["id"]
    }
    expected_keys = {
        "schema_version",
        "control_principal",
        "model_family",
        "alias_of",
        "alias_chain",
    }
    resolved: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    resolving: set[str] = set()

    def resolve(agent_id: str) -> tuple[str, str, tuple[str, ...]] | None:
        if agent_id in resolved:
            return resolved[agent_id]
        if agent_id in resolving:
            return None
        record = records.get(agent_id)
        identity = record.get("identity") if isinstance(record, dict) else None
        if not isinstance(identity, dict) or set(identity) != expected_keys:
            return None
        if identity.get("schema_version") != 1:
            return None
        principal = identity.get("control_principal")
        model_family = identity.get("model_family")
        alias_of = identity.get("alias_of")
        alias_chain = identity.get("alias_chain")
        if (
            not isinstance(principal, str)
            or not principal.strip()
            or not isinstance(model_family, str)
            or not model_family.strip()
            or (alias_of is not None and not isinstance(alias_of, str))
            or not isinstance(alias_chain, list)
            or not all(isinstance(item, str) and item for item in alias_chain)
            or len(alias_chain) != len(set(alias_chain))
            or agent_id in alias_chain
        ):
            return None

        resolving.add(agent_id)
        try:
            if alias_of is None:
                if alias_chain:
                    return None
                value = (principal, model_family, ())
            else:
                if not alias_of or alias_of == agent_id:
                    return None
                target = resolve(alias_of)
                if target is None:
                    return None
                target_principal, target_family, target_chain = target
                expected_chain = (alias_of, *target_chain)
                if (
                    tuple(alias_chain) != expected_chain
                    or principal != target_principal
                    or model_family != target_family
                ):
                    return None
                value = (principal, model_family, expected_chain)
            resolved[agent_id] = value
            return value
        finally:
            resolving.discard(agent_id)

    for agent_id in sorted(records):
        resolve(agent_id)

    grouped: dict[tuple[str, str], set[str]] = {}
    for agent_id, (principal, model_family, _chain) in resolved.items():
        grouped.setdefault((principal, model_family), set()).add(agent_id)
    return {
        agent_id: frozenset(grouped[(principal, model_family)])
        for agent_id, (principal, model_family, _chain) in resolved.items()
    }


def task_actor_ids(
    raw_task: dict[str, Any],
    trusted_secondary_actors: Iterable[str] = (),
) -> frozenset[str]:
    """Return signed actors for whom a task is relevant without exposing them."""

    actors: set[str] = set()
    trusted = set(trusted_secondary_actors)
    owner = raw_task.get("owner")
    if isinstance(owner, str) and owner:
        actors.add(owner)

    verification = raw_task.get("verification")
    if (
        isinstance(verification, dict)
        and isinstance(verification.get("identity"), dict)
        and isinstance(verification.get("actor"), str)
        and verification["actor"]
        and verification["actor"] in trusted
    ):
        actors.add(verification["actor"])

    external = raw_task.get("external_status")
    if (
        isinstance(external, dict)
        and isinstance(external.get("author_identity"), dict)
        and isinstance(external.get("author"), str)
        and external["author"]
        and external["author"] in trusted
    ):
        actors.add(external["author"])
    return frozenset(actors)


def _task_timestamp(task: dict[str, Any]) -> float:
    value = str(task.get("updated_at") or "")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def choose_agent_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select the task that best describes an agent's current operational state."""

    def sort_key(task: dict[str, Any]) -> tuple[int, float, str]:
        is_live = (
            task.get("external_phase") is not None
            or task.get("state") in LIVE_CARD_STATES
        )
        return (
            0 if is_live else 1,
            -_task_timestamp(task),
            str(task.get("id") or ""),
        )

    return min(tasks, key=sort_key, default=None)


def agent_state(task: dict[str, Any] | None) -> str:
    """Map an EFO task state to a dashboard agent state."""

    task_state = task.get("state") if task else None
    external_phase = task.get("external_phase") if task else None
    if task_state == "pending" and external_phase == "blocked":
        return "blocked"
    if task_state == "pending" and external_phase in {
        "working",
        "reviewing",
        "ready",
    }:
        return "working"
    if task_state in ACTIVE_STATES and not task.get("lease_active", False):
        return "blocked"
    if task_state in ACTIVE_STATES:
        return "working"
    if task_state in {"blocked", "rejected", "invalidated"}:
        return "blocked"
    return "waiting"


def workflow_progress(tasks: list[dict[str, Any]]) -> float:
    """Return a workflow-phase indicator, not a scientific performance metric."""

    if not tasks:
        return 0.0
    return round(
        sum(
            float(
                task.get(
                    "progress_percent",
                    TASK_PROGRESS.get(str(task.get("state")), 0),
                )
            )
            for task in tasks
        )
        / len(tasks),
        2,
    )


def collect_activity(
    config: dict[str, Any],
    workspace_path: str,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Read a bounded, sanitized projection of signed EFO ledger events."""

    ledger_path = Path(
        config.get("efo_ledger_file")
        or Path(workspace_path) / "ledger" / "events.jsonl"
    ).expanduser()
    task_titles = {
        str(task.get("id")): str(task.get("title"))
        for task in tasks
        if task.get("id") and task.get("title")
    }
    actor_aliases = {
        str(key): sanitize_label(value, str(key), 60)
        for key, value in (config.get("activity_actor_aliases") or {}).items()
    }
    events: deque[dict[str, Any]] = deque(maxlen=ACTIVITY_LIMIT)
    try:
        ledger_handle = ledger_path.open("r", encoding="utf-8")
    except OSError:
        return []

    with ledger_handle:
        for line in ledger_handle:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            timestamp = str(event.get("timestamp") or "")
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            action = sanitize_label(event.get("action"), "ledger.event", 60)
            label, category = ACTIVITY_ACTIONS.get(
                action,
                ("원장 이벤트", "system"),
            )
            actor = sanitize_label(event.get("actor"), "system", 60)
            task_id = sanitize_label(event.get("task_id"), "", 80)
            payload = (
                event.get("payload") if isinstance(event.get("payload"), dict) else {}
            )
            task_snapshot = (
                payload.get("task") if isinstance(payload.get("task"), dict) else {}
            )
            title = sanitize_label(
                task_snapshot.get("title") or task_titles.get(task_id),
                "",
                160,
            )
            try:
                sequence = int(event.get("sequence"))
            except (TypeError, ValueError):
                continue
            if sequence < 1:
                continue
            events.append(
                {
                    "sequence": sequence,
                    "at": timestamp,
                    "actor": actor,
                    "actor_name": actor_aliases.get(actor, actor),
                    "action": action,
                    "label": label,
                    "category": category,
                    "task_id": task_id or None,
                    "title": title or None,
                }
            )
    return list(events)


def collect_efo(
    config: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Read EFO agents, tasks, and signed ledger state."""

    workspace_path = str(config.get("efo_workspace") or "/home/shoon/efo_ws")
    alerts: list[dict[str, Any]] = []
    try:
        status_payload = parse_json_command(
            efo_command(config, "status", workspace_path)
        )
        registered_agents = parse_json_command(
            efo_command(config, "agent", "list", workspace_path)
        )
        raw_tasks = status_payload.get("tasks") or []
        ledger = status_payload.get("status", {}).get("ledger") or {}
    except (RuntimeError, json.JSONDecodeError, ValueError) as exc:
        raw_tasks = []
        registered_agents = []
        ledger = {"valid": False, "event_count": 0}
        alerts.append(
            {
                "severity": "warning",
                "title": "EFO 원장 수집 실패",
                "message": sanitize_label(exc, "EFO command failed", 180),
                "at": utc_now(),
            }
        )

    task_records = [
        (task, task_to_view(task))
        for task in raw_tasks
        if isinstance(task, dict)
    ]
    tasks = [view for _raw, view in task_records]
    registered_ids = {
        str(agent.get("id"))
        for agent in registered_agents
        if isinstance(agent, dict) and agent.get("id")
    }
    ledger_valid = ledger.get("valid") is True
    identity_groups = resolve_signed_identity_groups(
        registered_agents,
        ledger_valid=ledger_valid,
    )
    profiles = config.get("agents") or [
        {
            "id": "codex",
            "efo_id": "codex",
            "name": "Codex",
            "role": "메타 오케스트레이터",
        },
        {
            "id": "claude-a",
            "efo_id": "claude-a",
            "name": "Claude A",
            "role": "연구·분석 작업자",
        },
        {
            "id": "claude-b",
            "efo_id": "claude-b",
            "name": "Claude B",
            "role": "구현·검증 작업자",
        },
        {
            "id": "antigravity",
            "efo_id": "antigravity",
            "name": "Antigravity",
            "role": "연구 운영·기록",
        },
    ]
    agents: list[dict[str, Any]] = []
    for profile in profiles:
        efo_id = str(profile.get("efo_id") or profile.get("id"))
        profile_id = str(profile.get("id") or efo_id)
        relevant_actor_ids = {efo_id, profile_id}
        relevant_actor_ids.update(identity_groups.get(efo_id, ()))
        relevant_actor_ids.update(identity_groups.get(profile_id, ()))
        owned = (
            [
                view
                for raw, view in task_records
                if task_actor_ids(raw, identity_groups) & relevant_actor_ids
            ]
            if ledger_valid
            else []
        )
        current = choose_agent_task(owned)
        configured_state = str(profile.get("state") or "").lower()
        if configured_state not in {"waiting", "offline"}:
            configured_state = ""
        missing_state = configured_state or (
            "waiting" if profile.get("allow_unregistered", True) else "offline"
        )
        state = (
            agent_state(current)
            if current
            else ("waiting" if efo_id in registered_ids else missing_state)
        )
        agents.append(
            {
                "id": sanitize_label(profile_id, efo_id),
                "name": sanitize_label(profile.get("name"), efo_id),
                "role": sanitize_label(profile.get("role"), "작업자", 100),
                "state": state,
                "current": current["title"] if current else "배정 대기",
                "current_task_id": current["id"] if current else None,
                "next": current["next"] if current else "오케스트레이터 지시 대기",
                "progress_percent": current["progress_percent"] if current else 0,
                "status_source": current["status_source"] if current else "none",
                "status_badge": current["status_badge"] if current else None,
                "updated_at": current["updated_at"] if current else None,
            }
        )
    activity = (
        collect_activity(config, workspace_path, tasks)
        if ledger.get("valid") is True
        else []
    )
    return agents, tasks, ledger, alerts, activity


def history_point(gpus: list[dict[str, Any]], at: str) -> dict[str, Any]:
    """Reduce GPU state to chart-safe fields."""

    return {
        "at": at,
        "gpus": [
            {
                "index": gpu["index"],
                "utilization_percent": gpu["utilization_percent"],
                "temperature_c": gpu["temperature_c"],
                "memory_percent": round(
                    gpu["memory_used_mib"] / gpu["memory_total_mib"] * 100,
                    2,
                )
                if gpu["memory_total_mib"]
                else 0.0,
            }
            for gpu in gpus
        ],
    }


def load_history(path: Path) -> list[dict[str, Any]]:
    """Load the rolling chart history, returning an empty list on corruption."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return value[-(HISTORY_LIMIT - 1) :] if isinstance(value, list) else []


def save_history(path: Path, history: list[dict[str, Any]]) -> None:
    """Atomically persist bounded history with owner-only permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(history[-HISTORY_LIMIT:], handle, ensure_ascii=False)
            handle.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_alerts(
    gpus: list[dict[str, Any]],
    system: dict[str, Any],
    inherited: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build deterministic resource alerts."""

    alerts = list(inherited)
    for gpu in gpus:
        if gpu["temperature_c"] >= 82:
            alerts.append(
                {
                    "severity": "critical",
                    "title": f"GPU {gpu['index']} 고온",
                    "message": f"현재 {gpu['temperature_c']:.0f}°C",
                    "at": utc_now(),
                }
            )
    disk_percent = parse_number(system.get("disk", {}).get("percent"))
    if disk_percent >= 90:
        alerts.append(
            {
                "severity": "critical",
                "title": "저장 공간 부족",
                "message": f"디스크 사용률 {disk_percent:.1f}%",
                "at": utc_now(),
            }
        )
    return alerts[:100]


def strip_internal_fields(gpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove correlation-only identifiers before serialization."""

    return [
        {key: value for key, value in gpu.items() if not key.startswith("_")}
        for gpu in gpus
    ]


def collect_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    """Collect one complete sanitized operations snapshot."""

    generated_at = utc_now()
    gpus, gpu_alerts = query_gpus()
    map_projects_to_gpus(gpus, config)
    system = collect_system(config)
    agents, tasks, ledger, efo_alerts, activity = collect_efo(config)
    history_path = Path(
        config.get("history_file")
        or "~/.local/state/efo-monitor/history.json"
    ).expanduser()
    history = load_history(history_path)
    history.append(history_point(gpus, generated_at))
    history = history[-HISTORY_LIMIT:]
    save_history(history_path, history)
    safe_gpus = strip_internal_fields(gpus)

    workspace = config.get("workspace") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "collection_interval_seconds": int(
            config.get("collection_interval_seconds") or 120
        ),
        "source": {
            "mode": "collector",
            "host": sanitize_label(
                config.get("display_host") or system["hostname"],
                "SSH GPU 서버",
            ),
            "collector": COLLECTOR_VERSION,
            "ledger": {
                "valid": bool(ledger.get("valid", ledger.get("ok", False))),
                "event_count": int(
                    ledger.get("events", ledger.get("event_count", 0)) or 0
                ),
            },
        },
        "workspace": {
            "name": sanitize_label(workspace.get("name"), "System 1.5"),
            "objective": sanitize_label(
                workspace.get("objective"),
                "검증 가능한 근거를 남기며 연구를 완성합니다.",
                240,
            ),
            "next_milestone": sanitize_label(
                workspace.get("next_milestone"),
                "다음 EFO 검증 게이트",
                180,
            ),
            "workflow_progress_percent": workflow_progress(tasks),
        },
        "agents": agents,
        "tasks": tasks,
        "activity": activity,
        "gpus": safe_gpus,
        "system": system,
        "history": history,
        "alerts": build_alerts(
            safe_gpus,
            system,
            [*gpu_alerts, *efo_alerts],
        ),
    }


def read_secret(config: dict[str, Any]) -> str:
    """Read the ingest secret from a protected file or process environment."""

    variable = str(config.get("ingest_secret_env") or "EFO_INGEST_SECRET")
    if os.environ.get(variable):
        return os.environ[variable]
    secret_path = Path(
        config.get("ingest_secret_file")
        or "~/.config/efo-monitor/ingest-secret"
    ).expanduser()
    secret = secret_path.read_text(encoding="utf-8").strip()
    if not secret:
        raise RuntimeError(f"ingest secret is empty: {secret_path}")
    return secret


def submit_snapshot(
    endpoint: str,
    secret: str,
    snapshot: dict[str, Any],
    timeout: float = 20.0,
) -> dict[str, Any]:
    """HMAC-sign and submit one snapshot to the Cloudflare endpoint."""

    body = json.dumps(
        snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "user-agent": COLLECTOR_VERSION,
            "x-efo-timestamp": timestamp,
            "x-efo-signature": f"sha256={signature}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"ingest HTTP {exc.code}: {detail}") from exc


def load_config(path: Path) -> dict[str, Any]:
    """Load and minimally validate collector configuration."""

    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("collector config must be a JSON object")
    interval = int(config.get("collection_interval_seconds") or 120)
    if not 10 <= interval <= 3600:
        raise ValueError("collection_interval_seconds must be between 10 and 3600")
    return config


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse collector command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("~/.config/efo-monitor/config.json").expanduser(),
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the sanitized snapshot.",
    )
    parser.add_argument(
        "--no-submit",
        action="store_true",
        help="Collect and validate locally without HTTP submission.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Collect once; scheduling is handled by a systemd user timer."""

    args = parse_args(argv)
    try:
        config = load_config(args.config)
        snapshot = collect_snapshot(config)
        if args.stdout:
            print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        if not args.no_submit:
            endpoint = str(config.get("endpoint") or "").strip()
            if not endpoint.startswith("https://"):
                raise ValueError("endpoint must use HTTPS")
            result = submit_snapshot(endpoint, read_secret(config), snapshot)
            print(
                json.dumps(
                    {
                        "ok": bool(result.get("ok")),
                        "generated_at": snapshot["generated_at"],
                        "gpu_count": len(snapshot["gpus"]),
                        "task_count": len(snapshot["tasks"]),
                    },
                    ensure_ascii=False,
                )
            )
        return 0
    except Exception as exc:  # noqa: BLE001 - service entrypoint must emit one error
        print(f"efo-monitor: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
