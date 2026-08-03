"""Offline Git provenance checks for transparent proxy submissions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from .errors import AuthorizationError, ConfigurationError, EvidenceError
from .util import is_relative_to, sha256_file, validate_agent_id

COMMIT_RE = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
REMOTE_NAME_RE = re.compile(r"[A-Za-z0-9._-]+")


def _run_git(
    repository: Path,
    arguments: list[str],
    *,
    binary: bool = False,
) -> str | bytes:
    environment = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={repository}",
            "-C",
            str(repository),
            *arguments,
        ],
        check=False,
        capture_output=True,
        env=environment,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", "replace").strip()
        raise EvidenceError(
            f"Git provenance command failed ({' '.join(arguments)}): {error}"
        )
    if binary:
        return completed.stdout
    return completed.stdout.decode("utf-8", "strict").strip()


def _validate_remote_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("Git provenance remote_url must be non-empty")
    remote_url = value.strip()
    parsed = urlsplit(remote_url)
    if parsed.scheme in {"http", "https"} and (
        parsed.username is not None or parsed.password is not None
    ):
        raise AuthorizationError(
            "Git provenance remote_url must not contain embedded credentials"
        )
    if "\n" in remote_url or "\r" in remote_url:
        raise ConfigurationError("Git provenance remote_url contains a line break")
    return remote_url


def validate_git_source_claim(remote_url: Any, branch: Any) -> tuple[str, str]:
    """Validate the immutable source constraints stored in a proxy grant."""

    normalized_remote = _validate_remote_url(remote_url)
    if not isinstance(branch, str) or not branch.strip():
        raise ConfigurationError("Git provenance branch must be non-empty")
    normalized_branch = branch.strip()
    if "\n" in normalized_branch or "\r" in normalized_branch:
        raise ConfigurationError("Git provenance branch contains a line break")
    if normalized_branch.startswith("-"):
        raise ConfigurationError("Git provenance branch cannot start with '-'")
    return normalized_remote, normalized_branch


def validate_git_commit(value: Any) -> str:
    """Return a normalized full Git object ID for preregistration."""

    commit = str(value or "").lower()
    if not COMMIT_RE.fullmatch(commit):
        raise ConfigurationError(
            "Git provenance commit must be a full 40- or 64-character object ID"
        )
    return commit


def _validate_source_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigurationError("Git provenance source_path must be non-empty")
    if (
        "\\" in value
        or ":" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ConfigurationError(
            "Git provenance source_path must be a plain POSIX relative path"
        )
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ConfigurationError(
            "Git provenance source_path must not escape the repository"
        )
    return path.as_posix()


def _evidence_file_map(evidence: dict[str, Any]) -> dict[Path, str]:
    files: dict[Path, str] = {}
    for artifact in evidence.get("manifest", {}).get("artifacts", []):
        files[Path(artifact["path"]).resolve()] = artifact["sha256"]
    for validation in evidence.get("manifest", {}).get("validations", []):
        raw_output = validation.get("raw_output")
        if raw_output:
            files[Path(raw_output["path"]).resolve()] = raw_output["sha256"]
    return files


def validate_git_provenance(
    provenance_path: str | Path,
    *,
    source_repository: str | Path,
    report_root: str | Path,
    expected_author: str,
    evidence: dict[str, Any],
    max_blob_bytes: int,
) -> dict[str, Any]:
    """Bind every claim-bearing evidence file to raw bytes in one Git commit."""

    provenance = Path(provenance_path).resolve()
    owned_root = Path(report_root).resolve()
    if not is_relative_to(provenance, owned_root):
        raise AuthorizationError(
            f"Provenance manifest must be under the transport report directory: "
            f"{owned_root}"
        )
    if not provenance.is_file():
        raise EvidenceError(f"Git provenance manifest does not exist: {provenance}")
    try:
        payload = json.loads(provenance.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"Invalid Git provenance JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise EvidenceError("Git provenance schema_version must be 1")
    if payload.get("kind") != "git":
        raise EvidenceError("Git provenance kind must be 'git'")

    author = validate_agent_id(str(payload.get("author", "")))
    if author != validate_agent_id(expected_author):
        raise AuthorizationError(
            f"Git provenance author {author!r} does not match task owner "
            f"{expected_author!r}"
        )
    remote_name = str(payload.get("remote_name", "origin"))
    if not REMOTE_NAME_RE.fullmatch(remote_name):
        raise ConfigurationError("Git provenance remote_name is invalid")
    remote_url, branch = validate_git_source_claim(
        payload.get("remote_url"),
        payload.get("branch"),
    )
    commit = validate_git_commit(payload.get("commit"))
    if not isinstance(max_blob_bytes, int) or max_blob_bytes < 1:
        raise ConfigurationError("max_blob_bytes must be a positive integer")

    repository = Path(source_repository).resolve()
    if not repository.is_dir():
        raise EvidenceError(f"Git source repository does not exist: {repository}")
    actual_remote = str(
        _run_git(repository, ["remote", "get-url", remote_name])
    )
    if actual_remote != remote_url:
        raise EvidenceError(
            f"Git remote mismatch: expected {remote_url!r}, observed "
            f"{actual_remote!r}"
        )
    _run_git(repository, ["check-ref-format", "--branch", branch])
    resolved_commit = str(
        _run_git(repository, ["rev-parse", "--verify", f"{commit}^{{commit}}"])
    ).lower()
    if resolved_commit != commit:
        raise EvidenceError(
            f"Git commit mismatch: expected {commit}, observed {resolved_commit}"
        )

    candidates = [
        f"refs/remotes/{remote_name}/{branch}",
        f"refs/heads/{branch}",
    ]
    resolved_ref = None
    ref_tip = None
    for candidate in candidates:
        try:
            value = str(
                _run_git(repository, ["rev-parse", "--verify", candidate])
            ).lower()
        except EvidenceError:
            continue
        resolved_ref = candidate
        ref_tip = value
        break
    if resolved_ref is None or ref_tip is None:
        raise EvidenceError(
            f"Git provenance branch is not available locally: {branch!r}"
        )
    _run_git(repository, ["merge-base", "--is-ancestor", commit, resolved_ref])

    declared_files = payload.get("files")
    if not isinstance(declared_files, list) or not declared_files:
        raise EvidenceError("Git provenance must declare at least one source file")
    expected_files = _evidence_file_map(evidence)
    if not expected_files:
        raise EvidenceError(
            "Proxy submissions require at least one claim-bearing artifact or "
            "raw validation output"
        )

    verified_files: list[dict[str, Any]] = []
    observed_submitted: set[Path] = set()
    observed_sources: set[str] = set()
    for index, record in enumerate(declared_files):
        context = f"Git provenance files[{index}]"
        if not isinstance(record, dict):
            raise EvidenceError(f"{context} must be an object")
        source_path = _validate_source_path(record.get("source_path"))
        submitted_value = record.get("submitted_path")
        if not isinstance(submitted_value, str) or not submitted_value:
            raise ConfigurationError(f"{context}.submitted_path must be non-empty")
        submitted = (provenance.parent / submitted_value).resolve()
        if not is_relative_to(submitted, owned_root):
            raise AuthorizationError(
                f"{context}.submitted_path escapes the transport report directory"
            )
        if submitted not in expected_files:
            raise EvidenceError(
                f"{context}.submitted_path is not claim-bearing evidence: {submitted}"
            )
        if submitted in observed_submitted:
            raise EvidenceError(f"Duplicate submitted_path in Git provenance: {submitted}")
        if source_path in observed_sources:
            raise EvidenceError(
                f"Duplicate source_path in Git provenance: {source_path}"
            )
        observed_submitted.add(submitted)
        observed_sources.add(source_path)

        size_text = str(
            _run_git(repository, ["cat-file", "-s", f"{commit}:{source_path}"])
        )
        try:
            blob_size = int(size_text)
        except ValueError as exc:
            raise EvidenceError(
                f"Git reported a non-integer blob size for {source_path!r}"
            ) from exc
        if blob_size > max_blob_bytes:
            raise EvidenceError(
                f"Git source blob exceeds the proxy verification limit: "
                f"{source_path} ({blob_size} > {max_blob_bytes})"
            )
        blob = _run_git(
            repository,
            ["cat-file", "blob", f"{commit}:{source_path}"],
            binary=True,
        )
        assert isinstance(blob, bytes)
        tree_record = str(
            _run_git(repository, ["ls-tree", commit, "--", source_path])
        )
        metadata, separator, tree_path = tree_record.partition("\t")
        fields = metadata.split()
        if (
            not separator
            or tree_path != source_path
            or len(fields) != 3
            or fields[1] != "blob"
            or fields[0] not in {"100644", "100755"}
        ):
            raise EvidenceError(
                f"Git provenance source must be a regular file blob: {source_path}"
            )
        if blob.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            raise EvidenceError(
                f"Git LFS pointer is not accepted as evidence content: {source_path}"
            )
        blob_sha = hashlib.sha256(blob).hexdigest()
        submitted_sha = sha256_file(submitted)
        if submitted_sha != expected_files[submitted]:
            raise EvidenceError(
                f"Submitted evidence changed after validation: {submitted}"
            )
        if blob_sha != submitted_sha:
            raise EvidenceError(
                "Git blob bytes differ from submitted evidence; possible newline "
                f"or transport mutation for {source_path!r}: "
                f"blob={blob_sha}, submitted={submitted_sha}"
            )
        blob_oid = str(
            _run_git(repository, ["rev-parse", f"{commit}:{source_path}"])
        ).lower()
        verified_files.append(
            {
                "source_path": source_path,
                "submitted_path": str(submitted),
                "sha256": submitted_sha,
                "blob_oid": blob_oid,
                "mode": fields[0],
                "size_bytes": blob_size,
            }
        )

    if observed_submitted != set(expected_files):
        missing = sorted(str(path) for path in set(expected_files) - observed_submitted)
        raise EvidenceError(
            "Git provenance does not bind every claim-bearing evidence file: "
            + ", ".join(missing)
        )

    return {
        "schema_version": 1,
        "kind": "git",
        "path": str(provenance),
        "sha256": sha256_file(provenance),
        "author": author,
        "repository": str(repository),
        "remote_name": remote_name,
        "remote_url": remote_url,
        "branch": branch,
        "resolved_ref": resolved_ref,
        "ref_tip": ref_tip,
        "commit": commit,
        "files": verified_files,
        "byte_exact": True,
    }
