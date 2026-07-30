"""Agent identity profiles and verifier-independence checks."""

from __future__ import annotations

import re
from typing import Any

from .errors import ConfigurationError

IDENTITY_VALUE_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,79}$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9._:-]{0,79}$")
INDEPENDENCE_DIMENSIONS = {"actor", "controller", "model_family"}
UNKNOWN_IDENTITY_VALUES = {"", "unknown", "unspecified"}


def validate_identity_value(value: str, *, field: str) -> str:
    """Validate a stable, lower-case identity profile value."""

    normalized = value.strip().lower()
    if not IDENTITY_VALUE_RE.fullmatch(normalized):
        raise ConfigurationError(
            f"{field} must be a lower-case identity slug containing only "
            "letters, numbers, dot, underscore, slash, or hyphen"
        )
    return normalized


def validate_capabilities(values: list[str] | None) -> list[str]:
    """Return unique, sorted capability slugs."""

    result: set[str] = set()
    for value in values or []:
        normalized = value.strip().lower()
        if not CAPABILITY_RE.fullmatch(normalized):
            raise ConfigurationError(f"Invalid capability: {value!r}")
        result.add(normalized)
    return sorted(result)


def validate_independence_dimensions(values: list[str] | None) -> list[str]:
    """Validate verifier-independence dimensions."""

    dimensions = values or ["actor"]
    unknown = sorted(set(dimensions) - INDEPENDENCE_DIMENSIONS)
    if unknown:
        raise ConfigurationError(
            "Unknown independence dimensions: " + ", ".join(unknown)
        )
    return list(dict.fromkeys(dimensions))


def profile_snapshot(agent: dict[str, Any]) -> dict[str, Any]:
    """Return identity fields that must be frozen into verification records."""

    identity = agent.get("identity")
    if not isinstance(identity, dict):
        identity = {}
    return {
        "id": agent["id"],
        "role": agent.get("role"),
        "controller_id": identity.get("controller_id"),
        "provider": identity.get("provider"),
        "model_family": identity.get("model_family"),
        "capabilities": sorted(agent.get("capabilities", [])),
        "active": agent.get("active", True),
    }


def _known(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.strip().lower() not in UNKNOWN_IDENTITY_VALUES
    )


def evaluate_independence(
    *,
    author: dict[str, Any],
    verifier: dict[str, Any],
    dimensions: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate whether a verifier is independent from a work author.

    Unknown values fail closed for every requested dimension except ``actor``.
    The returned detail is suitable for a signed ledger snapshot.
    """

    required = validate_independence_dimensions(dimensions)
    checks: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []

    for dimension in required:
        if dimension == "actor":
            left = author.get("id")
            right = verifier.get("id")
        else:
            key = "controller_id" if dimension == "controller" else dimension
            left = author.get(key)
            right = verifier.get(key)

        if dimension != "actor" and (not _known(left) or not _known(right)):
            passed = False
            reason = f"{dimension} is not declared for both actors"
        elif left == right:
            passed = False
            reason = f"{dimension} matches ({left})"
        else:
            passed = True
            reason = f"{dimension} differs"

        checks[dimension] = {
            "author": left,
            "verifier": right,
            "passed": passed,
        }
        if not passed:
            reasons.append(reason)

    return {
        "independent": not reasons,
        "dimensions": required,
        "checks": checks,
        "reasons": reasons,
    }
