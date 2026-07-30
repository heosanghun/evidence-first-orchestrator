"""Transactional workspace broker and task state machine."""

from __future__ import annotations

import hashlib
import secrets
from copy import deepcopy
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
from .independence import (
    audit_verification_events,
    build_identity,
    evaluate_independence,
    identity_snapshot,
)
from .ledger import Ledger
from .lock import FileLock
from .model import lease_expired, lease_expiry, new_task, transition, validate_task
from .provenance import (
    validate_git_commit,
    validate_git_provenance,
    validate_git_source_claim,
)
from .util import (
    atomic_write_json,
    is_relative_to,
    parse_utc,
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
        orchestrator_control_principal: str | None = None,
        orchestrator_model_family: str | None = None,
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
        orchestrator_identity = None
        if orchestrator_control_principal or orchestrator_model_family:
            if not orchestrator_control_principal or not orchestrator_model_family:
                raise ConfigurationError(
                    "Both orchestrator_control_principal and "
                    "orchestrator_model_family are required together"
                )
            orchestrator_identity = build_identity(
                control_principal=orchestrator_control_principal,
                model_family=orchestrator_model_family,
            )
        workspace._commit_agent(
            actor=orchestrator,
            record={
                "schema_version": 2,
                "id": orchestrator,
                "role": "orchestrator",
                "mode": "manual",
                "command": None,
                "created_at": utc_now(),
                "write_roots": ["tasks", "shared", "archive"],
                "identity": orchestrator_identity,
            },
        )
        if preset == "antigravity-codex-claude":
            workspace.add_agent(
                actor=orchestrator,
                agent_id="codex",
                role="worker",
                mode="manual",
                control_principal="codex",
                model_family="openai-codex",
            )
            workspace.add_agent(
                actor=orchestrator,
                agent_id="claude",
                role="worker",
                mode="manual",
                control_principal="claude",
                model_family="anthropic-claude",
            )
        elif preset is not None:
            raise ConfigurationError(f"Unknown workspace preset: {preset}")
        return workspace

    @property
    def orchestrator(self) -> str:
        return str(self.config["orchestrator"])

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
    ) -> dict[str, Any]:
        self.ledger.append(
            actor=actor,
            action=action,
            task_id=None,
            payload={"agent": record},
        )
        self._write_agent(record)
        return record

    def _signed_agents(self) -> dict[str, dict[str, Any]]:
        self.ledger.verify()
        signed: dict[str, dict[str, Any]] = {}
        for event in self.ledger.read():
            if event.get("action") not in {
                "agent.added",
                "agent.identity_attested",
            }:
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
        self.get_agent(actor)
        if actor != self.orchestrator:
            raise AuthorizationError(
                f"Only orchestrator {self.orchestrator!r} may perform this action"
            )

    def add_agent(
        self,
        *,
        actor: str,
        agent_id: str,
        role: str = "worker",
        mode: str = "manual",
        command: list[str] | None = None,
        write_roots: list[str] | None = None,
        control_principal: str | None = None,
        model_family: str | None = None,
        alias_of: str | None = None,
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
        identity = self._prepare_identity(
            agent_id=agent_id,
            control_principal=control_principal,
            model_family=model_family,
            alias_of=alias_of,
        )
        record = {
            "schema_version": 2,
            "id": agent_id,
            "role": role,
            "mode": mode,
            "command": command,
            "created_at": utc_now(),
            "write_roots": write_roots or [f"reports/{agent_id}", f"runs/{agent_id}"],
            "identity": identity,
        }
        with self._agent_lock():
            path = self._agent_path(agent_id)
            if path.exists() or agent_id in self._signed_agents():
                raise ConfigurationError(f"Agent already exists: {agent_id}")
            return self._commit_agent(actor=actor, record=record)

    def _prepare_identity(
        self,
        *,
        agent_id: str,
        control_principal: str | None,
        model_family: str | None,
        alias_of: str | None,
    ) -> dict[str, Any] | None:
        if alias_of:
            if control_principal or model_family:
                raise ConfigurationError(
                    "Alias identity inherits control principal and model family"
                )
            target_id = validate_agent_id(alias_of)
            if target_id == agent_id:
                raise ConfigurationError("Agent cannot alias itself")
            target = self.get_agent(target_id)
            target_identity = identity_snapshot(
                target_id,
                target.get("identity"),
            )
            if target_identity is None:
                raise ConfigurationError(
                    f"Alias target {target_id!r} has no attested identity"
                )
            alias_chain = [target_id, *target_identity.get("alias_chain", [])]
            if agent_id in alias_chain:
                raise ConfigurationError("Agent identity alias chain contains a cycle")
            return build_identity(
                control_principal=target_identity["control_principal"],
                model_family=target_identity["model_family"],
                alias_of=target_id,
                alias_chain=alias_chain,
            )
        if control_principal is None and model_family is None:
            return None
        if not control_principal or not model_family:
            raise ConfigurationError(
                "Both control_principal and model_family are required together"
            )
        return build_identity(
            control_principal=control_principal,
            model_family=model_family,
        )

    def attest_agent_identity(
        self,
        *,
        actor: str,
        agent_id: str,
        control_principal: str | None = None,
        model_family: str | None = None,
        alias_of: str | None = None,
    ) -> dict[str, Any]:
        """Append a signed, prospective identity declaration for an agent."""

        self._require_orchestrator(actor)
        agent_id = validate_agent_id(agent_id)
        with self._agent_lock():
            current = self.get_agent(agent_id)
            current_identity = current.get("identity")
            current_alias = (
                current_identity.get("alias_of")
                if isinstance(current_identity, dict)
                else None
            )
            if current_alias and alias_of != current_alias:
                raise ConfigurationError(
                    "An attested alias lineage cannot be removed or reparented; "
                    "register a new agent identity instead"
                )
            identity = self._prepare_identity(
                agent_id=agent_id,
                control_principal=control_principal,
                model_family=model_family,
                alias_of=alias_of,
            )
            if identity is None:
                raise ConfigurationError("Identity attestation cannot be empty")
            updated = deepcopy(current)
            updated.update(
                {
                    "schema_version": 2,
                    "identity": identity,
                    "identity_attested_at": utc_now(),
                    "identity_attested_by": actor,
                }
            )
            return self._commit_agent(
                actor=actor,
                action="agent.identity_attested",
                record=updated,
            )

    def _agent_identity(self, actor: str) -> dict[str, Any] | None:
        agent = self.get_agent(actor)
        return identity_snapshot(actor, agent.get("identity"))

    def _require_verifier(self, actor: str) -> dict[str, Any]:
        agent = self.get_agent(actor)
        if agent["role"] not in {"orchestrator", "verifier"}:
            raise AuthorizationError(
                "Only an orchestrator or registered verifier may verify a task"
            )
        return agent

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
        )
        projected = deepcopy(snapshot)
        projected["last_event_hash"] = event["event_hash"]
        atomic_write_json(self._task_path(task["id"]), projected)
        return projected

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
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a task with immutable preregistered permissions and gates."""

        self._require_orchestrator(actor)
        worker = self.get_agent(owner)
        if worker["role"] not in {"worker", "verifier"}:
            raise ConfigurationError(f"Task owner {owner!r} is not a worker")
        defaults = self.config["defaults"]
        merged_permissions = {
            **defaults["permissions"],
            **(permissions or {}),
        }
        merged_gates = {**defaults["gates"], **(gates or {})}
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
            idempotency_key=idempotency_key,
        )
        path = self._task_path(task_id)
        with self._creation_lock():
            for existing in self.list_tasks():
                if existing.get("idempotency_key") == task["idempotency_key"]:
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
            )

    def _prerequisites_ready(self, task: dict[str, Any]) -> bool:
        for task_id in task["prerequisites"]:
            if self.get_task(task_id)["state"] not in {"verified", "archived"}:
                return False
        return True

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def report_proxy_status(
        self,
        *,
        actor: str,
        author: str,
        task_id: str,
        phase: str,
        reference: str,
        note: str,
    ) -> dict[str, Any]:
        """Record an orchestrator-observed external phase without a worker lease."""

        self._require_orchestrator(actor)
        author = validate_agent_id(author)
        normalized_phase = str(phase).strip().lower()
        phases = {"dispatched", "working", "reviewing", "ready", "blocked"}
        if normalized_phase not in phases:
            raise ConfigurationError(
                "Proxy status phase must be dispatched, working, reviewing, "
                "ready, or blocked"
            )
        if not isinstance(reference, str):
            raise ConfigurationError("Proxy status reference must be a string")
        normalized_reference = reference.strip()
        if not normalized_reference or len(normalized_reference) > 200:
            raise ConfigurationError(
                "Proxy status reference must be 1 to 200 characters"
            )
        if not isinstance(note, str):
            raise ConfigurationError("Proxy status note must be a string")
        normalized_note = note.strip()
        if not normalized_note or len(normalized_note) > 500:
            raise ConfigurationError("Proxy status note must be 1 to 500 characters")

        author_identity = self._agent_identity(author)
        transport_identity = self._agent_identity(actor)
        if author_identity is None:
            raise AuthorizationError(
                f"Proxy author {author!r} needs a signed identity attestation"
            )
        if transport_identity is None:
            raise AuthorizationError(
                f"Transport actor {actor!r} needs a signed identity attestation"
            )

        allowed_next = {
            "dispatched": {"dispatched", "working", "blocked"},
            "working": {"working", "reviewing", "blocked"},
            "reviewing": {"reviewing", "ready", "blocked"},
            "ready": {"ready", "blocked"},
            "blocked": {"blocked", "working"},
        }
        now = utc_now()
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "pending":
                raise TransitionError(
                    "Proxy status reports require a pending task and never "
                    f"replace canonical state transitions; observed {task['state']}"
                )
            if task["owner"] != author:
                raise AuthorizationError(
                    f"Proxy author {author!r} is not task owner {task['owner']!r}"
                )
            current = task.get("external_status")
            if current is None:
                if normalized_phase != "dispatched":
                    raise TransitionError(
                        "The first proxy status phase must be dispatched"
                    )
            elif isinstance(current, dict):
                if current.get("reference") != normalized_reference:
                    raise AuthorizationError(
                        "Proxy status reference cannot change during a dispatch"
                    )
                current_phase = str(current.get("phase") or "")
                if normalized_phase not in allowed_next.get(current_phase, set()):
                    raise TransitionError(
                        "Proxy status phase cannot regress "
                        f"{current_phase!r} -> {normalized_phase!r}"
                    )
            else:
                raise IntegrityError("Task external_status projection is malformed")

            status = {
                "schema_version": 1,
                "phase": normalized_phase,
                "reference": normalized_reference,
                "note": normalized_note,
                "reported_at": now,
                "reported_by": actor,
                "author": author,
                "transport_identity": transport_identity,
                "author_identity": author_identity,
                "assertion": "transport_observation",
            }
            updated = deepcopy(task)
            updated["external_status"] = status
            updated["revision"] += 1
            updated["updated_at"] = now
            return self._commit_task(
                actor=actor,
                action="task.proxy_status_reported",
                task=updated,
                details={
                    "author_actor": author,
                    "transport_actor": actor,
                    "phase": normalized_phase,
                    "reference": normalized_reference,
                    "assertion": "transport_observation",
                },
            )

    def authorize_proxy_submission(
        self,
        *,
        actor: str,
        task_id: str,
        transport_actor: str,
        remote_url: str,
        branch: str,
        commit: str,
        duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Issue a one-time signed grant for an offline worker delivery."""

        self._require_orchestrator(actor)
        transport_actor = validate_agent_id(transport_actor)
        self.get_agent(transport_actor)
        if transport_actor != self.orchestrator:
            raise AuthorizationError(
                "Proxy transport must be the workspace orchestrator"
            )
        normalized_remote, normalized_branch = validate_git_source_claim(
            remote_url,
            branch,
        )
        normalized_commit = validate_git_commit(commit)
        duration = duration_seconds or int(
            self.config["defaults"]["lease_seconds"]
        )
        now = utc_now()
        token = secrets.token_urlsafe(24)
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "pending":
                raise TransitionError(
                    "Proxy authorization requires a pending task"
                )
            if task["owner"] == transport_actor:
                raise AuthorizationError(
                    "The task owner must use the normal submission path"
                )
            existing = task.get("proxy_grant")
            if (
                isinstance(existing, dict)
                and existing.get("consumed_at") is None
                and parse_utc(str(existing["expires_at"])) > parse_utc(now)
            ):
                raise TransitionError(
                    "Task already has an active proxy authorization"
                )
            updated = deepcopy(task)
            updated["proxy_grant"] = {
                "schema_version": 1,
                "workspace_id": self.config["workspace_id"],
                "task_id": task_id,
                "next_attempt": task["attempt"] + 1,
                "author": task["owner"],
                "transport_actor": transport_actor,
                "remote_url": normalized_remote,
                "branch": normalized_branch,
                "commit": normalized_commit,
                "issued_at": now,
                "expires_at": lease_expiry(duration, now),
                "token_hash": self._token_hash(token),
                "consumed_at": None,
                "consumed_by": None,
            }
            updated["revision"] += 1
            updated["updated_at"] = now
            projection = self._commit_task(
                actor=actor,
                action="task.proxy_authorized",
                task=updated,
                details={
                    "author_actor": task["owner"],
                    "transport_actor": transport_actor,
                    "remote_url": normalized_remote,
                    "branch": normalized_branch,
                    "commit": normalized_commit,
                },
            )
            return {"task": projection, "proxy_token": token}

    def _require_proxy_grant(
        self,
        task: dict[str, Any],
        *,
        actor: str,
        author: str,
        proxy_token: str,
    ) -> dict[str, Any]:
        grant = task.get("proxy_grant")
        if not isinstance(grant, dict):
            raise AuthorizationError(
                f"Task {task['id']} has no proxy authorization"
            )
        expected = {
            "workspace_id": self.config["workspace_id"],
            "task_id": task["id"],
            "next_attempt": task["attempt"] + 1,
            "author": author,
            "transport_actor": actor,
        }
        mismatches = [
            key for key, value in expected.items() if grant.get(key) != value
        ]
        if mismatches:
            raise AuthorizationError(
                "Proxy authorization does not match this submission: "
                + ", ".join(mismatches)
            )
        if grant.get("consumed_at") is not None:
            raise AuthorizationError("Proxy authorization was already consumed")
        if parse_utc(str(grant["expires_at"])) <= parse_utc(utc_now()):
            raise AuthorizationError("Proxy authorization has expired")
        if not secrets.compare_digest(
            str(grant.get("token_hash", "")),
            self._token_hash(proxy_token),
        ):
            raise AuthorizationError("Proxy authorization token is invalid")
        return deepcopy(grant)

    def claim(
        self,
        *,
        actor: str,
        task_id: str | None = None,
        lease_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Atomically claim one ready task and return its one-time lease token."""

        agent = self.get_agent(actor)
        if agent["role"] not in {"worker", "verifier"}:
            raise AuthorizationError("Only worker or verifier agents may claim tasks")
        candidate_ids = (
            [validate_task_id(task_id)]
            if task_id is not None
            else [
                validate_task_id(path.stem)
                for path in sorted(self.tasks_dir.glob("*.json"))
            ]
        )
        for candidate_id in candidate_ids:
            # Read the ledger-backed projection only after acquiring the task
            # lock. Otherwise a concurrent commit can expose the new ledger
            # event before its projection file is atomically replaced.
            with self._task_lock(candidate_id):
                task = self.get_task(candidate_id)
                if task["owner"] != actor:
                    if task_id is not None:
                        raise AuthorizationError(
                            f"Task {task['id']} is owned by {task['owner']}"
                        )
                    continue
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
        if lease_expired(task):
            raise LeaseError(f"Task {task['id']} lease has expired")

    def start(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
    ) -> dict[str, Any]:
        """Move a claimed task into running state."""

        with self._task_lock(task_id):
            task = self.get_task(task_id)
            self._require_lease(task, actor=actor, lease_token=lease_token)
            started = transition(task, "running")
            return self._commit_task(
                actor=actor,
                action="task.started",
                task=started,
            )

    def heartbeat(
        self,
        *,
        actor: str,
        task_id: str,
        lease_token: str,
    ) -> dict[str, Any]:
        """Extend a claimed or running task lease."""

        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"claimed", "running"}:
                raise TransitionError(
                    f"Cannot heartbeat task {task_id} in state {task['state']}"
                )
            self._require_lease(task, actor=actor, lease_token=lease_token)
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
        """Record a genuine blocker without claiming successful completion."""

        if not reason.strip():
            raise ConfigurationError("Blocked reason cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] not in {"claimed", "running"}:
                raise TransitionError(
                    f"Cannot block task {task_id} in state {task['state']}"
                )
            self._require_lease(task, actor=actor, lease_token=lease_token)
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

        author_identity = self._agent_identity(actor)
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
        if (
            task_for_validation["gates"].get(
                "require_independent_verification",
                True,
            )
            and author_identity is None
        ):
            raise AuthorizationError(
                f"Agent {actor!r} needs a signed identity attestation before "
                "submitting work that requires independent verification"
            )
        evidence["authorship"] = {
            "actor": actor,
            "identity": author_identity,
        }
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "running":
                raise TransitionError(
                    f"Task {task_id} must be running before submission"
                )
            self._require_lease(task, actor=actor, lease_token=lease_token)
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
            submitted = transition(
                task,
                "submitted",
                lease=None,
                result=evidence,
                verification=None,
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

    def proxy_submit(
        self,
        *,
        actor: str,
        author: str,
        task_id: str,
        proxy_token: str,
        report_path: str | Path,
        manifest_path: str | Path,
        provenance_path: str | Path,
        source_repository: str | Path,
    ) -> dict[str, Any]:
        """Transport an unreachable worker's Git-bound evidence without impersonation."""

        self._require_orchestrator(actor)
        author = validate_agent_id(author)
        if actor == author:
            raise AuthorizationError(
                "An author must use the normal claim/start/submit path"
            )
        author_identity = self._agent_identity(author)
        transport_identity = self._agent_identity(actor)
        if author_identity is None:
            raise AuthorizationError(
                f"Proxy author {author!r} needs a signed identity attestation"
            )
        if transport_identity is None:
            raise AuthorizationError(
                f"Transport actor {actor!r} needs a signed identity attestation"
            )

        report = Path(report_path).resolve()
        manifest = Path(manifest_path).resolve()
        transport_root = self.reports_dir / actor
        if not is_relative_to(report, transport_root):
            raise AuthorizationError(
                "Proxy report must be under the transport actor's report "
                f"directory: {transport_root}"
            )
        if not is_relative_to(manifest, transport_root):
            raise AuthorizationError(
                "Proxy manifest must be under the transport actor's report "
                f"directory: {transport_root}"
            )

        task_for_validation = self.get_task(task_id)
        if task_for_validation["owner"] != author:
            raise AuthorizationError(
                f"Proxy author {author!r} is not task owner "
                f"{task_for_validation['owner']!r}"
            )
        grant = self._require_proxy_grant(
            task_for_validation,
            actor=actor,
            author=author,
            proxy_token=proxy_token,
        )
        evidence = validate_submission(
            report,
            manifest,
            permissions=task_for_validation["permissions"],
            gates=task_for_validation["gates"],
        )
        max_evidence_bytes = int(
            self.config["defaults"].get(
                "max_evidence_bytes",
                50 * 1024 * 1024,
            )
        )
        provenance = validate_git_provenance(
            provenance_path,
            source_repository=source_repository,
            report_root=transport_root,
            expected_author=author,
            evidence=evidence,
            max_blob_bytes=max_evidence_bytes,
        )
        if provenance["remote_url"] != grant["remote_url"]:
            raise AuthorizationError(
                "Git provenance remote_url differs from the proxy authorization"
            )
        if provenance["branch"] != grant["branch"]:
            raise AuthorizationError(
                "Git provenance branch differs from the proxy authorization"
            )
        if provenance["commit"] != grant["commit"]:
            raise AuthorizationError(
                "Git provenance commit differs from the proxy authorization"
            )
        evidence["authorship"] = {
            "actor": author,
            "identity": author_identity,
            "method": "proxy",
        }
        evidence["transport"] = {
            "actor": actor,
            "identity": transport_identity,
            "envelope_creator": actor,
            "grant_event_hash": task_for_validation["last_event_hash"],
        }
        evidence["transport_independence"] = evaluate_independence(
            author_identity,
            transport_identity,
        )
        evidence["provenance"] = provenance

        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "pending":
                raise TransitionError(
                    f"Proxy submission requires a pending task, observed "
                    f"{task['state']}"
                )
            if task["owner"] != author:
                raise AuthorizationError(
                    f"Proxy author {author!r} is not task owner {task['owner']!r}"
                )
            grant = self._require_proxy_grant(
                task,
                actor=actor,
                author=author,
                proxy_token=proxy_token,
            )
            if provenance["remote_url"] != grant["remote_url"]:
                raise AuthorizationError(
                    "Git provenance remote_url differs from the proxy authorization"
                )
            if provenance["branch"] != grant["branch"]:
                raise AuthorizationError(
                    "Git provenance branch differs from the proxy authorization"
                )
            if provenance["commit"] != grant["commit"]:
                raise AuthorizationError(
                    "Git provenance commit differs from the proxy authorization"
                )
            attempt = int(grant["next_attempt"])
            evidence["archive"] = archive_evidence_bundle(
                submissions_root=self.submissions_dir,
                task_id=task_id,
                attempt=attempt,
                label="proxy-worker",
                report=evidence["report"],
                manifest=evidence["manifest"],
                max_artifact_bytes=max_evidence_bytes,
                extra_files=[
                    {
                        "path": provenance["path"],
                        "sha256": provenance["sha256"],
                        "kind": "provenance_manifest",
                        "force": True,
                    }
                ],
            )
            submitted = transition(
                task,
                "submitted",
                attempt=attempt,
                lease=None,
                proxy_grant={
                    **grant,
                    "consumed_at": utc_now(),
                    "consumed_by": actor,
                },
                result=evidence,
                verification=None,
            )
            return self._commit_task(
                actor=actor,
                action="task.proxy_submitted",
                task=submitted,
                details={
                    "author_actor": author,
                    "transport_actor": actor,
                    "report_sha256": evidence["report"]["sha256"],
                    "manifest_sha256": evidence["manifest"]["sha256"],
                    "provenance_sha256": provenance["sha256"],
                    "source_commit": provenance["commit"],
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
        """Accept or reject a submitted task after independent verification."""

        verifier_agent = self._require_verifier(actor)
        if decision not in {"accept", "reject"}:
            raise ConfigurationError("Verification decision must be accept or reject")
        if not note.strip():
            raise ConfigurationError("Verification note cannot be empty")
        with self._task_lock(task_id):
            task = self.get_task(task_id)
            if task["state"] != "submitted":
                raise TransitionError(
                    f"Task {task_id} is {task['state']}, not submitted"
                )
            verification: dict[str, Any] = {
                "actor": actor,
                "identity": identity_snapshot(
                    actor,
                    verifier_agent.get("identity"),
                ),
                "decision": decision,
                "note": note.strip(),
                "verified_at": utc_now(),
            }
            transport = task.get("result", {}).get("transport")
            if isinstance(transport, dict):
                transport_identity = transport.get("identity")
                if not isinstance(transport_identity, dict):
                    transport_identity = None
                transport_independence = evaluate_independence(
                    transport_identity,
                    verification["identity"],
                )
                verification["transport_overlap"] = not transport_independence[
                    "independent"
                ]
                verification["transport_independence"] = transport_independence
                verification["transport"] = deepcopy(transport)
            if task["gates"].get("require_independent_verification", True):
                authorship = task.get("result", {}).get("authorship", {})
                worker_identity = authorship.get("identity")
                if not isinstance(worker_identity, dict):
                    worker_identity = None
                verifier_identity = verification["identity"]
                independence = evaluate_independence(
                    worker_identity,
                    verifier_identity,
                )
                verification["independence"] = independence
                if not independence["independent"]:
                    reasons = ", ".join(independence["reasons"])
                    raise AuthorizationError(
                        "Independent verification could not be established: "
                        f"{reasons}"
                    )
            if decision == "accept":
                if task["gates"].get("require_independent_verification", True):
                    if verification_manifest is None:
                        raise EvidenceError(
                            "Independent verification manifest is required"
                        )
                    verification_path = Path(verification_manifest).resolve()
                    verifier_root = self.reports_dir / actor
                    if not is_relative_to(verification_path, verifier_root):
                        raise AuthorizationError(
                            "Verification manifest must be under the verifier's "
                            f"report directory: {verifier_root}"
                        )
                    verification["evidence"] = validate_manifest(
                        verification_path,
                        permissions=task["permissions"],
                        gates=task["gates"],
                    )
                    worker_manifest_sha = (
                        task.get("result", {}).get("manifest", {}).get("sha256")
                    )
                    if (
                        worker_manifest_sha
                        and verification["evidence"]["sha256"] == worker_manifest_sha
                    ):
                        raise EvidenceError(
                            "Independent verification cannot reuse the worker manifest"
                        )
                    verification["archive"] = archive_evidence_bundle(
                        submissions_root=self.submissions_dir,
                        task_id=task_id,
                        attempt=task["attempt"],
                        label="verification",
                        report=None,
                        manifest=verification["evidence"],
                        max_artifact_bytes=int(
                            self.config["defaults"].get(
                                "max_evidence_bytes", 50 * 1024 * 1024
                            )
                        ),
                    )
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
            if task["state"] not in {"blocked", "rejected"}:
                raise TransitionError(
                    f"Cannot requeue task {task_id} in state {task['state']}"
                )
            pending = transition(
                task,
                "pending",
                lease=None,
                result=None,
                verification=None,
                blocked_reason=None,
            )
            return self._commit_task(
                actor=actor,
                action="task.requeued",
                task=pending,
                details={"reason": reason.strip()},
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
            )
            atomic_write_json(self.archive_dir / f"{task_id}.json", result)
            return result

    def recover_expired(
        self,
        *,
        actor: str,
        now: str | None = None,
    ) -> list[dict[str, Any]]:
        """Move expired leases to blocked so they cannot run twice silently."""

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
                blocked = transition(
                    task,
                    "blocked",
                    lease=None,
                    blocked_reason="Lease expired; manual requeue required",
                )
                recovered.append(
                    self._commit_task(
                        actor=actor,
                        action="task.lease_expired",
                        task=blocked,
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

    def audit_independence(
        self,
        *,
        identity_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Read historical verification events without changing the ledger."""

        self.ledger.verify()
        agents = {agent["id"]: agent for agent in self.list_agents()}
        return audit_verification_events(
            self.ledger.read(),
            agents,
            policy=identity_policy,
        )

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

        self._require_orchestrator(actor)
        return self._audit_projections(repair=True)

    def status(self) -> dict[str, Any]:
        """Return a dashboard-ready workspace summary."""

        tasks = self.list_tasks()
        counts = {
            state: sum(task["state"] == state for task in tasks)
            for state in (
                "pending",
                "claimed",
                "running",
                "blocked",
                "submitted",
                "verified",
                "rejected",
                "archived",
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
