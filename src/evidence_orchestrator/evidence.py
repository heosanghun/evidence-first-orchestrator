"""Validation for worker reports and machine-readable evidence manifests."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from .errors import EvidenceError
from .util import read_json, sha256_file

SECTION_RE = re.compile(r"^##\s+([1-6])(?:[.)]|\s)", re.MULTILINE)
REQUIRED_SECTION_NUMBERS = {"1", "2", "3", "4", "5", "6"}
CLAIM_KINDS = {"functional", "performance", "resource", "provenance"}


def validate_report(path: Path) -> dict[str, Any]:
    """Check that a Markdown report contains the six protocol sections."""

    if not path.is_file():
        raise EvidenceError(f"Report does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    ordered_sections = [match.group(1) for match in matches]
    sections = set(ordered_sections)
    missing = sorted(REQUIRED_SECTION_NUMBERS - sections)
    if missing:
        raise EvidenceError(
            f"Report is missing required numbered sections: {', '.join(missing)}"
        )
    if ordered_sections != ["1", "2", "3", "4", "5", "6"]:
        raise EvidenceError(
            "Report sections must appear exactly once in the order 1 through 6"
        )
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if not body:
            raise EvidenceError(f"Report section {match.group(1)} is empty")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "sections": ordered_sections,
        "contains_fill_marker": "[FILL]" in text,
    }


def _resolve_evidence_path(value: str, manifest_path: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def _require_int(record: dict[str, Any], name: str, context: str) -> int:
    value = record.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise EvidenceError(f"{context}.{name} must be an integer")
    return value


def _reject_non_finite(value: Any, context: str = "manifest") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise EvidenceError(f"{context} contains a non-finite number")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_non_finite(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_non_finite(child, f"{context}[{index}]")


def validate_manifest(
    manifest_path: Path,
    *,
    permissions: dict[str, bool],
    gates: dict[str, Any],
) -> dict[str, Any]:
    """Validate a reproducibility manifest against preregistered task gates."""

    if not manifest_path.is_file():
        raise EvidenceError(f"Evidence manifest does not exist: {manifest_path}")
    manifest = read_json(manifest_path)
    _reject_non_finite(manifest)
    if manifest.get("schema_version") != 1:
        raise EvidenceError("Evidence manifest schema_version must be 1")

    artifacts = manifest.get("artifacts", [])
    validations = manifest.get("validations", [])
    known_checks = manifest.get("known_answer_checks", [])
    claims = manifest.get("claims", [])
    for name, value in (
        ("artifacts", artifacts),
        ("validations", validations),
        ("known_answer_checks", known_checks),
        ("claims", claims),
    ):
        if not isinstance(value, list):
            raise EvidenceError(f"Evidence manifest {name} must be a list")

    artifact_results: list[dict[str, Any]] = []
    for index, artifact in enumerate(artifacts):
        context = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise EvidenceError(f"{context} must be an object")
        value = artifact.get("path")
        expected_sha = artifact.get("sha256")
        if not isinstance(value, str) or not value:
            raise EvidenceError(f"{context}.path must be a non-empty string")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise EvidenceError(f"{context}.sha256 must be a full SHA-256")
        path = _resolve_evidence_path(value, manifest_path)
        if not path.is_file():
            raise EvidenceError(f"Evidence artifact does not exist: {path}")
        actual_sha = sha256_file(path)
        if actual_sha != expected_sha.lower():
            raise EvidenceError(
                f"Evidence artifact SHA mismatch for {path}: "
                f"expected {expected_sha}, observed {actual_sha}"
            )
        artifact_results.append({"path": str(path), "sha256": actual_sha})

    if gates.get("require_validation", True) and not validations:
        raise EvidenceError("At least one validation command is required")
    validation_results: list[dict[str, Any]] = []
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    for index, validation in enumerate(validations):
        context = f"validations[{index}]"
        if not isinstance(validation, dict):
            raise EvidenceError(f"{context} must be an object")
        command = validation.get("command")
        if not isinstance(command, str) or not command.strip():
            raise EvidenceError(f"{context}.command must be a non-empty string")
        exit_code = _require_int(validation, "exit_code", context)
        passed = _require_int(validation, "passed", context)
        failed = _require_int(validation, "failed", context)
        skipped = _require_int(validation, "skipped", context)
        if min(passed, failed, skipped) < 0:
            raise EvidenceError(f"{context} counts cannot be negative")
        if exit_code != 0 or failed:
            raise EvidenceError(
                f"{context} did not pass: exit_code={exit_code}, failed={failed}"
            )
        skip_reasons = validation.get("skip_reasons", [])
        if not isinstance(skip_reasons, list):
            raise EvidenceError(f"{context}.skip_reasons must be a list")
        if skipped and len(skip_reasons) < skipped:
            raise EvidenceError(
                f"{context} has {skipped} skipped checks but lacks a reason for each"
            )
        if skipped and not gates.get("allow_skips", False):
            raise EvidenceError(
                f"{context} has {skipped} skipped checks; skip is not pass"
            )
        raw_output = validation.get("raw_output_path")
        raw_output_sha = validation.get("raw_output_sha256")
        raw_output_result = None
        if raw_output is not None:
            if not isinstance(raw_output, str) or not raw_output:
                raise EvidenceError(f"{context}.raw_output_path must be a string")
            output_path = _resolve_evidence_path(raw_output, manifest_path)
            if not output_path.is_file():
                raise EvidenceError(f"Raw validation output is missing: {output_path}")
            observed_output_sha = sha256_file(output_path)
            if raw_output_sha != observed_output_sha:
                raise EvidenceError(
                    f"Raw validation output SHA mismatch for {output_path}"
                )
            raw_output_result = {
                "path": str(output_path),
                "sha256": observed_output_sha,
            }
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        validation_results.append(
            {
                "command": command,
                "exit_code": exit_code,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "raw_output": raw_output_result,
            }
        )

    if gates.get("require_known_answer_check", True) and not known_checks:
        raise EvidenceError("At least one known-answer comparison is required")
    for index, check in enumerate(known_checks):
        context = f"known_answer_checks[{index}]"
        if not isinstance(check, dict):
            raise EvidenceError(f"{context} must be an object")
        if check.get("passed") is not True:
            raise EvidenceError(f"{context} is not explicitly passed")
        if "expected" not in check or "observed" not in check:
            raise EvidenceError(f"{context} must record expected and observed values")
        if check["expected"] != check["observed"]:
            raise EvidenceError(f"{context} expected and observed values differ")

    unmeasured = 0
    measured_performance = 0
    if not claims:
        raise EvidenceError("Evidence manifest must declare at least one claim")
    valid_evidence_refs = {
        str(artifact.get("path"))
        for artifact in artifacts
        if isinstance(artifact, dict)
    }
    valid_evidence_refs.update(
        str(validation.get("raw_output_path"))
        for validation in validations
        if isinstance(validation, dict) and validation.get("raw_output_path")
    )
    for index, claim in enumerate(claims):
        context = f"claims[{index}]"
        if not isinstance(claim, dict):
            raise EvidenceError(f"{context} must be an object")
        kind = claim.get("kind")
        if kind not in CLAIM_KINDS:
            raise EvidenceError(
                f"{context}.kind must be one of {', '.join(sorted(CLAIM_KINDS))}"
            )
        if not isinstance(claim.get("name"), str) or not claim["name"].strip():
            raise EvidenceError(f"{context}.name must be a non-empty string")
        measured = claim.get("measured")
        if not isinstance(measured, bool):
            raise EvidenceError(f"{context}.measured must be true or false")
        if not measured:
            unmeasured += 1
            if claim.get("value") != "[FILL]":
                raise EvidenceError(
                    f"{context} is unmeasured and must use the exact value [FILL]"
                )
        else:
            evidence = claim.get("evidence", [])
            if not isinstance(evidence, list) or not evidence:
                raise EvidenceError(f"{context} is measured but has no evidence")
            if claim.get("value") is None or claim.get("value") == "[FILL]":
                raise EvidenceError(f"{context} is measured but has no measured value")
            unknown_evidence = [
                reference
                for reference in evidence
                if not isinstance(reference, str)
                or reference not in valid_evidence_refs
            ]
            if unknown_evidence:
                raise EvidenceError(
                    f"{context} references evidence not bound in artifacts or raw output: "
                    f"{unknown_evidence}"
                )
            if kind == "performance":
                measured_performance += 1

    if measured_performance and not permissions.get("performance_metrics", False):
        raise EvidenceError(
            "Measured performance claims are forbidden by this task's permissions"
        )

    return {
        "path": str(manifest_path.resolve()),
        "sha256": sha256_file(manifest_path),
        "artifacts": artifact_results,
        "validation_commands": len(validation_results),
        "validations": validation_results,
        "passed": total_passed,
        "failed": total_failed,
        "skipped": total_skipped,
        "known_answer_checks": len(known_checks),
        "claims": len(claims),
        "unmeasured_claims": unmeasured,
        "measured_performance_claims": measured_performance,
    }


def validate_submission(
    report_path: Path,
    manifest_path: Path,
    *,
    permissions: dict[str, bool],
    gates: dict[str, Any],
) -> dict[str, Any]:
    """Validate both the human report and its evidence manifest."""

    report = validate_report(report_path)
    manifest = validate_manifest(
        manifest_path,
        permissions=permissions,
        gates=gates,
    )
    if manifest["unmeasured_claims"] and not report["contains_fill_marker"]:
        raise EvidenceError(
            "The manifest declares unmeasured claims but the report has no [FILL] marker"
        )
    return {"report": report, "manifest": manifest}
