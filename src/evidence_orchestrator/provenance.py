"""Byte-exact provenance verification for proxy-delivered Git artifacts."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from .errors import EvidenceError
from .util import utc_now

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
BRANCH_REF_RE = re.compile(
    r"^refs/heads/[A-Za-z0-9](?:[A-Za-z0-9._/-]*[A-Za-z0-9_-])?$"
)


def _valid_branch_ref(value: str) -> bool:
    if not BRANCH_REF_RE.fullmatch(value):
        return False
    branch = value.removeprefix("refs/heads/")
    return (
        ".." not in branch
        and "@{" not in branch
        and "//" not in branch
        and all(
            part
            and not part.startswith(".")
            and not part.endswith(".")
            and not part.endswith(".lock")
            for part in branch.split("/")
        )
    )


def _git(
    repo: Path,
    *args: str,
    binary: bool = False,
    timeout_seconds: int = 30,
) -> str | bytes:
    try:
        completed = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = (
            exc.stderr.decode("utf-8", "replace").strip()
            if isinstance(
                exc,
                (subprocess.CalledProcessError, subprocess.TimeoutExpired),
            )
            and exc.stderr
            else str(exc)
        )
        raise EvidenceError(f"Git provenance check failed: {stderr}") from exc
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", "strict").strip()


def _safe_repo_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not value.strip():
        raise EvidenceError(f"Unsafe Git artifact path: {value!r}")
    return path.as_posix()


def verify_git_delivery(
    *,
    repo_path: str | Path,
    remote_name: str,
    expected_remote_url: str,
    source_ref: str,
    source_commit: str,
    files: list[dict[str, str]],
) -> dict[str, Any]:
    """Bind local delivered files to exact Git blobs without text conversion."""

    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        raise EvidenceError(f"Git source repository does not exist: {repo}")
    if not REMOTE_NAME_RE.fullmatch(remote_name):
        raise EvidenceError(f"Unsafe Git remote name: {remote_name!r}")
    if not _valid_branch_ref(source_ref):
        raise EvidenceError(
            "source_ref must be a full refs/heads/<branch> reference"
        )
    commit = source_commit.lower()
    if not COMMIT_RE.fullmatch(commit):
        raise EvidenceError("source_commit must be a full 40-character Git SHA")
    if not files:
        raise EvidenceError("Proxy delivery must bind at least one Git artifact")

    remote_url = str(_git(repo, "remote", "get-url", remote_name))
    if remote_url != expected_remote_url:
        raise EvidenceError(
            f"Git remote URL mismatch: expected {expected_remote_url!r}, "
            f"observed {remote_url!r}"
        )

    advertised = str(
        _git(
            repo,
            "ls-remote",
            "--refs",
            "--exit-code",
            remote_name,
            source_ref,
        )
    )
    advertised_records: list[list[str]] = []
    for line in advertised.splitlines():
        if not line.strip():
            continue
        fields = line.split(None, 1)
        if len(fields) != 2 or not COMMIT_RE.fullmatch(fields[0].lower()):
            raise EvidenceError("Git remote returned malformed ref data")
        advertised_records.append(fields)
    if len(advertised_records) != 1 or advertised_records[0][1] != source_ref:
        raise EvidenceError(
            f"Remote ref {source_ref!r} did not resolve to one exact record"
        )
    advertised_commit = advertised_records[0][0].lower()
    if advertised_commit != commit:
        raise EvidenceError(
            f"Remote ref {source_ref!r} advertises {advertised_commit}, not {commit}"
        )

    observed_commit = str(_git(repo, "rev-parse", f"{commit}^{{commit}}")).lower()
    if observed_commit != commit:
        raise EvidenceError(
            f"Git commit mismatch: expected {commit}, observed {observed_commit}"
        )

    verified_files: list[dict[str, Any]] = []
    for index, record in enumerate(files):
        if not isinstance(record, dict):
            raise EvidenceError(f"source_files[{index}] must be an object")
        local_value = record.get("local_path")
        repo_value = record.get("repo_path")
        if not isinstance(local_value, str) or not local_value:
            raise EvidenceError(f"source_files[{index}].local_path is required")
        if not isinstance(repo_value, str) or not repo_value:
            raise EvidenceError(f"source_files[{index}].repo_path is required")
        local_path = Path(local_value).resolve()
        if not local_path.is_file():
            raise EvidenceError(f"Delivered artifact does not exist: {local_path}")
        git_path = _safe_repo_path(repo_value)
        blob_spec = f"{commit}:{git_path}"
        blob_bytes = _git(repo, "cat-file", "blob", blob_spec, binary=True)
        if not isinstance(blob_bytes, bytes):
            raise EvidenceError("Git returned a non-binary blob unexpectedly")
        delivered_bytes = local_path.read_bytes()
        blob_sha256 = hashlib.sha256(blob_bytes).hexdigest()
        delivered_sha256 = hashlib.sha256(delivered_bytes).hexdigest()
        if delivered_sha256 != blob_sha256:
            raise EvidenceError(
                "Delivered artifact bytes differ from the Git blob for "
                f"{git_path}: expected {blob_sha256}, observed {delivered_sha256}"
            )
        blob_oid = str(_git(repo, "rev-parse", blob_spec))
        verified_files.append(
            {
                "local_path": str(local_path),
                "repo_path": git_path,
                "git_blob": blob_oid,
                "sha256": delivered_sha256,
                "size_bytes": len(delivered_bytes),
            }
        )

    return {
        "transport": "git",
        "repo_path": str(repo),
        "remote_name": remote_name,
        "remote_url": remote_url,
        "source_ref": source_ref,
        "source_commit": commit,
        "remote_observation": {
            "method": "git-ls-remote",
            "observed_at": utc_now(),
            "advertised_ref": source_ref,
            "advertised_commit": advertised_commit,
        },
        "files": verified_files,
    }
