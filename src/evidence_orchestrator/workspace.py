"""Transactional workspace broker and task state machine."""

from __future__ import annotations

import hashlib
import secrets
from copy import deepcopy
from itertools import combinations
from pathlib import Path
from typing import Any

from .archive import archive_evidence_bundle
from .errors import (
    AuthorizationError,
    ConfigurationError,
    EvidenceError,
    IntegrityError,
    LeaseError,
    TransitionError,
)
from .evidence import validate_manifest, validate_submission
from .identity import (
    evaluate_independence,
    profile_snapshot,
    validate_capabilities,
    validate_identity_value,
    validate_independence_dimensions,
)
from .ledger import Ledger
from .lock import FileLock
from .model import lease_expired, lease_expiry, new_task, transition, validate_task
from .provenance import verify_git_delivery
from .util import (
    atomic_write_json,
    is_relative_to,
    read_json,
    utc_now,
    validate_agent_id,
    validate_task_id,
)


class Workspace:
    """Coordinate agents through a local evidence-gated workspace."""

    CONFIG_VERSION = 1

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.control_dir = self.root / ".efo"
        self.config_path = self.control_dir / "workspace.json"
        self.agents_dir = self.root / "agents"
        self.tasks_dir = self.root / "tasks"
        self.reports_dir = self.root / "reports"
        self.runs_dir = self.root / "runs"
        self.shared_dir = self.root / "shared"
        self.archive_dir = self.root / "archive"
        self.submissions_dir = self.root / "submissions"
        self.ledger = Ledger(
            self.root / "ledger" / "events.jsonl",
            self.control_dir / "locks" / "ledger.lock",
            self.control_dir / "ledger.key",
        )
        if not self.config_path.is_file():
            raise ConfigurationError(
                f"Not an Evidence First Orchestrator workspace: {self.root}"
            )
        self.config = read_json(self.config_path)
        if self.config.get("schema_version") != self.CONFIG_VERSION:
            raise ConfigurationError("Unsupported workspace schema version")
        if self.ledger.path.exists() and self.ledger.key_path.exists():
            events = self.ledger.read()
            if events:
                self.ledger.verify()
                initialization = next(
                    (
                        event
                        for event in events
                        if event.get("action") == "workspace.initialized"
                    ),
                    None,
                )
                expected_config = (
                    initialization.get("payload", {}).get("config")
                    if initialization
                    else None
                )
                if expected_config != self.config:
                    raise IntegrityError(
                        "Workspace configuration differs from the signed ledger"
                    )

    @classmethod
    def initialize(
        cls,
        root: str | Path,
        *,
        name: str,
        orchestrator: str = "antigravity",
        preset: str | None = None,
    ) -> Workspace:
        """Create a workspace and its initial orchestrator identity."""

        root_path = Path(root).resolve()
        control_dir = root_path / ".efo"
        config_path = control_dir / "workspace.json"
        if config_path.exists():
            raise ConfigurationError(f"Workspace already initialized: {root_path}")
        orchestrator = validate_agent_id(orchestrator)
        for directory in (
            control_dir / "locks" / "tasks",
            root_path / "agents",
            root_path / "tasks",
            root_path / "reports",
            root_path / "runs",
            root_path / "shared",
            root_path / "archive",
            root_path / "submissions",
            root_path / "ledger",
        ):
            directory.mkdir(parents=True, exist_ok=True)
        (control_dir / ".gitignore").write_text(
            "ledger.key\nlocks/\n",
            encoding="utf-8",
        )
        (root_path / "runs" / ".gitignore").write_text(
            "*\n!.gitignore\n",
            encoding="utf-8",
        )
        config = {
            "schema_version": cls.CONFIG_VERSION,
            "workspace_id": secrets.token_hex(16),
            "name": name.strip() or root_path.name,
            "orchestrator": orchestrator,
            "created_at": utc_now(),
            "defaults": {
                "lease_seconds": 1800,
                "permissions": {
                    "gpu": False,
                    "performance_metrics": False,
                    "network": False,
                    "outcome_data": False,
                },
                "gates": {
                    "require_validation": True,
                    "allow_skips": False,
                    "require_known_answer_check": True,
                    "require_independent_verification": True,
                },
                "max_evidence_bytes": 50 * 1024 * 1024,
            },
        }
        atomic_write_json(config_path, config)
        workspace = cls(root_path)
        workspace.ledger.initialize()
        workspace.ledger.append(
            actor=orchestrator,
            action="workspace.initialized",
            task_id=None,
            payload={"config": config},
        )
        workspace._commit_agent(
            actor=orchestrator,
            record={
                "schema_version": 1,
                "id": orchestrator,
                "role": "orchestrator",
                "mode": "manual",
                "command": None,
                "created_at": utc_now(),
                "write_roots": ["tasks", "shared", "archive"],
                "identity": {
                    "controller_id": orchestrator,
                    "provider": "unknown",
                    "model_family": "unknown",
                },
                "capabilities": ["orchestrate", "proxy_submit", "verify"],
                "max_concurrency": 1,
                "active": True,
            },
            require_orchestrator=True,
        )
        if preset == "antigravity-codex-claude":
            workspace.add_agent(
                actor=orchestrator,
                agent_id="codex",
                role="worker",
                mode="manual",
                controller_id="codex",
                provider="openai",
                model_family="codex",
                capabilities=["code", "research", "verify"],
            )
            workspace.add_agent(
                actor=orchestrator,
                agent_id="claude",
                role="worker",
                mode="manual",
                controller_id="claude",
                provider="anthropic",
                model_family="claude-code",
                capabilities=["code", "review"],
            )
        elif preset == "meta-4-agent":
            workspace.update_agent(
                actor=orchestrator,
                agent_id=orchestrator,
                controller_id=orchestrator,
                provider="unknown",
                model_family="unknown",
                capabilities=[
                    "data-audit",
                    "experiment-ops",
                    "gpu-schedule",
                    "orchestrate",
                    "proxy_submit",
                    "verify",
                ],
            )
            workspace.add_agent(
                actor=orchestrator,
                agent_id="codex",
                role="worker",
                mode="manual",
                controller_id="codex",
                provider="openai",
                model_family="codex",
                capabilities=["code", "meta-orchestrate", "research", "verify"],
            )
            workspace.add_agent(
                actor=orchestrator,
                agent_id="claude-a",
                role="worker",
                mode="manual",
                controller_id="claude-a",
                provider="anthropic",
                model_family="claude-code",
                capabilities=["code", "implementation"],
            )
            workspace.add_agent(
                actor=orchestrator,
                agent_id="claude-b",
                role="verifier",
                mode="manual",
                controller_id="claude-b",
                provider="anthropic",
                model_family="claude-code",
                capabilities=["adversarial-review", "regression-test", "verify"],
            )
        elif preset is not None:
            raise ConfigurationError(f"Unknown workspace preset: {preset}")
        return workspace

    @property
    def orchestrator(self) -> str:
        orchestrator = str(self.config["orchestrator"])
        if not self.ledger.path.exists():
            return orchestrator
        for event in self.ledger.read():
            if event.get("action") != "workspace.orchestrator_transferred":
                continue
            target = event.get("payload", {}).get("to")
            if isinstance(target, str):
                orchestrator = target
        return orchestrator

    def _agent_path(self, agent_id: str) -> Path:
        return self.agents_dir / f"{validate_agent_id(agent_id)}.json"

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{validate_task_id(task_id)}.json"

    def _task_lock(self, task_id: str) -> FileLock:
        return FileLock(self.control_dir / "locks" / "tasks" / f"{task_id}.lock")

    def _creation_lock(self) -> FileLock:
        return FileLock(self.control_dir / "locks" / "task-create.lock")

    def _agent_lock(self) -> FileLock:
        return FileLock(self.control_dir / "locks" / "agent-create.lock")

    def _orchestrator_lock(self) -> FileLock:
        return FileLock(self.control_dir / "locks" / "orchestrator.lock")

    def _resource_lock(self) -> FileLock:
        return FileLock(self.control_dir / "locks" / "resources.lock")

    def _write_agent(self, record: dict[str, Any]) -> None:
        path = self._agent_path(record["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        (self.reports_dir / record["id"]).mkdir(parents=True, exist_ok=True)
        (self.runs_dir / record["id"]).mkdir(parents=True, exist_ok=True)
        atomic_write_json(path, record)

    def _commit_agent(
        self,
        *,
        actor: str,
        record: dict[str, Any],
        action: str = "agent.added",
        require_orchestrator: bool = False,
    ) -> dict[str, Any]:
        self.ledger.append(
            actor=actor,
            action=action,
            task_id=None,
            payload={"agent": record},
            expected_orchestrator=actor if require_orchestrator else None,
        )
        self._write_agent(record)
        return record

    def _signed_agents(self) -> dict[str, dict[str, Any]]:
        self.ledger.verify()
        signed: dict[str, dict[str, Any]] = {}
        for event in self.ledger.read():
            if event.get("action") not in {"agent.added", "agent.updated"}:
                continue
            record = event.get("payload", {}).get("agent")
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                signed[record["id"]] = record
        return signed

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        """Return one registered agent."""

        path = self._agent_path(agent_id)
        if not path.is_file():
            raise AuthorizationError(f"Unknown agent: {agent_id}")
        record = read_json(path)
        if self._signed_agents().get(agent_id) != record:
            raise IntegrityError(
                f"Agent {agent_id} registration differs from the signed ledger"
            )
        return record

    def list_agents(self) -> list[dict[str, Any]]:
        """Return all registered agents."""

        signed = self._signed_agents()
        records: list[dict[str, Any]] = []
        for path in sorted(self.agents_dir.glob("*.json")):
            record = read_json(path)
            agent_id = record.get("id")
            if signed.get(agent_id) != record:
                raise IntegrityError(
                    f"Agent {agent_id!r} registration differs from the signed ledger"
                )
            records.append(record)
        if set(signed) != {record["id"] for record in records}:
            raise IntegrityError("One or more signed agent projections are missing")
        return records

    def _require_orchestrator(self, actor: str) -> None:
        agent = self.get_agent(actor)
        if actor != self.orchestrator:
            raise AuthorizationError(
                f"Only orchestrator {self.orchestrator!r} may perform this action"
            )
        if agent.get("active", True) is not True:
            raise AuthorizationError("The current orchestrator is inactive")

    def add_agent(
        self,
        *,
        actor: str,
        agent_id: str,
        role: str = "worker",
        mode: str = "manual",
        command: list[str] | None = None,
        prompt_stdin: bool = False,
        write_roots: list[str] | None = None,
        controller_id: str | None = None,
        provider: str = "unknown",
        model_family: str = "unknown",
        capabilities: list[str] | None = None,
        max_concurrency: int = 1,
        active: bool = True,
    ) -> dict[str, Any]:
        """Register a worker or verifier. Only the orchestrator may do this."""

        self._require_orchestrator(actor)
        agent_id = validate_agent_id(agent_id)
        if role not in {"worker", "verifier"}:
            raise ConfigurationError("Agent role must be worker or verifier")
        if mode not in {"manual", "command"}:
            raise ConfigurationError("Agent mode must be manual or command")
        if mode == "command" and (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) and item for item in command)
        ):
            raise ConfigurationError("Command-mode agents need a non-empty command list")
        if mode == "manual" and prompt_stdin:
            raise ConfigurationError(
                "Manual-mode agents cannot receive prompts on command stdin"
            )
        if max_concurrency < 1:
            raise ConfigurationError("Agent max_concurrency must be positive")
        record = {
            "schema_version": 1,
            "id": agent_id,
            "role": role,
            "mode": mode,
            "command": command,
            "prompt_stdin": prompt_stdin,
            "created_at": utc_now(),
            "write_roots": write_roots or [f"reports/{agent_id}", f"runs/{agent_id}"],
            "identity": {
                "controller_id": validate_identity_value(
                    controller_id or agent_id,
                    field="controller_id",
                ),
                "provider": validate_identity_value(provider, field="provider"),
                "model_family": validate_identity_value(
                    model_family,
                    field="model_family",
                ),
            },
            "capabilities": validate_capabilities(capabilities),
            "max_concurrency": max_concurrency,
            "active": active,
        }
        with self._agent_lock():
            path = self._agent_path(agent_id)
            if path.exists() or agent_id in self._signed_agents():
                raise ConfigurationError(f"Agent already exists: {agent_id}")
            return self._commit_agent(
                actor=actor,
                record=record,
                require_orchestrator=True,
            )

    def configure_agent_delivery(
        self,
        *,
        actor: str,
        agent_id: str,
        mode: str,
        command: list[str] | None = None,
        prompt_stdin: bool = False,
    ) -> dict[str, Any]:
        """Append a signed update to an agent's task-delivery configuration."""

        self._require_orchestrator(actor)
        if mode not in {"manual", "command"}:
            raise ConfigurationError("Agent mode must be manual or command")
        if mode == "command" and (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) and item for item in command)
        ):
            raise ConfigurationError("Command-mode agents need a non-empty command list")
        if mode == "manual" and (command is not None or prompt_stdin):
            raise ConfigurationError(
                "Manual-mode delivery cannot define a command or prompt stdin"
            )

        with self._agent_lock():
            record = deepcopy(self.get_agent(agent_id))
            active = [
                task["id"]
                for task in self.list_tasks()
                if task.get("owner") == agent_id
                and task.get("state") in {"claimed", "running", "revoking"}
            ]
            if active:
                raise ConfigurationError(
                    "Cannot change delivery while the agent owns active tasks: "
                    + ", ".join(sorted(active))
                )
            record["mode"] = mode
            record["command"] = command if mode == "command" else None
            record["prompt_stdin"] = prompt_stdin if mode == "command" else False
            record["updated_at"] = utc_now()
            return self._commit_agent(
                actor=actor,
                record=record,
                action="agent.updated",
                require_orchestrator=True,
            )

    def update_agent(
        self,
        *,
        actor: str,
        agent_id: str,
        controller_id: str,
        provider: str,
        model_family: str,
        capabilities: list[str] | None = None,
        max_concurrency: int = 1,
        active: bool = True,
    ) -> dict[str, Any]:
        """Append a signed agent profile update for capability-aware routing."""

        self._require_orchestrator(actor)
        if max_concurrency < 1:
            raise ConfigurationError("Agent max_concurrency must be positive")
        if agent_id == self.orchestrator and not active:
            raise ConfigurationError(
                "Transfer orchestration before deactivating the current orchestrator"
            )
        with self._agent_lock():
            record = deepcopy(self.get_agent(agent_id))
            record["identity"] = {
                "controller_id": validate_identity_value(
                    controller_id,
                    field="controller_id",
                ),
                "provider": validate_identity_value(provider, field="provider"),
                "model_family": validate_identity_value(
                    model_family,
                    field="model_family",
                ),
            }
            record["capabilities"] = validate_capabilities(capabilities)
            record["max_concurrency"] = max_concurrency
            record["active"] = active
            record["updated_at"] = utc_now()
            return self._commit_agent(
                actor=actor,
                record=record,
                action="agent.updated",
                require_orchestrator=True,
            )

    def transfer_orchestrator(
        self,
        *,
        actor: str,
        target: str,
        reason: str,
    ) -> dict[str, Any]:
        """Transfer control through an explicit signed handoff event."""

        if not reason.strip():
            raise ConfigurationError("Orchestrator transfer reason cannot be empty")
        with self._orchestrator_lock():
            self._require_orchestrator(actor)
            if target == actor:
                raise ConfigurationError("Target is already the orchestrator")
            transfer_events = sum(
                event.get("action") == "workspace.orchestrator_transferred"
                for event in self.ledger.read()
            )
            governance_epoch = transfer_events + 1
            with self._agent_lock():
                target_agent = self.get_agent(target)
                if target_agent.get("active", True) is not True:
                    raise AuthorizationError(
                        "Cannot transfer control to an inactive agent"
                    )
                for agent_id in (actor, target):
                    record = deepcopy(self.get_agent(agent_id))
                    record["governance_epoch"] = governance_epoch
                    record["updated_at"] = utc_now()
                    self._commit_agent(
                        actor=actor,
                        record=record,
                        action="agent.updated",
                        require_orchestrator=True,
                    )
                event = self.ledger.append(
                    actor=actor,
                    action="workspace.orchestrator_transferred",
                    task_id=None,
                    payload={
                        "from": actor,
                        "to": target_agent["id"],
                        "reason": reason.strip(),
                    },
                    expected_orchestrator=actor,
                )
            return {
                "from": actor,
                "to": target_agent["id"],
                "reason": reason.strip(),
                "event_hash": event["event_hash"],
            }

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Return one task projection after matching it to the signed ledger."""

        path = self._task_path(task_id)
        if not path.is_file():
            raise ConfigurationError(f"Unknown task: {task_id}")
        task = read_json(path)
        validate_task(task)
        self.ledger.verify()
        expected = self.ledger.projected_tasks().get(task_id)
        comparable = {
            key: value for key, value in task.items() if key != "last_event_hash"
        }
        if expected is None:
            raise IntegrityError(f"Task {task_id} has no signed ledger snapshot")
        if comparable != expected:
            raise IntegrityError(
                f"Task {task_id} projection differs from the signed ledger"
            )
        return task

    def list_tasks(
        self,
        *,
        state: str | None = None,
        owner: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return task projections filtered by state or owner."""

        self.ledger.verify()
        expected_tasks = self.ledger.projected_tasks()
        result: list[dict[str, Any]] = []
        for path in sorted(self.tasks_dir.glob("*.json")):
            task = read_json(path)
            validate_task(task)
            comparable = {
                key: value for key, value in task.items() if key != "last_event_hash"
            }
            if expected_tasks.get(task["id"]) != comparable:
                raise IntegrityError(
                    f"Task {task['id']} projection differs from the signed ledger"
                )
            if state is not None and task["state"] != state:
                continue
            if owner is not None and task["owner"] != owner:
                continue
            result.append(task)
        return result

    def _commit_task(
        self,
        *,
        actor: str,
        action: str,
        task: dict[str, Any],
        details: dict[str, Any] | None = None,
        require_orchestrator: bool = False,
    ) -> dict[str, Any]:
        snapshot = {
            key: value for key, value in task.items() if key != "last_event_hash"
        }
        payload = {"task": snapshot}
        if details:
            payload["details"] = details
        event = self.ledger.append(
            actor=actor,
            action=action,
            task_id=task["id"],
            payload=payload,
            expected_orchestrator=actor if require_orchestrator else None,
        )
        projected = deepcopy(snapshot)
        projected["last_event_hash"] = event["event_hash"]
        atomic_write_json(self._task_path(task["id"]), projected)
        return projected

    @staticmethod
    def _profiles_mutually_diverse(
        *,
        profiles: list[dict[str, Any]],
        dimensions: list[str],
    ) -> bool:
        for dimension in dimensions:
            key = (
                "id"
                if dimension == "actor"
                else "controller_id"
                if dimension == "controller"
                else dimension
            )
            values = [profile.get(key) for profile in profiles]
            if any(
                value in {None, "", "unknown", "unspecified"}
                for value in values
            ):
                return False
            if len(values) != len(set(values)):
                return False
        return True

    @staticmethod
    def _task_creation_contract(task: dict[str, Any]) -> dict[str, Any]:
        permissions = {
            "gpu": False,
            "performance_metrics": False,
            "network": False,
            "outcome_data": False,
            **task.get("permissions", {}),
        }
        gates = {
            "require_validation": True,
            "allow_skips": False,
            "require_known_answer_check": True,
            "require_independent_verification": True,
            **task.get("gates", {}),
        }
        verification_policy = {
            "required_attestations": 0,
            "allowed_verifiers": [],
            "independence_dimensions": ["actor"],
            **task.get("verification_policy", {}),
        }
        delivery_policy = {
            "allow_proxy": False,
            "git_remote_name": None,
            "git_remote_url": None,
            "git_ref": None,
            "required_repo_paths": [],
            **task.get("delivery_policy", {}),
        }
        return {
            "id": task["id"],
            "title": task["title"],
            "description": task.get("description", ""),
            "owner": task["owner"],
            "prerequisites": task.get("prerequisites", []),
            "allowed_write_roots": task.get("allowed_write_roots", []),
            "task_type": task.get("task_type", "general"),
            "risk_tier": task.get("risk_tier", "medium"),
            "required_capabilities": task.get("required_capabilities", []),
            "resource_locks": task.get("resource_locks", []),
            "permissions": permissions,
            "gates": gates,
            "verification_policy": verification_policy,
            "delivery_policy": delivery_policy,
        }

    def create_task(
        self,
        *,
        actor: str,
        task_id: str,
        title: str,
        description: str,
        owner: str,
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
        """Create a task with immutable preregistered permissions and gates."""

        self._require_orchestrator(actor)
        worker = self.get_agent(owner)
        if worker.get("active", True) is not True:
            raise ConfigurationError(f"Task owner {owner!r} is inactive")
        if worker["role"] not in {"worker", "verifier", "orchestrator"}:
            raise ConfigurationError(f"Task owner {owner!r} cannot own tasks")
        defaults = self.config["defaults"]
        normalized_risk_tier = risk_tier.strip().lower()
        normalized_task_type = task_type.strip().lower()
        merged_permissions = {
            **defaults["permissions"],
            **(permissions or {}),
        }
        merged_gates = {**defaults["gates"], **(gates or {})}
        normalized_capabilities = validate_capabilities(required_capabilities)
        worker_capabilities = set(worker.get("capabilities", []))
        missing_capabilities = sorted(
            set(normalized_capabilities) - worker_capabilities
        )
        if missing_capabilities:
            raise ConfigurationError(
                f"Task owner {owner!r} lacks required capabilities: "
                + ", ".join(missing_capabilities)
            )
        if not all(
            isinstance(lock, str) and lock.strip()
            for lock in (resource_locks or [])
        ):
            raise ConfigurationError("Resource locks must be non-empty strings")
        locks = sorted({lock.strip().lower() for lock in (resource_locks or [])})
        if merged_permissions.get("gpu") and not any(
            lock.startswith("gpu:") for lock in locks
        ):
            raise ConfigurationError(
                "GPU-enabled tasks must preregister at least one gpu:<index> resource lock"
            )
        policy = deepcopy(verification_policy or {})
        required_value = policy.get("required_attestations", 0)
        if (
            not isinstance(required_value, int)
            or isinstance(required_value, bool)
            or required_value < 0
        ):
            raise ConfigurationError(
                "required_attestations must be a non-negative integer"
            )
        required_attestations = required_value
        allowed_value = policy.get("allowed_verifiers", [])
        if not isinstance(allowed_value, list):
            raise ConfigurationError("allowed_verifiers must be a list")
        allowed_verifiers = list(
            dict.fromkeys(validate_agent_id(str(item)) for item in allowed_value)
        )
        dimensions = validate_independence_dimensions(
            policy.get("independence_dimensions", ["actor"])
        )
        policy["required_attestations"] = required_attestations
        policy["allowed_verifiers"] = allowed_verifiers
        policy["independence_dimensions"] = dimensions
        if required_attestations and not merged_gates.get(
            "require_independent_verification", True
        ):
            raise ConfigurationError(
                "A task cannot require verifier attestations while independent "
                "verification is disabled"
            )
        if required_attestations and not allowed_verifiers:
            raise ConfigurationError(
                "Tasks with verifier attestations must name allowed verifiers"
            )
        if (
            allowed_verifiers
            and required_attestations + 1 > len(allowed_verifiers)
        ):
            raise ConfigurationError(
                "Verification requires at least required_attestations + 1 "
                "allowed verifiers because the finalizer must be distinct"
            )
        verifier_profiles: list[dict[str, Any]] = []
        for verifier_id in allowed_verifiers:
            verifier = self.get_agent(verifier_id)
            if verifier.get("active", True) is not True:
                raise ConfigurationError(
                    f"Allowed verifier {verifier_id!r} is inactive"
                )
            verifier_capabilities = set(verifier.get("capabilities", []))
            if (
                verifier_id != self.orchestrator
                and verifier.get("role") != "verifier"
                and "verify" not in verifier_capabilities
            ):
                raise ConfigurationError(
                    f"Allowed verifier {verifier_id!r} lacks verifier authority"
                )
            verifier_profiles.append(profile_snapshot(verifier))

        if normalized_risk_tier in {"high", "critical"}:
            if (
                not merged_gates.get("require_independent_verification", True)
                or not merged_gates.get("require_validation", True)
                or not merged_gates.get("require_known_answer_check", True)
                or merged_gates.get("allow_skips", False)
            ):
                raise ConfigurationError(
                    f"{normalized_risk_tier} risk tasks require validation, known-answer, "
                    "zero-skip, and independent-verification gates"
                )
            strict_dimensions = {"actor", "controller", "model_family"}
            if not strict_dimensions.issubset(dimensions):
                raise ConfigurationError(
                    f"{normalized_risk_tier} risk tasks require actor, controller, and "
                    "model_family independence"
                )
            if not allowed_verifiers:
                raise ConfigurationError(
                    f"{normalized_risk_tier} risk tasks must name allowed verifiers"
                )

        if merged_gates.get("require_independent_verification", True):
            author_profile = profile_snapshot(worker)
            independent_profiles = [
                profile
                for profile in verifier_profiles
                if evaluate_independence(
                    author=author_profile,
                    verifier=profile,
                    dimensions=dimensions,
                )["independent"]
            ]
            if allowed_verifiers and not independent_profiles:
                raise ConfigurationError(
                    "No allowed verifier is independent from the task owner "
                    "under the declared dimensions"
                )
            if required_attestations:
                quorum_size = required_attestations + 1
                if not any(
                    self._profiles_mutually_diverse(
                        profiles=list(candidate),
                        dimensions=dimensions,
                    )
                    for candidate in combinations(
                        independent_profiles,
                        quorum_size,
                    )
                ):
                    raise ConfigurationError(
                        "Allowed verifiers cannot form the preregistered "
                        "attestation-plus-finalizer independence quorum"
                    )
        task = new_task(
            task_id=task_id,
            title=title,
            description=description,
            owner=owner,
            created_by=actor,
            prerequisites=prerequisites,
            allowed_write_roots=allowed_write_roots,
            permissions=merged_permissions,
            gates=merged_gates,
            task_type=normalized_task_type,
            risk_tier=normalized_risk_tier,
            required_capabilities=normalized_capabilities,
            resource_locks=locks,
            verification_policy=policy,
            delivery_policy=delivery_policy,
            idempotency_key=idempotency_key,
        )
        path = self._task_path(task_id)
        with self._creation_lock():
            for existing in self.list_tasks():
                if existing.get("idempotency_key") == task["idempotency_key"]:
                    requested_contract = self._task_creation_contract(task)
                    existing_contract = self._task_creation_contract(existing)
                    if requested_contract != existing_contract:
                        mismatches = sorted(
                            key
                            for key in requested_contract
                            if requested_contract[key] != existing_contract.get(key)
                        )
                        raise ConfigurationError(
                            "Idempotency key is already bound to a different "
                            "immutable task contract: " + ", ".join(mismatches)
                        )
                    return existing
            if path.exists():
                existing = self.get_task(task_id)
                raise ConfigurationError(f"Task already exists: {task_id}")
            for prerequisite in task["prerequisites"]:
                self.get_task(prerequisite)
            return self._commit_task(
                actor=actor,
                action="task.created",
                task=task,
                require_orchestrator=True,
            )

    def _prerequisites_ready(self, task: dict[str, Any]) -> bool:
        for task_id in task["prerequisites"]:
            if self.get_task(task_id)["state"] not in {"verified", "archived"}:
                return False
        return True

    def _active_tasks(self) -> list[dict[str, Any]]:
        return [
            task
            for task in self.list_tasks()
            if task["state"] in {"claimed", "running", "revoking"}
        ]

    def _resource_holders(self) -> list[dict[str, Any]]:
        return [
            task
            for task in self.list_tasks()
            if task["state"] in {"claimed", "running", "revoking", "submitted"}
        ]

    def _assert_resource_availability(self, task: dict[str, Any]) -> None:
        requested = {
            str(lock).strip().lower()
            for lock in task.get("resource_locks", [])
        }
        for other in self._resource_holders():
            if other["id"] == task["id"]:
                continue
            other_locks = {
                str(lock).strip().lower()
                for lock in other.get("resource_locks", [])
            }
            conflict = sorted(requested & other_locks)
            if conflict:
                raise TransitionError(
                    f"Task {task['id']} conflicts with active task {other['id']} "
                    "on resources: " + ", ".join(conflict)
                )

    def _assert_claim_policy(
        self,
        *,
        agent: dict[str, Any],
        task: dict[str, Any],
    ) -> None:
        capabilities = set(agent.get("capabilities", []))
        missing = sorted(
            set(task.get("required_capabilities", [])) - capabilities
        )
        if missing:
            raise AuthorizationError(
                f"Agent {agent['id']} lacks required capabilities: "
                + ", ".join(missing)
            )

        active = self._active_tasks()
        actor_active = [item for item in active if item["owner"] == agent["id"]]
        max_concurrency = int(agent.get("max_concurrency", 1))
        if len(actor_active) >= max_concurrency:
            raise TransitionError(
                f"Agent {agent['id']} reached max_concurrency={max_concurrency}"
            )

        self._assert_resource_availability(task)

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def claim(
        self,
        *,
        actor: str,
        task_id: str | None = None,
        lease_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Atomically claim one ready task and return its one-time lease token."""

        self.get_agent(actor)
        candidates = (
            [self.get_task(task_id)]
            if task_id is not None
            else self.list_tasks(state="pending", owner=actor)
        )
        for candidate in candidates:
            if candidate["owner"] != actor:
                if task_id is not None:
                    raise AuthorizationError(
                        f"Task {candidate['id']} is owned by {candidate['owner']}"
                    )
                continue
            with self._resource_lock():
                with self._task_lock(candidate["id"]):
                    with self._agent_lock():
                        agent = self.get_agent(actor)
                        if agent.get("active", True) is not True:
                            raise AuthorizationError(f"Agent {actor!r} is inactive")
                        if agent["role"] not in {
                            "worker",
                            "verifier",
                            "orchestrator",
                        }:
                            raise AuthorizationError(
                                "Only worker, verifier, or orchestrator agents "
                                "may claim tasks"
                            )
                        task = self.get_task(candidate["id"])
                        if task["state"] != "pending":
                            if task_id is not None:
                                raise TransitionError(
                                    f"Task {task['id']} is {task['state']}, not pending"
                                )
                            continue
                        if not self._prerequisites_ready(task):
                            if task_id is not None:
                                raise TransitionError(
                                    f"Task {task['id']} has unverified prerequisites"
                                )
                            continue
                        self._assert_claim_policy(agent=agent, task=task)
                        token = secrets.token_urlsafe(24)
                        duration = lease_seconds or int(
                            self.config["defaults"]["lease_seconds"]
                        )
                        now = utc_now()
                        claimed = transition(
                            task,
                            "claimed",
                            attempt=task["attempt"] + 1,
                            lease={
                                "owner": actor,
                                "token_hash": self._token_hash(token),
                                "claimed_at": now,
                                "heartbeat_at": now,
                                "expires_at": lease_expiry(duration, now),
                                "duration_seconds": duration,
                            },
                            blocked_reason=None,
                        )
                        projection = self._commit_task(
                            actor=actor,
                            action="task.claimed",
                            task=claimed,
                        )
                        return {"task": projection, "lease_token": token}
        raise TransitionError(f"No ready pending tasks are available for {actor}")

    def _require_lease(
        self,
        task: dict[str, Any],
        *,
        actor: str,
        lease_token: str,
        allow_expired: bool = False,
    ) -> None:
        lease = task.get("lease")
        if not lease:
            raise LeaseError(f"Task {task['id']} has no active lease")
        if lease.get("owner") != actor:
            raise LeaseError(f"Task {task['id']} lease belongs to another worker")
        if not secrets.compare_digest(
            str(lease.get("token_hash", "")), self._token_hash(lease_token)
        ):
            raise LeaseError(f"Task {task['id']} lease token is invalid")
        if not allow_expired and lease_expired(task):
            raise LeaseError(f"Task {task['id']} lease has expired")

    def _require_active_task_owner(
        self,
        *,
        task: dict[str, Any],
        actor: str,
    ) -> dict[str, Any]:
        agent = self.get_agent(actor)
        if agent.get("active", True) is not True:
            raise AuthorizationError(f"Agent {actor!r} is inactive")
        missing = sorted(
            set(task.get("required_capabilities", []))
            - set(agent.get("capabilities", []))
        )
        if missing:
            raise AuthorizationError(
                f"Agent {actor!r} no longer has required capabilities: "
                + ", ".join(missing)
            )
        return agent

    def start(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
    ) -> dict[str, Any]:
        """Move a claimed task into running state."""

        with self._task_lock(task_id), self._agent_lock():
            task = self.get_task(task_id)
            self._require_lease(task, actor=actor, lease_token=lease_token)
            self._require_active_task_owner(task=task, actor=actor)
            started = transition(task, "running")
            return self._commit_task(
                actor=actor,
                action="task.started",
                task=started,
            )

    def register_execution(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
        execution_token: str,
        pid: int,
        isolation: str,
    ) -> dict[str, Any]:
        """Bind a command-adapter execution secret and process-tree identity."""

        if not execution_token:
            raise ConfigurationError("Execution token cannot be empty")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1:
            raise ConfigurationError("Execution PID must be a positive integer")
        if isolation not in {"process-group", "windows-job", "linux-subreaper"}:
            raise ConfigurationError(
                "Execution isolation must be process-group, windows-job, "
                "or linux-subreaper"
            )
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "running":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not running"
                )
            self._require_lease(
                task,
                actor=actor,
                lease_token=lease_token,
            )
            agent = self.get_agent(actor)
            if agent.get("mode") != "command":
                raise AuthorizationError(
                    "Only a configured command adapter may register execution"
                )
            if task.get("execution") is not None:
                raise ConfigurationError(
                    f"Task {task_id} already has a registered execution"
                )
            registered = deepcopy(task)
            registered["execution"] = {
                "token_hash": self._token_hash(execution_token),
                "pid": pid,
                "isolation": isolation,
                "registered_at": utc_now(),
                "status": "running",
                "ended_at": None,
                "termination_evidence": None,
            }
            registered["revision"] += 1
            registered["updated_at"] = utc_now()
            validate_task(registered)
            return self._commit_task(
                actor=actor,
                action="task.execution_registered",
                task=registered,
                details={"pid": pid, "isolation": isolation},
            )

    def record_execution_exit(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
        execution_token: str,
        exit_code: int,
        termination_evidence: str,
    ) -> dict[str, Any]:
        """Record a broker-observed command exit without changing task state."""

        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise ConfigurationError("Execution exit code must be an integer")
        if not termination_evidence.strip():
            raise ConfigurationError("Execution exit evidence cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "running":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not running"
                )
            self._require_lease(
                task,
                actor=actor,
                lease_token=lease_token,
                allow_expired=True,
            )
            execution = task.get("execution")
            if (
                not isinstance(execution, dict)
                or not secrets.compare_digest(
                    str(execution.get("token_hash", "")),
                    self._token_hash(execution_token),
                )
            ):
                raise AuthorizationError(
                    "Execution exit requires the adapter-held execution token"
                )
            exited = deepcopy(task)
            exited["execution"] = {
                **execution,
                "status": "exited",
                "exit_code": exit_code,
                "ended_at": utc_now(),
                "termination_evidence": termination_evidence.strip(),
            }
            exited["revision"] += 1
            exited["updated_at"] = utc_now()
            validate_task(exited)
            return self._commit_task(
                actor=actor,
                action="task.execution_exited",
                task=exited,
                details={
                    "exit_code": exit_code,
                    "termination_evidence": termination_evidence.strip(),
                },
            )

    def heartbeat(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
    ) -> dict[str, Any]:
        """Extend a claimed or running task lease."""

        with self._task_lock(task_id), self._agent_lock():
            task = self.get_task(task_id)
            if task["state"] not in {"claimed", "running"}:
                raise TransitionError(
                    f"Cannot heartbeat task {task_id} in state {task['state']}"
                )
            self._require_lease(task, actor=actor, lease_token=lease_token)
            self._require_active_task_owner(task=task, actor=actor)
            renewed = deepcopy(task)
            now = utc_now()
            renewed["lease"]["heartbeat_at"] = now
            renewed["lease"]["expires_at"] = lease_expiry(
                int(renewed["lease"]["duration_seconds"]), now
            )
            renewed["revision"] += 1
            renewed["updated_at"] = now
            return self._commit_task(
                actor=actor,
                action="task.heartbeat",
                task=renewed,
            )

    def block(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
        reason: str,
    ) -> dict[str, Any]:
        """Record a blocker, retaining locks if execution may still be live."""

        if not reason.strip():
            raise ConfigurationError("Blocked reason cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"claimed", "running"}:
                raise TransitionError(
                    f"Cannot block task {task_id} in state {task['state']}"
                )
            self._require_lease(task, actor=actor, lease_token=lease_token)
            if task["state"] == "running":
                revoking = transition(
                    task,
                    "revoking",
                    blocked_reason=(
                        "Termination unconfirmed after worker block: "
                        + reason.strip()
                    ),
                    revocation={
                        "requested_by": actor,
                        "requested_at": utc_now(),
                        "reason": reason.strip(),
                        "acknowledged_by": None,
                        "acknowledged_at": None,
                        "termination_evidence": None,
                    },
                )
                return self._commit_task(
                    actor=actor,
                    action="task.termination_unconfirmed",
                    task=revoking,
                    details={"reason": reason.strip()},
                )
            blocked = transition(
                task,
                "blocked",
                lease=None,
                blocked_reason=reason.strip(),
            )
            return self._commit_task(
                actor=actor,
                action="task.blocked",
                task=blocked,
                details={"reason": reason.strip()},
            )

    def revoke_lease(
        self,
        *,
        actor: str,
        task_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Request termination while retaining locks until it is confirmed."""

        self._require_orchestrator(actor)
        if not reason.strip():
            raise ConfigurationError("Lease revocation reason cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"claimed", "running"}:
                raise TransitionError(
                    f"Cannot revoke lease for task {task_id} in state {task['state']}"
                )
            revoking = transition(
                task,
                "revoking",
                blocked_reason=f"Revocation requested: {reason.strip()}",
                revocation={
                    "requested_by": actor,
                    "requested_at": utc_now(),
                    "reason": reason.strip(),
                    "acknowledged_by": None,
                    "acknowledged_at": None,
                    "termination_evidence": None,
                },
            )
            return self._commit_task(
                actor=actor,
                action="task.revocation_requested",
                task=revoking,
                details={"reason": reason.strip()},
                require_orchestrator=True,
            )

    def hold_for_termination(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
        reason: str,
    ) -> dict[str, Any]:
        """Keep resources locked when an adapter cannot prove process exit."""

        if not reason.strip():
            raise ConfigurationError("Termination hold reason cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"claimed", "running"}:
                raise TransitionError(
                    f"Cannot hold task {task_id} in state {task['state']}"
                )
            self._require_lease(
                task,
                actor=actor,
                lease_token=lease_token,
                allow_expired=True,
            )
            revoking = transition(
                task,
                "revoking",
                blocked_reason=f"Termination unconfirmed: {reason.strip()}",
                revocation={
                    "requested_by": actor,
                    "requested_at": utc_now(),
                    "reason": reason.strip(),
                    "acknowledged_by": None,
                    "acknowledged_at": None,
                    "termination_evidence": None,
                },
            )
            return self._commit_task(
                actor=actor,
                action="task.termination_unconfirmed",
                task=revoking,
                details={"reason": reason.strip()},
            )

    def acknowledge_revocation(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
        termination_evidence: str,
        execution_token: str | None = None,
    ) -> dict[str, Any]:
        """Release a command task after its owning adapter confirms termination."""

        if not termination_evidence.strip():
            raise ConfigurationError("Termination evidence cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "revoking":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not revoking"
                )
            self._require_lease(
                task,
                actor=actor,
                lease_token=lease_token,
                allow_expired=True,
            )
            agent = self.get_agent(actor)
            if agent.get("mode") != "command":
                raise AuthorizationError(
                    "Manual agents cannot self-confirm process termination; "
                    "the orchestrator must confirm it externally"
                )
            execution = task.get("execution")
            if (
                not isinstance(execution, dict)
                or not execution_token
                or not secrets.compare_digest(
                    str(execution.get("token_hash", "")),
                    self._token_hash(execution_token),
                )
            ):
                raise AuthorizationError(
                    "Revocation acknowledgement requires the adapter-held "
                    "execution token"
                )
            revocation = deepcopy(task.get("revocation") or {})
            revocation.update(
                {
                    "acknowledged_by": actor,
                    "acknowledged_at": utc_now(),
                    "termination_evidence": termination_evidence.strip(),
                }
            )
            blocked = transition(
                task,
                "blocked",
                lease=None,
                revocation=revocation,
                execution={
                    **execution,
                    "status": "terminated",
                    "ended_at": utc_now(),
                    "termination_evidence": termination_evidence.strip(),
                },
                blocked_reason=(
                    "Revocation acknowledged after termination: "
                    + termination_evidence.strip()
                ),
            )
            return self._commit_task(
                actor=actor,
                action="task.revocation_acknowledged",
                task=blocked,
                details={"termination_evidence": termination_evidence.strip()},
            )

    def confirm_revocation(
        self,
        *,
        actor: str,
        task_id: str,
        termination_evidence: str,
    ) -> dict[str, Any]:
        """Release a revoked task after external termination was verified."""

        self._require_orchestrator(actor)
        if not termination_evidence.strip():
            raise ConfigurationError("Termination evidence cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "revoking":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not revoking"
                )
            revocation = deepcopy(task.get("revocation") or {})
            revocation.update(
                {
                    "acknowledged_by": actor,
                    "acknowledged_at": utc_now(),
                    "termination_evidence": termination_evidence.strip(),
                }
            )
            execution = task.get("execution")
            execution_update = (
                {
                    **execution,
                    "status": "externally-confirmed",
                    "ended_at": utc_now(),
                    "termination_evidence": termination_evidence.strip(),
                }
                if isinstance(execution, dict)
                else execution
            )
            blocked = transition(
                task,
                "blocked",
                lease=None,
                revocation=revocation,
                execution=execution_update,
                blocked_reason=(
                    "Revocation confirmed after external termination: "
                    + termination_evidence.strip()
                ),
            )
            return self._commit_task(
                actor=actor,
                action="task.revocation_confirmed",
                task=blocked,
                details={"termination_evidence": termination_evidence.strip()},
                require_orchestrator=True,
            )

    def submit(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
        report_path: str | Path,
        manifest_path: str | Path,
    ) -> dict[str, Any]:
        """Submit a passing evidence bundle for independent verification."""

        report = Path(report_path).resolve()
        manifest = Path(manifest_path).resolve()
        owned_report_root = self.reports_dir / actor
        if not is_relative_to(report, owned_report_root):
            raise AuthorizationError(
                f"Report must be under the actor's report directory: {owned_report_root}"
            )
        if not is_relative_to(manifest, owned_report_root):
            raise AuthorizationError(
                f"Manifest must be under the actor's report directory: {owned_report_root}"
            )
        task_for_validation = self.get_task(task_id)
        evidence = validate_submission(
            report,
            manifest,
            permissions=task_for_validation["permissions"],
            gates=task_for_validation["gates"],
        )
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "running":
                raise TransitionError(
                    f"Task {task_id} must be running before submission"
                )
            self._require_lease(task, actor=actor, lease_token=lease_token)
            with self._agent_lock():
                author_agent = self._require_active_task_owner(
                    task=task,
                    actor=actor,
                )
                evidence["archive"] = archive_evidence_bundle(
                    submissions_root=self.submissions_dir,
                    task_id=task_id,
                    attempt=task["attempt"],
                    label="worker",
                    report=evidence["report"],
                    manifest=evidence["manifest"],
                    max_artifact_bytes=int(
                        self.config["defaults"].get(
                            "max_evidence_bytes", 50 * 1024 * 1024
                        )
                    ),
                )
                evidence["submission"] = {
                    "mode": "direct",
                    "author": actor,
                    "submitted_by": actor,
                    "author_profile": profile_snapshot(author_agent),
                }
                submitted = transition(
                    task,
                    "submitted",
                    lease=None,
                    result=evidence,
                    verification=None,
                    verification_attestations=[],
                )
                return self._commit_task(
                    actor=actor,
                    action="task.submitted",
                    task=submitted,
                    details={
                        "report_sha256": evidence["report"]["sha256"],
                        "manifest_sha256": evidence["manifest"]["sha256"],
                    },
                )

    @staticmethod
    def _submission_author(task: dict[str, Any]) -> str:
        submission = task.get("result", {}).get("submission", {})
        author = submission.get("author") if isinstance(submission, dict) else None
        return str(author or task["owner"])

    def _submission_author_profile(self, task: dict[str, Any]) -> dict[str, Any]:
        """Return the author identity frozen when the evidence was submitted."""

        submission = task.get("result", {}).get("submission", {})
        profile = (
            submission.get("author_profile")
            if isinstance(submission, dict)
            else None
        )
        if isinstance(profile, dict):
            return deepcopy(profile)
        # Legacy submissions can still use actor-only independence. Stronger
        # dimensions fail closed because their original identity was not frozen.
        return {
            "id": self._submission_author(task),
            "role": None,
            "controller_id": None,
            "provider": None,
            "model_family": None,
            "capabilities": [],
            "active": None,
        }

    def proxy_submit(
        self,
        *,
        actor: str,
        task_id: str,
        author: str,
        report_path: str | Path,
        manifest_path: str | Path,
        source_repo: str | Path,
        source_commit: str,
        source_files: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Submit byte-verified Git delivery on behalf of an unreachable owner."""

        self._require_orchestrator(actor)
        task_for_validation = self.get_task(task_id)
        if author != task_for_validation["owner"]:
            raise AuthorizationError(
                "Proxy submission author must be the task's registered owner"
            )
        if actor == author:
            raise AuthorizationError(
                "Proxy submitter must be a different identity from the author"
            )
        delivery_policy = task_for_validation.get("delivery_policy", {})
        if delivery_policy.get("allow_proxy") is not True:
            raise AuthorizationError(
                "Proxy delivery was not preregistered for this task"
            )
        report = Path(report_path).resolve()
        manifest = Path(manifest_path).resolve()
        proxy_root = self.reports_dir / actor
        if not is_relative_to(report, proxy_root):
            raise AuthorizationError(
                f"Proxy report must be under the actor's report directory: {proxy_root}"
            )
        if not is_relative_to(manifest, proxy_root):
            raise AuthorizationError(
                f"Proxy manifest must be under the actor's report directory: {proxy_root}"
            )

        evidence = validate_submission(
            report,
            manifest,
            permissions=task_for_validation["permissions"],
            gates=task_for_validation["gates"],
        )
        source = verify_git_delivery(
            repo_path=source_repo,
            remote_name=delivery_policy["git_remote_name"],
            expected_remote_url=delivery_policy["git_remote_url"],
            source_ref=delivery_policy["git_ref"],
            source_commit=source_commit,
            files=source_files,
        )
        required_repo_paths = set(delivery_policy["required_repo_paths"])
        observed_repo_paths = [item["repo_path"] for item in source["files"]]
        if (
            len(observed_repo_paths) != len(set(observed_repo_paths))
            or set(observed_repo_paths) != required_repo_paths
        ):
            raise EvidenceError(
                "Proxy delivery must bind exactly the preregistered repository "
                "paths"
            )
        manifest_artifacts = {
            (item["path"], item["sha256"])
            for item in evidence["manifest"].get("artifacts", [])
        }
        unbound = [
            item
            for item in source["files"]
            if (item["local_path"], item["sha256"]) not in manifest_artifacts
        ]
        if unbound:
            raise EvidenceError(
                "Every proxy-delivered Git artifact must also be bound in the "
                "evidence manifest"
            )

        with self._resource_lock():
            with self._task_lock(task_id):
                task = self.get_task(task_id)
                if task["state"] != "pending":
                    raise TransitionError(
                        "Proxy submission requires pending state, found "
                        f"{task['state']}"
                    )
                if not self._prerequisites_ready(task):
                    raise TransitionError(
                        f"Task {task_id} has unverified prerequisites"
                    )
                self._assert_resource_availability(task)
                attempt = task["attempt"] + 1
                with self._agent_lock():
                    self._require_orchestrator(actor)
                    author_agent = self.get_agent(author)
                    if author_agent.get("active", True) is not True:
                        raise AuthorizationError(
                            f"Proxy author {author!r} is inactive"
                        )
                    self._assert_claim_policy(
                        agent=author_agent,
                        task=task,
                    )
                    evidence["archive"] = archive_evidence_bundle(
                        submissions_root=self.submissions_dir,
                        task_id=task_id,
                        attempt=attempt,
                        label="proxy",
                        report=evidence["report"],
                        manifest=evidence["manifest"],
                        max_artifact_bytes=int(
                            self.config["defaults"].get(
                                "max_evidence_bytes", 50 * 1024 * 1024
                            )
                        ),
                    )
                    evidence["submission"] = {
                        "mode": "proxy",
                        "author": author,
                        "submitted_by": actor,
                        "author_profile": profile_snapshot(author_agent),
                        "proxy_profile": profile_snapshot(self.get_agent(actor)),
                        "source": source,
                    }
                    submitted = transition(
                        task,
                        "submitted",
                        attempt=attempt,
                        lease=None,
                        result=evidence,
                        verification=None,
                        verification_attestations=[],
                    )
                    return self._commit_task(
                        actor=actor,
                        action="task.proxy_submitted",
                        task=submitted,
                        details={
                            "author": author,
                            "proxy": actor,
                            "source_commit": source["source_commit"],
                            "report_sha256": evidence["report"]["sha256"],
                            "manifest_sha256": evidence["manifest"]["sha256"],
                        },
                        require_orchestrator=True,
                    )

    def _require_verifier(self, actor: str) -> dict[str, Any]:
        agent = self.get_agent(actor)
        if agent.get("active", True) is not True:
            raise AuthorizationError(f"Agent {actor!r} is inactive")
        capabilities = set(agent.get("capabilities", []))
        if (
            actor != self.orchestrator
            and agent.get("role") != "verifier"
            and "verify" not in capabilities
        ):
            raise AuthorizationError(
                "Only the orchestrator or an agent with verifier authority "
                "may perform this action"
            )
        return agent

    @staticmethod
    def _verification_policy(task: dict[str, Any]) -> dict[str, Any]:
        return task.get(
            "verification_policy",
            {
                "required_attestations": 0,
                "allowed_verifiers": [],
                "independence_dimensions": ["actor"],
            },
        )

    def _assert_verifier_allowed(
        self,
        *,
        task: dict[str, Any],
        actor: str,
    ) -> None:
        policy = self._verification_policy(task)
        allowed = policy.get("allowed_verifiers", [])
        if allowed and actor not in allowed:
            raise AuthorizationError(
                f"Agent {actor!r} is not an allowed verifier for task {task['id']}"
            )

    def _independence_for(
        self,
        *,
        task: dict[str, Any],
        verifier: dict[str, Any],
    ) -> dict[str, Any]:
        dimensions = self._verification_policy(task).get(
            "independence_dimensions", ["actor"]
        )
        return evaluate_independence(
            author=self._submission_author_profile(task),
            verifier=profile_snapshot(verifier),
            dimensions=dimensions,
        )

    def _validate_verifier_manifest(
        self,
        *,
        actor: str,
        task: dict[str, Any],
        manifest_path: str | Path,
        label: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        verification_path = Path(manifest_path).resolve()
        verifier_root = self.reports_dir / actor
        if not is_relative_to(verification_path, verifier_root):
            role_label = (
                "orchestrator's"
                if actor == self.orchestrator
                else "verifier's"
            )
            raise AuthorizationError(
                f"Verification manifest must be under the {role_label} "
                f"report directory: {verifier_root}"
            )
        evidence = validate_manifest(
            verification_path,
            permissions=task["permissions"],
            gates=task["gates"],
        )
        worker_manifest_sha = (
            task.get("result", {}).get("manifest", {}).get("sha256")
        )
        if worker_manifest_sha and evidence["sha256"] == worker_manifest_sha:
            raise EvidenceError(
                "Independent verification cannot reuse the worker manifest"
            )
        archive = archive_evidence_bundle(
            submissions_root=self.submissions_dir,
            task_id=task["id"],
            attempt=task["attempt"],
            label=label,
            report=None,
            manifest=evidence,
            max_artifact_bytes=int(
                self.config["defaults"].get(
                    "max_evidence_bytes", 50 * 1024 * 1024
                )
            ),
        )
        return evidence, archive

    @staticmethod
    def _diverse_attestation_quorum(
        *,
        attestations: list[dict[str, Any]],
        required: int,
        dimensions: list[str],
        finalizer: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        if required == 0:
            return []
        for candidate in combinations(attestations, required):
            profiles = [
                item.get("verifier", {})
                for item in candidate
            ]
            profiles.append(finalizer)
            if Workspace._profiles_mutually_diverse(
                profiles=profiles,
                dimensions=dimensions,
            ):
                return list(candidate)
        return None

    def attest(
        self,
        *,
        actor: str,
        task_id: str,
        decision: str,
        note: str,
        verification_manifest: str | Path | None = None,
    ) -> dict[str, Any]:
        """Record an independent verifier attestation without finalizing a task."""

        if decision not in {"accept", "reject"}:
            raise ConfigurationError("Attestation decision must be accept or reject")
        if not note.strip():
            raise ConfigurationError("Attestation note cannot be empty")
        with self._task_lock(task_id), self._agent_lock():
            verifier = self._require_verifier(actor)
            task = self.get_task(task_id)
            if task["state"] != "submitted":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not submitted"
                )
            self._assert_verifier_allowed(task=task, actor=actor)
            independence = self._independence_for(
                task=task,
                verifier=verifier,
            )
            if not independence["independent"]:
                raise AuthorizationError(
                    "Verifier is not independent from the work author: "
                    + "; ".join(independence["reasons"])
                )
            attestations = list(task.get("verification_attestations", []))
            if any(item.get("actor") == actor for item in attestations):
                raise ConfigurationError(
                    f"Agent {actor!r} already attested task {task_id}"
                )
            attestation: dict[str, Any] = {
                "actor": actor,
                "decision": decision,
                "note": note.strip(),
                "attested_at": utc_now(),
                "author": self._submission_author_profile(task),
                "verifier": profile_snapshot(verifier),
                "independence": independence,
            }
            if decision == "accept":
                if verification_manifest is None:
                    raise EvidenceError(
                        "Accepting attestation requires a verification manifest"
                    )
                evidence, archive = self._validate_verifier_manifest(
                    actor=actor,
                    task=task,
                    manifest_path=verification_manifest,
                    label=f"attestation-{actor}",
                )
                attestation["evidence"] = evidence
                attestation["archive"] = archive
            attestations.append(attestation)
            updated = deepcopy(task)
            updated["verification_attestations"] = attestations
            updated["revision"] += 1
            updated["updated_at"] = utc_now()
            validate_task(updated)
            return self._commit_task(
                actor=actor,
                action="task.attested",
                task=updated,
                details={
                    "decision": decision,
                    "independence": independence,
                },
            )

    def verify(
        self,
        *,
        actor: str,
        task_id: str,
        decision: str,
        note: str,
        verification_manifest: str | Path | None = None,
    ) -> dict[str, Any]:
        """Accept or reject a task through an identity-aware verifier."""

        if decision not in {"accept", "reject"}:
            raise ConfigurationError("Verification decision must be accept or reject")
        if not note.strip():
            raise ConfigurationError("Verification note cannot be empty")
        with self._task_lock(task_id), self._agent_lock():
            verifier = self._require_verifier(actor)
            task = self.get_task(task_id)
            if task["state"] != "submitted":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not submitted"
                )
            self._assert_verifier_allowed(task=task, actor=actor)
            verification: dict[str, Any] = {
                "actor": actor,
                "decision": decision,
                "note": note.strip(),
                "verified_at": utc_now(),
                "author": self._submission_author_profile(task),
                "verifier": profile_snapshot(verifier),
            }
            if decision == "accept":
                if task["gates"].get("require_independent_verification", True):
                    independence = self._independence_for(
                        task=task,
                        verifier=verifier,
                    )
                    if not independence["independent"]:
                        raise AuthorizationError(
                            "Final verifier is not independent from the work author: "
                            + "; ".join(independence["reasons"])
                        )
                    verification["independence"] = independence
                    policy = self._verification_policy(task)
                    required = int(policy.get("required_attestations", 0))
                    attestations = task.get("verification_attestations", [])
                    rejected = [
                        item
                        for item in attestations
                        if item.get("decision") == "reject"
                    ]
                    accepted = [
                        item
                        for item in attestations
                        if item.get("decision") == "accept"
                        and item.get("independence", {}).get("independent") is True
                    ]
                    if rejected:
                        raise EvidenceError(
                            "Task has a rejecting verifier attestation and cannot "
                            "be accepted without requeueing a new attempt"
                        )
                    quorum = self._diverse_attestation_quorum(
                        attestations=accepted,
                        required=required,
                        dimensions=policy.get(
                            "independence_dimensions", ["actor"]
                        ),
                        finalizer=profile_snapshot(verifier),
                    )
                    if quorum is None:
                        raise EvidenceError(
                            f"Task requires {required} mutually independent accepting "
                            "attestations under its declared dimensions"
                        )
                    verification["attestations"] = [
                        {
                            "actor": item["actor"],
                            "decision": item["decision"],
                            "evidence_sha256": item.get("evidence", {}).get("sha256"),
                        }
                        for item in quorum
                    ]
                    if verification_manifest is None:
                        raise EvidenceError(
                            "Independent finalizer verification manifest is required"
                        )
                    evidence, archive = self._validate_verifier_manifest(
                        actor=actor,
                        task=task,
                        manifest_path=verification_manifest,
                        label="verification",
                    )
                    verification["evidence"] = evidence
                    verification["archive"] = archive
                verified = transition(
                    task,
                    "verified",
                    verification=verification,
                )
                return self._commit_task(
                    actor=actor,
                    action="task.verified",
                    task=verified,
                )
            rejected = transition(
                task,
                "rejected",
                verification=verification,
            )
            return self._commit_task(
                actor=actor,
                action="task.rejected",
                task=rejected,
            )

    def invalidate(
        self,
        *,
        actor: str,
        task_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Quarantine a past verification without rewriting its evidence."""

        self._require_orchestrator(actor)
        if not reason.strip():
            raise ConfigurationError("Invalidation reason cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"verified", "archived"}:
                raise TransitionError(
                    f"Cannot invalidate task {task_id} in state {task['state']}"
                )
            invalidated = transition(
                task,
                "invalidated",
                invalidation={
                    "actor": actor,
                    "reason": reason.strip(),
                    "invalidated_at": utc_now(),
                    "prior_state": task["state"],
                },
            )
            return self._commit_task(
                actor=actor,
                action="task.invalidated",
                task=invalidated,
                details={"reason": reason.strip()},
                require_orchestrator=True,
            )

    def requeue(
        self,
        *,
        actor: str,
        task_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Return a blocked or rejected task to pending for another attempt."""

        self._require_orchestrator(actor)
        if not reason.strip():
            raise ConfigurationError("Requeue reason cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"blocked", "rejected", "invalidated"}:
                raise TransitionError(
                    f"Cannot requeue task {task_id} in state {task['state']}"
                )
            pending = transition(
                task,
                "pending",
                lease=None,
                result=None,
                verification=None,
                verification_attestations=[],
                invalidation=None,
                revocation=None,
                execution=None,
                blocked_reason=None,
            )
            return self._commit_task(
                actor=actor,
                action="task.requeued",
                task=pending,
                details={"reason": reason.strip()},
                require_orchestrator=True,
            )

    def archive(self, *, actor: str, task_id: str) -> dict[str, Any]:
        """Mark a verified task archived while retaining its live projection."""

        self._require_orchestrator(actor)
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            archived = transition(task, "archived")
            result = self._commit_task(
                actor=actor,
                action="task.archived",
                task=archived,
                require_orchestrator=True,
            )
            atomic_write_json(self.archive_dir / f"{task_id}.json", result)
            return result

    def recover_expired(
        self,
        *,
        actor: str,
        now: str | None = None,
    ) -> list[dict[str, Any]]:
        """Quarantine expired leases without silently releasing live resources."""

        self._require_orchestrator(actor)
        recovered: list[dict[str, Any]] = []
        for candidate in self.list_tasks():
            if candidate["state"] not in {"claimed", "running"}:
                continue
            with self._task_lock(candidate["id"]):
                task = self.get_task(candidate["id"])
                if task["state"] not in {"claimed", "running"} or not lease_expired(
                    task, now
                ):
                    continue
                if task["state"] == "running":
                    recovered_task = transition(
                        task,
                        "revoking",
                        blocked_reason=(
                            "Lease expired while running; termination must be "
                            "confirmed before requeue"
                        ),
                        revocation={
                            "requested_by": actor,
                            "requested_at": utc_now(),
                            "reason": "Lease expired while task was running.",
                            "acknowledged_by": None,
                            "acknowledged_at": None,
                            "termination_evidence": None,
                        },
                    )
                    action = "task.lease_expired_termination_unconfirmed"
                else:
                    recovered_task = transition(
                        task,
                        "blocked",
                        lease=None,
                        blocked_reason="Lease expired; manual requeue required",
                    )
                    action = "task.lease_expired"
                recovered.append(
                    self._commit_task(
                        actor=actor,
                        action=action,
                        task=recovered_task,
                        require_orchestrator=True,
                    )
                )
        return recovered

    def audit_projections(self, *, repair: bool = False) -> dict[str, Any]:
        """Compare task JSON projections with the signed event stream."""

        if repair:
            raise AuthorizationError(
                "Projection repair requires repair_projections(actor=...)"
            )
        return self._audit_projections(repair=False)

    def _audit_projections(self, *, repair: bool) -> dict[str, Any]:
        ledger_status = self.ledger.verify()
        projected = self.ledger.projected_tasks()
        mismatches: list[str] = []
        repaired: list[str] = []
        for task_id, ledger_task in projected.items():
            path = self._task_path(task_id)
            if not path.exists():
                mismatches.append(f"{task_id}: projection missing")
                if repair:
                    atomic_write_json(path, ledger_task)
                    repaired.append(task_id)
                continue
            disk_task = read_json(path)
            disk_comparable = {
                key: value for key, value in disk_task.items() if key != "last_event_hash"
            }
            if disk_comparable != ledger_task:
                mismatches.append(f"{task_id}: projection differs from ledger")
                if repair:
                    atomic_write_json(path, ledger_task)
                    repaired.append(task_id)
        unknown = {
            path.stem for path in self.tasks_dir.glob("*.json")
        } - set(projected)
        mismatches.extend(f"{task_id}: no ledger event" for task_id in sorted(unknown))
        if mismatches and not repair:
            raise IntegrityError("; ".join(mismatches))
        return {
            "ledger": ledger_status,
            "task_snapshots": len(projected),
            "mismatches": mismatches,
            "repaired": repaired,
        }

    def repair_projections(self, *, actor: str) -> dict[str, Any]:
        """Rebuild missing or changed task projections as the orchestrator."""

        with self._orchestrator_lock():
            self._require_orchestrator(actor)
            return self._audit_projections(repair=True)

    def audit_independence(
        self,
        *,
        dimensions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Audit every historical verification event without losing old attempts."""

        required = validate_independence_dimensions(
            dimensions or ["actor", "controller", "model_family"]
        )
        events = self.ledger.read()
        self.ledger.verify()
        current_agents = {
            agent_id: profile_snapshot(record)
            for agent_id, record in self._signed_agents().items()
        }
        invalidated_attempts: set[tuple[str, int]] = set()
        for event in events:
            if event.get("action") != "task.invalidated":
                continue
            task = event.get("payload", {}).get("task")
            if isinstance(task, dict) and isinstance(task.get("attempt"), int):
                invalidated_attempts.add((str(task.get("id")), task["attempt"]))

        historical_agents: dict[str, dict[str, Any]] = {}
        records: list[dict[str, Any]] = []
        unknown_values = {None, "", "unknown", "unspecified"}

        for event in events:
            action = event.get("action")
            if action in {"agent.added", "agent.updated"}:
                agent = event.get("payload", {}).get("agent")
                if isinstance(agent, dict) and isinstance(agent.get("id"), str):
                    historical_agents[agent["id"]] = deepcopy(agent)
                continue
            if action != "task.verified":
                continue

            task = event.get("payload", {}).get("task")
            if not isinstance(task, dict):
                continue
            verification = task.get("verification")
            if not isinstance(verification, dict):
                continue
            task_id = str(task.get("id"))
            attempt = int(task.get("attempt", 0))
            verifier_id = str(verification.get("actor"))
            submission = task.get("result", {}).get("submission", {})
            author_id = str(
                submission.get("author")
                if isinstance(submission, dict) and submission.get("author")
                else task.get("owner")
            )

            author = verification.get("author")
            verifier = verification.get("verifier")
            frozen_profiles = isinstance(author, dict) and isinstance(verifier, dict)
            if not isinstance(author, dict) and author_id in historical_agents:
                author = profile_snapshot(historical_agents[author_id])
            if not isinstance(verifier, dict) and verifier_id in historical_agents:
                verifier = profile_snapshot(historical_agents[verifier_id])

            def complete(profile: Any) -> bool:
                if not isinstance(profile, dict):
                    return False
                for dimension in required:
                    key = (
                        "id"
                        if dimension == "actor"
                        else "controller_id"
                        if dimension == "controller"
                        else dimension
                    )
                    if profile.get(key) in unknown_values:
                        return False
                return True

            profile_source = "frozen_verification"
            if not complete(author) or not complete(verifier):
                profile_source = "current_retrospective"
                author = current_agents.get(author_id)
                verifier = current_agents.get(verifier_id)

            if not isinstance(author, dict) or not isinstance(verifier, dict):
                status = "inconclusive"
                result = {
                    "independent": False,
                    "dimensions": required,
                    "checks": {},
                    "reasons": ["author or verifier profile is unavailable"],
                }
            else:
                result = evaluate_independence(
                    author=author,
                    verifier=verifier,
                    dimensions=required,
                )
                missing_identity = any(
                    "not declared" in reason for reason in result["reasons"]
                )
                if result["independent"] and (
                    profile_source != "frozen_verification"
                    or not frozen_profiles
                ):
                    status = "inconclusive"
                    result["reasons"].append(
                        "identity was not frozen at verification time"
                    )
                elif result["independent"]:
                    status = "independent"
                elif missing_identity:
                    status = "inconclusive"
                else:
                    status = "non_independent"

            records.append(
                {
                    "task_id": task_id,
                    "attempt": attempt,
                    "verification_sequence": event.get("sequence"),
                    "verification_event_hash": event.get("event_hash"),
                    "author": author_id,
                    "verifier": verifier_id,
                    "status": status,
                    "profile_source": profile_source,
                    "result": result,
                    "proxy": (
                        submission.get("submitted_by")
                        if isinstance(submission, dict)
                        else None
                    ),
                    "quarantined": (
                        task_id,
                        attempt,
                    )
                    in invalidated_attempts,
                }
            )
        return {
            "dimensions": required,
            "records": records,
            "summary": {
                status: sum(record["status"] == status for record in records)
                for status in ("independent", "non_independent", "inconclusive")
            }
            | {
                "action_required": sum(
                    record["status"] in {"non_independent", "inconclusive"}
                    and not record.get("quarantined", False)
                    for record in records
                ),
                "quarantined": sum(
                    record.get("quarantined", False) for record in records
                ),
            },
        }

    def status(self) -> dict[str, Any]:
        """Return a dashboard-ready workspace summary."""

        tasks = self.list_tasks()
        counts = {
            state: sum(task["state"] == state for task in tasks)
            for state in (
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
            )
        }
        return {
            "workspace": self.config["name"],
            "workspace_id": self.config["workspace_id"],
            "orchestrator": self.orchestrator,
            "agents": len(self.list_agents()),
            "tasks": len(tasks),
            "states": counts,
            "ledger": self.ledger.verify(),
        }
