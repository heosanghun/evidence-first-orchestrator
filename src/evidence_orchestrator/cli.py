"""Command-line interface for Evidence First Orchestrator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .adapter import run_loop, run_once
from .dashboard import serve
from .doctor import audit_legacy_workspace, audit_workspace
from .errors import EFOError
from .evidence import validate_submission
from .fingerprint import workspace_fingerprint
from .workspace import Workspace


def _emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _read_description(args: argparse.Namespace) -> str:
    if args.description_file:
        return Path(args.description_file).read_text(encoding="utf-8")
    if args.description:
        return args.description
    raise ValueError("Either --description or --description-file is required")


def _parse_command(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, list) or not all(
        isinstance(item, str) and item for item in parsed
    ):
        raise ValueError("--command-json must be a JSON array of non-empty strings")
    return parsed


def _parse_json_array(value: str, *, option: str) -> list[Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"{option} must be a JSON array")
    return parsed


def _workspace(path: str) -> Workspace:
    return Workspace(Path(path))


def _cmd_init(args: argparse.Namespace) -> None:
    workspace = Workspace.initialize(
        args.path,
        name=args.name,
        orchestrator=args.orchestrator,
        preset=args.preset,
    )
    _emit(workspace.status())


def _cmd_status(args: argparse.Namespace) -> None:
    workspace = _workspace(args.path)
    _emit({"status": workspace.status(), "tasks": workspace.list_tasks()})


def _cmd_agent_add(args: argparse.Namespace) -> None:
    workspace = _workspace(args.path)
    record = workspace.add_agent(
        actor=args.actor,
        agent_id=args.agent_id,
        role=args.role,
        mode=args.mode,
        command=_parse_command(args.command_json),
        prompt_stdin=args.prompt_stdin,
        write_roots=args.write_root,
        controller_id=args.controller_id,
        provider=args.provider,
        model_family=args.model_family,
        capabilities=args.capability,
        max_concurrency=args.max_concurrency,
        active=not args.inactive,
    )
    _emit(record)


def _cmd_agent_update(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).update_agent(
            actor=args.actor,
            agent_id=args.agent_id,
            controller_id=args.controller_id,
            provider=args.provider,
            model_family=args.model_family,
            capabilities=args.capability,
            max_concurrency=args.max_concurrency,
            active=not args.inactive,
        )
    )


def _cmd_agent_delivery(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).configure_agent_delivery(
            actor=args.actor,
            agent_id=args.agent_id,
            mode=args.mode,
            command=_parse_command(args.command_json),
            prompt_stdin=args.prompt_stdin,
        )
    )


def _cmd_agent_list(args: argparse.Namespace) -> None:
    _emit(_workspace(args.path).list_agents())


def _cmd_task_add(args: argparse.Namespace) -> None:
    workspace = _workspace(args.path)
    permissions = {
        "gpu": args.allow_gpu,
        "performance_metrics": args.allow_performance_metrics,
        "network": args.allow_network,
        "outcome_data": args.allow_outcome_data,
    }
    gates = {
        "require_validation": not args.no_validation,
        "allow_skips": args.allow_skips,
        "require_known_answer_check": not args.no_known_answer_check,
        "require_independent_verification": not args.no_independent_verification,
    }
    task = workspace.create_task(
        actor=args.actor,
        task_id=args.task_id,
        title=args.title,
        description=_read_description(args),
        owner=args.owner,
        prerequisites=args.requires,
        allowed_write_roots=args.allow_write,
        permissions=permissions,
        gates=gates,
        task_type=args.task_type,
        risk_tier=args.risk_tier,
        required_capabilities=args.requires_capability,
        resource_locks=args.resource_lock,
        verification_policy={
            "required_attestations": args.required_attestations,
            "allowed_verifiers": args.verifier,
            "independence_dimensions": args.independence_dimension or ["actor"],
        },
        delivery_policy={
            "allow_proxy": args.allow_proxy_delivery,
            "git_remote_name": (
                args.proxy_remote_name
                or ("origin" if args.allow_proxy_delivery else None)
            ),
            "git_remote_url": args.proxy_remote_url,
            "git_ref": args.proxy_ref,
            "required_repo_paths": args.proxy_repo_path,
        },
        idempotency_key=args.idempotency_key,
    )
    _emit(task)


def _cmd_task_list(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).list_tasks(
            state=args.state,
            owner=args.owner,
        )
    )


def _cmd_task_show(args: argparse.Namespace) -> None:
    _emit(_workspace(args.path).get_task(args.task_id))


def _cmd_task_claim(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).claim(
            actor=args.actor,
            task_id=args.task_id,
            lease_seconds=args.lease_seconds,
        )
    )


def _cmd_task_start(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).start(
            actor=args.actor,
            task_id=args.task_id,
            lease_token=args.lease_token,
        )
    )


def _cmd_task_heartbeat(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).heartbeat(
            actor=args.actor,
            task_id=args.task_id,
            lease_token=args.lease_token,
        )
    )


def _cmd_task_block(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).block(
            actor=args.actor,
            task_id=args.task_id,
            lease_token=args.lease_token,
            reason=args.reason,
        )
    )


def _cmd_task_revoke(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).revoke_lease(
            actor=args.actor,
            task_id=args.task_id,
            reason=args.reason,
        )
    )


def _cmd_task_confirm_revocation(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).confirm_revocation(
            actor=args.actor,
            task_id=args.task_id,
            termination_evidence=args.termination_evidence,
        )
    )


def _cmd_task_submit(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).submit(
            actor=args.actor,
            task_id=args.task_id,
            lease_token=args.lease_token,
            report_path=args.report,
            manifest_path=args.evidence,
        )
    )


def _cmd_task_proxy_submit(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).proxy_submit(
            actor=args.actor,
            task_id=args.task_id,
            author=args.author,
            report_path=args.report,
            manifest_path=args.evidence,
            source_repo=args.source_repo,
            source_commit=args.source_commit,
            source_files=_parse_json_array(
                args.source_files_json,
                option="--source-files-json",
            ),
        )
    )


def _cmd_task_attest(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).attest(
            actor=args.actor,
            task_id=args.task_id,
            decision=args.decision,
            note=args.note,
            verification_manifest=args.evidence,
        )
    )


def _cmd_task_verify(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).verify(
            actor=args.actor,
            task_id=args.task_id,
            decision=args.decision,
            note=args.note,
            verification_manifest=args.evidence,
        )
    )


def _cmd_transfer_orchestrator(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).transfer_orchestrator(
            actor=args.actor,
            target=args.target,
            reason=args.reason,
        )
    )


def _cmd_workspace_fingerprint(args: argparse.Namespace) -> None:
    _emit(workspace_fingerprint(_workspace(args.path)))


def _cmd_audit_independence(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).audit_independence(
            dimensions=args.dimension,
        )
    )


def _cmd_task_requeue(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).requeue(
            actor=args.actor,
            task_id=args.task_id,
            reason=args.reason,
        )
    )


def _cmd_task_invalidate(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).invalidate(
            actor=args.actor,
            task_id=args.task_id,
            reason=args.reason,
        )
    )


def _cmd_task_archive(args: argparse.Namespace) -> None:
    _emit(
        _workspace(args.path).archive(
            actor=args.actor,
            task_id=args.task_id,
        )
    )


def _cmd_recover(args: argparse.Namespace) -> None:
    _emit(_workspace(args.path).recover_expired(actor=args.actor))


def _cmd_ledger_verify(args: argparse.Namespace) -> None:
    _emit(_workspace(args.path).ledger.verify())


def _cmd_projection_audit(args: argparse.Namespace) -> None:
    _emit(_workspace(args.path).audit_projections(repair=False))


def _cmd_projection_repair(args: argparse.Namespace) -> None:
    _emit(_workspace(args.path).repair_projections(actor=args.actor))


def _cmd_doctor(args: argparse.Namespace) -> None:
    _emit(
        audit_workspace(
            args.path,
            legacy_root=args.legacy_root,
            legacy_agent=args.legacy_agent,
            legacy_write_test=args.legacy_write_test,
        )
    )


def _cmd_legacy_audit(args: argparse.Namespace) -> None:
    _emit(
        audit_legacy_workspace(
            args.path,
            agent_id=args.agent,
            write_test=args.write_test,
        )
    )


def _cmd_evidence_check(args: argparse.Namespace) -> None:
    workspace = _workspace(args.path)
    task = workspace.get_task(args.task_id)
    _emit(
        validate_submission(
            Path(args.report).resolve(),
            Path(args.evidence).resolve(),
            permissions=task["permissions"],
            gates=task["gates"],
        )
    )


def _cmd_worker_once(args: argparse.Namespace) -> None:
    _emit(
        run_once(
            _workspace(args.path),
            agent_id=args.agent,
            task_id=args.task_id,
            timeout_seconds=args.timeout_seconds,
        )
    )


def _cmd_worker_loop(args: argparse.Namespace) -> None:
    _emit(
        run_loop(
            _workspace(args.path),
            agent_id=args.agent,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
            max_tasks=args.max_tasks,
            idle_timeout_seconds=args.idle_timeout_seconds,
        )
    )


def _cmd_serve(args: argparse.Namespace) -> None:
    print(f"Dashboard: http://{args.host}:{args.port}", file=sys.stderr)
    serve(
        args.path,
        host=args.host,
        port=args.port,
        allow_remote=args.allow_remote,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the complete CLI parser."""

    parser = argparse.ArgumentParser(
        prog="efo",
        description="Evidence-gated orchestration for multiple coding agents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Initialize a broker workspace")
    init.add_argument("path")
    init.add_argument("--name", required=True)
    init.add_argument("--orchestrator", default="antigravity")
    init.add_argument(
        "--preset",
        choices=["antigravity-codex-claude", "meta-4-agent"],
    )
    init.set_defaults(handler=_cmd_init)

    status = subparsers.add_parser("status", help="Show workspace and task status")
    status.add_argument("path")
    status.set_defaults(handler=_cmd_status)

    workspace_command = subparsers.add_parser(
        "workspace",
        help="Manage signed workspace governance",
    )
    workspace_sub = workspace_command.add_subparsers(
        dest="workspace_command",
        required=True,
    )
    transfer = workspace_sub.add_parser("transfer-orchestrator")
    transfer.add_argument("path")
    transfer.add_argument("--actor", required=True)
    transfer.add_argument("--to", dest="target", required=True)
    transfer.add_argument("--reason", required=True)
    transfer.set_defaults(handler=_cmd_transfer_orchestrator)
    fingerprint = workspace_sub.add_parser(
        "fingerprint",
        help="Print a read-only workspace, ledger, host, and runtime identity packet",
    )
    fingerprint.add_argument("path")
    fingerprint.set_defaults(handler=_cmd_workspace_fingerprint)

    agent = subparsers.add_parser("agent", help="Manage registered agents")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    agent_add = agent_sub.add_parser("add")
    agent_add.add_argument("path")
    agent_add.add_argument("--actor", required=True)
    agent_add.add_argument("--id", dest="agent_id", required=True)
    agent_add.add_argument("--role", choices=["worker", "verifier"], default="worker")
    agent_add.add_argument("--mode", choices=["manual", "command"], default="manual")
    agent_add.add_argument(
        "--command-json",
        help='Command argv as JSON, for example ["codex","exec","{prompt}"]',
    )
    agent_add.add_argument(
        "--prompt-stdin",
        action="store_true",
        help="Pipe the generated task prompt to the command's standard input",
    )
    agent_add.add_argument("--write-root", action="append", default=[])
    agent_add.add_argument("--controller-id")
    agent_add.add_argument("--provider", default="unknown")
    agent_add.add_argument("--model-family", default="unknown")
    agent_add.add_argument("--capability", action="append", default=[])
    agent_add.add_argument("--max-concurrency", type=int, default=1)
    agent_add.add_argument("--inactive", action="store_true")
    agent_add.set_defaults(handler=_cmd_agent_add)
    agent_update = agent_sub.add_parser("update")
    agent_update.add_argument("path")
    agent_update.add_argument("--actor", required=True)
    agent_update.add_argument("--id", dest="agent_id", required=True)
    agent_update.add_argument("--controller-id", required=True)
    agent_update.add_argument("--provider", required=True)
    agent_update.add_argument("--model-family", required=True)
    agent_update.add_argument("--capability", action="append", default=[])
    agent_update.add_argument("--max-concurrency", type=int, default=1)
    agent_update.add_argument("--inactive", action="store_true")
    agent_update.set_defaults(handler=_cmd_agent_update)

    agent_delivery = agent_sub.add_parser(
        "delivery",
        help="Configure signed manual or command delivery for an existing agent",
    )
    agent_delivery.add_argument("path")
    agent_delivery.add_argument("--actor", required=True)
    agent_delivery.add_argument("--id", dest="agent_id", required=True)
    agent_delivery.add_argument(
        "--mode",
        choices=["manual", "command"],
        required=True,
    )
    agent_delivery.add_argument("--command-json")
    agent_delivery.add_argument("--prompt-stdin", action="store_true")
    agent_delivery.set_defaults(handler=_cmd_agent_delivery)
    agent_list = agent_sub.add_parser("list")
    agent_list.add_argument("path")
    agent_list.set_defaults(handler=_cmd_agent_list)

    task = subparsers.add_parser("task", help="Manage the task state machine")
    task_sub = task.add_subparsers(dest="task_command", required=True)

    task_add = task_sub.add_parser("add")
    task_add.add_argument("path")
    task_add.add_argument("--actor", required=True)
    task_add.add_argument("--id", dest="task_id", required=True)
    task_add.add_argument("--owner", required=True)
    task_add.add_argument("--title", required=True)
    description_group = task_add.add_mutually_exclusive_group(required=True)
    description_group.add_argument("--description")
    description_group.add_argument("--description-file")
    task_add.add_argument("--requires", action="append", default=[])
    task_add.add_argument("--allow-write", action="append", default=[])
    task_add.add_argument("--idempotency-key")
    task_add.add_argument("--allow-gpu", action="store_true")
    task_add.add_argument("--allow-network", action="store_true")
    task_add.add_argument("--allow-performance-metrics", action="store_true")
    task_add.add_argument("--allow-outcome-data", action="store_true")
    task_add.add_argument("--task-type", default="general")
    task_add.add_argument(
        "--risk-tier",
        choices=["low", "medium", "high", "critical"],
        default="medium",
    )
    task_add.add_argument("--requires-capability", action="append", default=[])
    task_add.add_argument("--resource-lock", action="append", default=[])
    task_add.add_argument("--allow-proxy-delivery", action="store_true")
    task_add.add_argument(
        "--proxy-remote-name",
        help="Preregistered Git remote name (defaults to origin for proxy tasks)",
    )
    task_add.add_argument("--proxy-remote-url")
    task_add.add_argument("--proxy-ref")
    task_add.add_argument("--proxy-repo-path", action="append", default=[])
    task_add.add_argument("--verifier", action="append", default=[])
    task_add.add_argument("--required-attestations", type=int, default=0)
    task_add.add_argument(
        "--independence-dimension",
        action="append",
        choices=["actor", "controller", "model_family"],
        default=None,
    )
    task_add.add_argument("--allow-skips", action="store_true")
    task_add.add_argument("--no-validation", action="store_true")
    task_add.add_argument("--no-known-answer-check", action="store_true")
    task_add.add_argument("--no-independent-verification", action="store_true")
    task_add.set_defaults(handler=_cmd_task_add)

    task_list = task_sub.add_parser("list")
    task_list.add_argument("path")
    task_list.add_argument("--state")
    task_list.add_argument("--owner")
    task_list.set_defaults(handler=_cmd_task_list)

    task_show = task_sub.add_parser("show")
    task_show.add_argument("path")
    task_show.add_argument("--id", dest="task_id", required=True)
    task_show.set_defaults(handler=_cmd_task_show)

    task_claim = task_sub.add_parser("claim")
    task_claim.add_argument("path")
    task_claim.add_argument("--actor", required=True)
    task_claim.add_argument("--id", dest="task_id")
    task_claim.add_argument("--lease-seconds", type=int)
    task_claim.set_defaults(handler=_cmd_task_claim)

    for name, handler in (
        ("start", _cmd_task_start),
        ("heartbeat", _cmd_task_heartbeat),
    ):
        command = task_sub.add_parser(name)
        command.add_argument("path")
        command.add_argument("--actor", required=True)
        command.add_argument("--id", dest="task_id", required=True)
        command.add_argument("--lease-token", required=True)
        command.set_defaults(handler=handler)

    task_block = task_sub.add_parser("block")
    task_block.add_argument("path")
    task_block.add_argument("--actor", required=True)
    task_block.add_argument("--id", dest="task_id", required=True)
    task_block.add_argument("--lease-token", required=True)
    task_block.add_argument("--reason", required=True)
    task_block.set_defaults(handler=_cmd_task_block)

    task_revoke = task_sub.add_parser("revoke")
    task_revoke.add_argument("path")
    task_revoke.add_argument("--actor", required=True)
    task_revoke.add_argument("--id", dest="task_id", required=True)
    task_revoke.add_argument("--reason", required=True)
    task_revoke.set_defaults(handler=_cmd_task_revoke)

    task_confirm_revocation = task_sub.add_parser("confirm-revocation")
    task_confirm_revocation.add_argument("path")
    task_confirm_revocation.add_argument("--actor", required=True)
    task_confirm_revocation.add_argument(
        "--id",
        dest="task_id",
        required=True,
    )
    task_confirm_revocation.add_argument(
        "--termination-evidence",
        required=True,
    )
    task_confirm_revocation.set_defaults(
        handler=_cmd_task_confirm_revocation
    )

    task_submit = task_sub.add_parser("submit")
    task_submit.add_argument("path")
    task_submit.add_argument("--actor", required=True)
    task_submit.add_argument("--id", dest="task_id", required=True)
    task_submit.add_argument("--lease-token", required=True)
    task_submit.add_argument("--report", required=True)
    task_submit.add_argument("--evidence", required=True)
    task_submit.set_defaults(handler=_cmd_task_submit)

    task_proxy_submit = task_sub.add_parser("proxy-submit")
    task_proxy_submit.add_argument("path")
    task_proxy_submit.add_argument("--actor", required=True)
    task_proxy_submit.add_argument("--id", dest="task_id", required=True)
    task_proxy_submit.add_argument("--author", required=True)
    task_proxy_submit.add_argument("--report", required=True)
    task_proxy_submit.add_argument("--evidence", required=True)
    task_proxy_submit.add_argument("--source-repo", required=True)
    task_proxy_submit.add_argument("--source-commit", required=True)
    task_proxy_submit.add_argument(
        "--source-files-json",
        required=True,
        help=(
            "JSON array of {local_path, repo_path} records; bytes are checked "
            "with git cat-file"
        ),
    )
    task_proxy_submit.set_defaults(handler=_cmd_task_proxy_submit)

    task_attest = task_sub.add_parser("attest")
    task_attest.add_argument("path")
    task_attest.add_argument("--actor", required=True)
    task_attest.add_argument("--id", dest="task_id", required=True)
    task_attest.add_argument(
        "--decision",
        choices=["accept", "reject"],
        required=True,
    )
    task_attest.add_argument("--note", required=True)
    task_attest.add_argument("--evidence")
    task_attest.set_defaults(handler=_cmd_task_attest)

    task_verify = task_sub.add_parser("verify")
    task_verify.add_argument("path")
    task_verify.add_argument("--actor", required=True)
    task_verify.add_argument("--id", dest="task_id", required=True)
    task_verify.add_argument("--decision", choices=["accept", "reject"], required=True)
    task_verify.add_argument("--note", required=True)
    task_verify.add_argument("--evidence")
    task_verify.set_defaults(handler=_cmd_task_verify)

    task_requeue = task_sub.add_parser("requeue")
    task_requeue.add_argument("path")
    task_requeue.add_argument("--actor", required=True)
    task_requeue.add_argument("--id", dest="task_id", required=True)
    task_requeue.add_argument("--reason", required=True)
    task_requeue.set_defaults(handler=_cmd_task_requeue)

    task_invalidate = task_sub.add_parser("invalidate")
    task_invalidate.add_argument("path")
    task_invalidate.add_argument("--actor", required=True)
    task_invalidate.add_argument("--id", dest="task_id", required=True)
    task_invalidate.add_argument("--reason", required=True)
    task_invalidate.set_defaults(handler=_cmd_task_invalidate)

    task_archive = task_sub.add_parser("archive")
    task_archive.add_argument("path")
    task_archive.add_argument("--actor", required=True)
    task_archive.add_argument("--id", dest="task_id", required=True)
    task_archive.set_defaults(handler=_cmd_task_archive)

    recover = subparsers.add_parser("recover", help="Block expired task leases")
    recover.add_argument("path")
    recover.add_argument("--actor", required=True)
    recover.set_defaults(handler=_cmd_recover)

    ledger = subparsers.add_parser("ledger", help="Inspect the signed event ledger")
    ledger_sub = ledger.add_subparsers(dest="ledger_command", required=True)
    ledger_verify = ledger_sub.add_parser("verify")
    ledger_verify.add_argument("path")
    ledger_verify.set_defaults(handler=_cmd_ledger_verify)
    projection_audit = ledger_sub.add_parser("audit-projections")
    projection_audit.add_argument("path")
    projection_audit.set_defaults(handler=_cmd_projection_audit)
    projection_repair = ledger_sub.add_parser("repair-projections")
    projection_repair.add_argument("path")
    projection_repair.add_argument("--actor", required=True)
    projection_repair.set_defaults(handler=_cmd_projection_repair)

    audit = subparsers.add_parser("audit", help="Run read-only policy audits")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    audit_independence = audit_sub.add_parser("independence")
    audit_independence.add_argument("path")
    audit_independence.add_argument(
        "--dimension",
        action="append",
        choices=["actor", "controller", "model_family"],
        default=None,
    )
    audit_independence.set_defaults(handler=_cmd_audit_independence)

    doctor = subparsers.add_parser("doctor", help="Audit a broker workspace")
    doctor.add_argument("path")
    doctor.add_argument("--legacy-root")
    doctor.add_argument("--legacy-agent")
    doctor.add_argument("--legacy-write-test", action="store_true")
    doctor.set_defaults(handler=_cmd_doctor)

    legacy = subparsers.add_parser("legacy", help="Audit a Markdown-only workspace")
    legacy_sub = legacy.add_subparsers(dest="legacy_command", required=True)
    legacy_audit = legacy_sub.add_parser("audit")
    legacy_audit.add_argument("path")
    legacy_audit.add_argument("--agent")
    legacy_audit.add_argument("--write-test", action="store_true")
    legacy_audit.set_defaults(handler=_cmd_legacy_audit)

    evidence = subparsers.add_parser("evidence", help="Validate a submission bundle")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_check = evidence_sub.add_parser("check")
    evidence_check.add_argument("path")
    evidence_check.add_argument("--id", dest="task_id", required=True)
    evidence_check.add_argument("--report", required=True)
    evidence_check.add_argument("--evidence", required=True)
    evidence_check.set_defaults(handler=_cmd_evidence_check)

    worker = subparsers.add_parser("worker", help="Run configured agent adapters")
    worker_sub = worker.add_subparsers(dest="worker_command", required=True)
    worker_once = worker_sub.add_parser("once")
    worker_once.add_argument("path")
    worker_once.add_argument("--agent", required=True)
    worker_once.add_argument("--id", dest="task_id")
    worker_once.add_argument("--timeout-seconds", type=int, default=3600)
    worker_once.set_defaults(handler=_cmd_worker_once)
    worker_loop = worker_sub.add_parser("loop")
    worker_loop.add_argument("path")
    worker_loop.add_argument("--agent", required=True)
    worker_loop.add_argument("--poll-seconds", type=float, default=5.0)
    worker_loop.add_argument("--timeout-seconds", type=int, default=3600)
    worker_loop.add_argument("--max-tasks", type=int)
    worker_loop.add_argument("--idle-timeout-seconds", type=float)
    worker_loop.set_defaults(handler=_cmd_worker_loop)

    dashboard = subparsers.add_parser("serve", help="Serve the read-only dashboard")
    dashboard.add_argument("path")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--allow-remote", action="store_true")
    dashboard.set_defaults(handler=_cmd_serve)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and translate domain errors into concise messages."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except (EFOError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
