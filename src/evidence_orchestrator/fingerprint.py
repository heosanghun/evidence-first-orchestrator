"""Read-only runtime and workspace identity fingerprints."""

from __future__ import annotations

import getpass
import platform
import socket
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from . import __version__
from .errors import IntegrityError
from .util import sha256_file, utc_now
from .workspace import Workspace


def _path_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    stat = resolved.stat()
    return {
        "path": str(resolved),
        "device": stat.st_dev,
        "inode": stat.st_ino,
        "size_bytes": stat.st_size,
    }


def workspace_fingerprint(workspace: Workspace) -> dict[str, Any]:
    """Return a read-only identity packet for one workspace and EFO runtime."""

    ledger_sha256 = sha256_file(workspace.ledger.path)
    ledger_verification = workspace.ledger.verify()
    agents = workspace.list_agents()
    tasks = workspace.list_tasks()
    ending_ledger_sha256 = sha256_file(workspace.ledger.path)
    ending_verification = workspace.ledger.verify()
    if (
        ending_ledger_sha256 != ledger_sha256
        or ending_verification != ledger_verification
    ):
        raise IntegrityError(
            "Ledger changed while the workspace fingerprint was collected; retry"
        )

    invocation = Path(sys.argv[0])
    invocation_path = (
        str(invocation.resolve()) if invocation.exists() else str(invocation)
    )
    task_states = Counter(str(task.get("state", "unknown")) for task in tasks)
    return {
        "captured_at": utc_now(),
        "host": {
            "hostname": socket.gethostname(),
            "user": getpass.getuser(),
            "platform": platform.platform(),
        },
        "runtime": {
            "efo_version": __version__,
            "python_executable": str(Path(sys.executable).resolve()),
            "package_path": str(Path(__file__).resolve().parent),
            "invocation": invocation_path,
        },
        "workspace": {
            "workspace_id": workspace.config["workspace_id"],
            "name": workspace.config["name"],
            "schema_version": workspace.config["schema_version"],
            "orchestrator": workspace.orchestrator,
            "root": _path_identity(workspace.root),
            "config": {
                **_path_identity(workspace.config_path),
                "sha256": sha256_file(workspace.config_path),
            },
            "ledger": {
                **_path_identity(workspace.ledger.path),
                "sha256": ledger_sha256,
                **ledger_verification,
            },
            "agents": {
                "count": len(agents),
                "ids": sorted(str(agent["id"]) for agent in agents),
            },
            "tasks": {
                "count": len(tasks),
                "ids": sorted(str(task["id"]) for task in tasks),
                "states": dict(sorted(task_states.items())),
            },
        },
    }
