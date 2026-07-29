"""Task schemas and state transition rules."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from pathlib import PurePosixPath
import re
from typing import Any

from .errors import ConfigurationError, TransitionError
from .identity import (
    validate_capabilities,
    validate_independence_dimensions,
)
from .util import parse_utc, utc_now, validate_agent_id, validate_task_id

TASK_STATES = {
    "pending",
    "claimed",
    "running",
    "revoking",
    "blocked",
    "submitted",
    "verified",
    "rejected",
    "archived",
    "invalidated",
}

TRANSITIONS = {
    "pending": {"claimed", "submitted"},
    "claimed": {"running", "blocked", "revoking"},
    "running": {"blocked", "submitted", "revoking"},
    "revoking": {"blocked"},
    "blocked": {"pending"},
    "submitted": {"verified", "rejected"},
    "rejected": {"pending"},
    "verified": {"archived", "invalidated"},
    "archived": {"invalidated"},
    "invalidated": {"pending"},
}

GIT_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
GIT_BRANCH_REF_RE = re.compile(
    r"^refs/heads/[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9_-])?$"
)


def _valid_git_branch_ref(value: Any) -> bool:
    if not isinstance(value, str) or not GIT_BRANCH_REF_RE.fullmatch(value):
        return False
    branch = value.removeprefix("refs/heads/")
    parts = branch.split("/")
    return (
        ".." not in branch
        and "@{" not in branch
        and "//" not in branch
        and all(
            part
            and not part.startswith(".")
            and not part.endswith(".")
            and not part.endswith(".lock")
            for part in parts
        )
    )


def _normalize_repo_paths(values: list[str] | None) -> list[str]:
    result: set[str] = set()
    for value in values or []:
        if not isinstance(value, str) or not value.strip() or "\\" in value:
            raise ConfigurationError(
                "delivery_policy.required_repo_paths must be Git-style paths"
            )
        path = PurePosixPath(value.strip())
        if path.is_absolute() or ".." in path.parts:
            raise ConfigurationError(f"Unsafe Git repository path: {value!r}")
        result.add(path.as_posix())
    return sorted(result)


def new_task(
    *,
    task_id: str,
    title: str,
    description: str,
    owner: str,
    created_by: str,
    prerequisites: list[str] | None = None,
    allowed_write_roots: list[str] | None = None,
    permissions: dict[str, bool] | None = None,
    gates: dict[str, Any] | None = None,
    task_type: str = "general",
    risk_tier: str = "medium",
    required_capabilities: list[str] | None = None,
    resource_locks: list[str] | None = None,
    verification_policy: dict[str, Any] | None = None,
    delivery_policy: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create a validated task record in the pending state."""

    now = utc_now()
    normalized_delivery = {
        "allow_proxy": False,
        "git_remote_name": None,
        "git_remote_url": None,
        "git_ref": None,
        "required_repo_paths": [],
        **(delivery_policy or {}),
    }
    delivery_paths = normalized_delivery.get("required_repo_paths")
    if not isinstance(delivery_paths, list):
        raise ConfigurationError(
            "delivery_policy.required_repo_paths must be a list"
        )
    normalized_delivery["required_repo_paths"] = _normalize_repo_paths(
        delivery_paths
    )
    record = {
        "schema_version": 1,
        "id": validate_task_id(task_id),
        "title": title.strip(),
        "description": description.strip(),
        "owner": validate_agent_id(owner),
        "created_by": validate_agent_id(created_by),
        "state": "pending",
        "revision": 1,
        "attempt": 0,
        "created_at": now,
        "updated_at": now,
        "prerequisites": prerequisites or [],
        "allowed_write_roots": allowed_write_roots or [],
        "task_type": task_type.strip().lower(),
        "risk_tier": risk_tier.strip().lower(),
        "required_capabilities": validate_capabilities(required_capabilities),
        "resource_locks": sorted(set(resource_locks or [])),
        "permissions": {
            "gpu": False,
            "performance_metrics": False,
            "network": False,
            "outcome_data": False,
            **(permissions or {}),
        },
        "gates": {
            "require_validation": True,
            "allow_skips": False,
            "require_known_answer_check": True,
            "require_independent_verification": True,
            **(gates or {}),
        },
        "verification_policy": {
            "required_attestations": 0,
            "allowed_verifiers": [],
            "independence_dimensions": ["actor"],
            **(verification_policy or {}),
        },
        "delivery_policy": normalized_delivery,
        "idempotency_key": idempotency_key or task_id,
        "lease": None,
        "result": None,
        "verification": None,
        "verification_attestations": [],
        "blocked_reason": None,
        "revocation": None,
        "execution": None,
    }
    validate_task(record)
    return record


def validate_task(task: dict[str, Any]) -> None:
    """Validate the fields needed by the broker."""

    validate_task_id(str(task.get("id", "")))
    validate_agent_id(str(task.get("owner", "")))
    state = task.get("state")
    if state not in TASK_STATES:
        raise ConfigurationError(f"Unknown task state: {state!r}")
    if not str(task.get("title", "")).strip():
        raise ConfigurationError("Task title cannot be empty")
    if not isinstance(task.get("revision"), int) or task["revision"] < 1:
        raise ConfigurationError("Task revision must be a positive integer")
    if not isinstance(task.get("prerequisites"), list):
        raise ConfigurationError("Task prerequisites must be a list")
    task_type = task.get("task_type", "general")
    if not isinstance(task_type, str) or not task_type.strip():
        raise ConfigurationError("Task type must be a non-empty string")
    risk_tier = task.get("risk_tier", "medium")
    if risk_tier not in {"low", "medium", "high", "critical"}:
        raise ConfigurationError("Task risk tier must be low, medium, high, or critical")
    required_capabilities = task.get("required_capabilities", [])
    if not isinstance(required_capabilities, list):
        raise ConfigurationError("Task required_capabilities must be a list")
    validate_capabilities(required_capabilities)
    resource_locks = task.get("resource_locks", [])
    if (
        not isinstance(resource_locks, list)
        or not all(isinstance(item, str) and item.strip() for item in resource_locks)
    ):
        raise ConfigurationError("Task resource_locks must be non-empty strings")
    if len(resource_locks) != len(set(resource_locks)):
        raise ConfigurationError("Task resource_locks must be unique")
    if not isinstance(task.get("permissions"), dict):
        raise ConfigurationError("Task permissions must be an object")
    if not isinstance(task.get("gates"), dict):
        raise ConfigurationError("Task gates must be an object")
    policy = task.get(
        "verification_policy",
        {
            "required_attestations": 0,
            "allowed_verifiers": [],
            "independence_dimensions": ["actor"],
        },
    )
    if not isinstance(policy, dict):
        raise ConfigurationError("Task verification_policy must be an object")
    required_attestations = policy.get("required_attestations", 0)
    if (
        not isinstance(required_attestations, int)
        or isinstance(required_attestations, bool)
        or required_attestations < 0
    ):
        raise ConfigurationError(
            "verification_policy.required_attestations must be a non-negative integer"
        )
    allowed_verifiers = policy.get("allowed_verifiers", [])
    if not isinstance(allowed_verifiers, list):
        raise ConfigurationError(
            "verification_policy.allowed_verifiers must be a list"
        )
    for verifier in allowed_verifiers:
        validate_agent_id(str(verifier))
    validate_independence_dimensions(
        policy.get("independence_dimensions", ["actor"])
    )
    delivery = task.get(
        "delivery_policy",
        {
            "allow_proxy": False,
            "git_remote_name": None,
            "git_remote_url": None,
            "git_ref": None,
            "required_repo_paths": [],
        },
    )
    if not isinstance(delivery, dict):
        raise ConfigurationError("Task delivery_policy must be an object")
    allow_proxy = delivery.get("allow_proxy", False)
    if not isinstance(allow_proxy, bool):
        raise ConfigurationError("delivery_policy.allow_proxy must be boolean")
    remote_name = delivery.get("git_remote_name")
    remote_url = delivery.get("git_remote_url")
    source_ref = delivery.get("git_ref")
    paths = delivery.get("required_repo_paths", [])
    if not isinstance(paths, list):
        raise ConfigurationError(
            "delivery_policy.required_repo_paths must be a list"
        )
    normalized_paths = _normalize_repo_paths(paths)
    if paths != normalized_paths:
        raise ConfigurationError(
            "delivery_policy.required_repo_paths must be unique and sorted"
        )
    if allow_proxy:
        if (
            not isinstance(remote_name, str)
            or not GIT_REMOTE_NAME_RE.fullmatch(remote_name)
        ):
            raise ConfigurationError(
                "Proxy delivery requires a safe delivery_policy.git_remote_name"
            )
        if not isinstance(remote_url, str) or not remote_url.strip():
            raise ConfigurationError(
                "Proxy delivery requires delivery_policy.git_remote_url"
            )
        if not _valid_git_branch_ref(source_ref):
            raise ConfigurationError(
                "Proxy delivery requires delivery_policy.git_ref as a full "
                "refs/heads/<branch> reference"
            )
        if not paths:
            raise ConfigurationError(
                "Proxy delivery requires at least one preregistered repository path"
            )
    attestations = task.get("verification_attestations", [])
    if not isinstance(attestations, list):
        raise ConfigurationError("Task verification_attestations must be a list")
    revocation = task.get("revocation")
    if revocation is not None and not isinstance(revocation, dict):
        raise ConfigurationError("Task revocation must be an object or null")
    execution = task.get("execution")
    if execution is not None and not isinstance(execution, dict):
        raise ConfigurationError("Task execution must be an object or null")


def transition(task: dict[str, Any], target: str, **updates: Any) -> dict[str, Any]:
    """Return a copy of a task after a legal state transition."""

    source = task["state"]
    if target not in TRANSITIONS.get(source, set()):
        raise TransitionError(f"Task {task['id']} cannot transition {source} -> {target}")
    result = deepcopy(task)
    result["state"] = target
    result["revision"] += 1
    result["updated_at"] = utc_now()
    result.update(updates)
    validate_task(result)
    return result


def lease_expired(task: dict[str, Any], now: str | None = None) -> bool:
    """Return whether an active task lease has expired."""

    lease = task.get("lease")
    if not lease:
        return False
    current = parse_utc(now or utc_now())
    return current >= parse_utc(lease["expires_at"])


def lease_expiry(seconds: int, now: str | None = None) -> str:
    """Build a UTC lease expiration timestamp."""

    if seconds < 10:
        raise ConfigurationError("Lease duration must be at least 10 seconds")
    current = parse_utc(now or utc_now())
    return (current + timedelta(seconds=seconds)).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
