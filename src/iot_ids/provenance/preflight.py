"""Fail-closed coordination for prospective experiment preflight.

This module has no production authorization provider and deliberately refuses
real-data authorization. A returned synthetic-ready status is meaningful only
within the synthetic test/demo boundary and does not authorize repository
datasets, adapters, models, or experiment runners.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Protocol, TypeVar

from iot_ids.provenance.artifact_integrity import (
    ArtifactIntegrityError,
    ArtifactIntegrityResult,
    verify_artifact_digest,
)
from iot_ids.provenance.manifest_validation import (
    ManifestValidationError,
    ManifestValidatorUnavailable,
    validate_manifest,
)


class AuthorizationStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    INDETERMINATE = "INDETERMINATE"
    MISSING = "MISSING"
    MALFORMED = "MALFORMED"
    NOT_CHECKED = "NOT_CHECKED"


class AuthorizationScope(str, Enum):
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"
    REAL_DATA = "REAL_DATA"


class PreflightStatus(str, Enum):
    READY_SYNTHETIC = "READY_SYNTHETIC"
    BLOCKED = "BLOCKED"


class SchemaStatus(str, Enum):
    NOT_CHECKED = "NOT_CHECKED"
    VALID = "SCHEMA_VALID"
    INVALID = "SCHEMA_INVALID"
    UNAVAILABLE = "SCHEMA_UNAVAILABLE"


class IntegrityStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    NOT_CHECKED = "NOT_CHECKED"
    VERIFIED = "INTEGRITY_VERIFIED"
    FAILED = "INTEGRITY_FAILED"


class EvidenceStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"


class PreflightReason(str, Enum):
    PREFLIGHT_INPUT_INVALID = "PREFLIGHT_INPUT_INVALID"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    SCHEMA_UNAVAILABLE = "SCHEMA_UNAVAILABLE"
    AUTHORIZATION_MISSING = "AUTHORIZATION_MISSING"
    AUTHORIZATION_MALFORMED = "AUTHORIZATION_MALFORMED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    AUTHORIZATION_INDETERMINATE = "AUTHORIZATION_INDETERMINATE"
    REAL_DATA_AUTHORIZATION_UNAVAILABLE = "REAL_DATA_AUTHORIZATION_UNAVAILABLE"
    REQUIRED_ARTIFACT_EVIDENCE_MISSING = "REQUIRED_ARTIFACT_EVIDENCE_MISSING"
    ARTIFACT_DECLARATION_INVALID = "ARTIFACT_DECLARATION_INVALID"
    ARTIFACT_MISSING = "ARTIFACT_MISSING"
    ARTIFACT_MISMATCH = "ARTIFACT_MISMATCH"
    ARTIFACT_VERIFICATION_FAILED = "ARTIFACT_VERIFICATION_FAILED"


@dataclass(frozen=True)
class AuthorizationDecision:
    """Structured response from the injected policy boundary.

    This record is not a credential or filesystem identity proof. Trust is
    placed in the policy provider that returns it. The coordinator accepts
    only SYNTHETIC_ONLY decisions; real-data authorization is unavailable.
    """

    status: AuthorizationStatus
    scope: AuthorizationScope


class AuthorizationPolicy(Protocol):
    """Trusted boundary responsible for the independent authorization decision."""

    def authorize(self, manifest: dict[str, Any]) -> AuthorizationDecision: ...


@dataclass(frozen=True)
class ArtifactEvidence:
    """Explicit artifact input; paths are never read from manifest fields."""

    relative_path: str
    algorithm: str
    expected_digest: str
    base_dir: str


@dataclass(frozen=True)
class PreflightResult:
    status: PreflightStatus
    schema_status: SchemaStatus
    authorization_status: AuthorizationStatus
    integrity_status: IntegrityStatus
    reason_codes: tuple[PreflightReason, ...]
    artifact_results: tuple[ArtifactIntegrityResult, ...] = ()
    evidence_status: EvidenceStatus = EvidenceStatus.UNVERIFIED


class PreflightOperationBlocked(RuntimeError):
    """A requested operation was not called because preflight blocked it."""

    def __init__(self, result: PreflightResult):
        self.result = result
        reason_codes = ",".join(reason.value for reason in result.reason_codes)
        super().__init__(f"preflight blocked operation ({reason_codes or 'unknown_reason'})")


_OperationResult = TypeVar("_OperationResult")


def execute_after_preflight(
    operation: Callable[[], _OperationResult],
    manifest: Any,
    *,
    authorization_policy: AuthorizationPolicy | None,
    artifact_evidence: tuple[ArtifactEvidence, ...] = (),
    require_artifacts: bool = False,
) -> tuple[PreflightResult, _OperationResult]:
    """Run an explicitly supplied synthetic operation only after preflight.

    This is an execution-order helper for synthetic/prospective workflows; it
    cannot authorize real data because ``evaluate_preflight`` only returns a
    ready status for ``SYNTHETIC_ONLY``. A blocked result raises before the
    callback is invoked. Callback exceptions propagate and are never converted
    into successful results.
    """
    if not callable(operation):
        raise TypeError("preflight operation must be callable")
    result = evaluate_preflight(
        manifest,
        authorization_policy=authorization_policy,
        artifact_evidence=artifact_evidence,
        require_artifacts=require_artifacts,
    )
    if result.status is not PreflightStatus.READY_SYNTHETIC:
        raise PreflightOperationBlocked(result)
    return result, operation()


def evaluate_preflight(
    manifest: Any,
    *,
    authorization_policy: AuthorizationPolicy | None,
    artifact_evidence: tuple[ArtifactEvidence, ...] = (),
    require_artifacts: bool = False,
) -> PreflightResult:
    """Evaluate manifest, synthetic-only authorization, then explicit artifacts.

    The function performs no operation itself. Caller-supplied artifact paths
    are explicit inputs and are considered only after schema and authorization
    succeed. A schema field cannot authorize its own use.
    """
    if type(require_artifacts) is not bool or not isinstance(artifact_evidence, tuple):
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.NOT_CHECKED,
            AuthorizationStatus.NOT_CHECKED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.PREFLIGHT_INPUT_INVALID,),
        )
    if any(not isinstance(item, ArtifactEvidence) for item in artifact_evidence):
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.NOT_CHECKED,
            AuthorizationStatus.NOT_CHECKED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.PREFLIGHT_INPUT_INVALID,),
        )
    try:
        validate_manifest(manifest)
    except ManifestValidatorUnavailable:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.UNAVAILABLE,
            AuthorizationStatus.NOT_CHECKED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.SCHEMA_UNAVAILABLE,),
        )
    except ManifestValidationError:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.INVALID,
            AuthorizationStatus.NOT_CHECKED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.SCHEMA_INVALID,),
        )

    if authorization_policy is None:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.MISSING,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.AUTHORIZATION_MISSING,),
        )
    if not callable(getattr(authorization_policy, "authorize", None)):
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.MALFORMED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.AUTHORIZATION_MALFORMED,),
        )
    try:
        decision = authorization_policy.authorize(manifest)
    except Exception:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.INDETERMINATE,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.AUTHORIZATION_INDETERMINATE,),
        )
    if (
        not isinstance(decision, AuthorizationDecision)
        or not isinstance(decision.status, AuthorizationStatus)
        or not isinstance(decision.scope, AuthorizationScope)
    ):
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.MALFORMED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.AUTHORIZATION_MALFORMED,),
        )
    if decision.status is AuthorizationStatus.DENIED:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.DENIED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.AUTHORIZATION_DENIED,),
        )
    if decision.status is AuthorizationStatus.INDETERMINATE:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.INDETERMINATE,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.AUTHORIZATION_INDETERMINATE,),
        )
    if decision.scope is not AuthorizationScope.SYNTHETIC_ONLY:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.DENIED,
            IntegrityStatus.NOT_CHECKED,
            (PreflightReason.REAL_DATA_AUTHORIZATION_UNAVAILABLE,),
        )

    if require_artifacts and not artifact_evidence:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.AUTHORIZED,
            IntegrityStatus.FAILED,
            (PreflightReason.REQUIRED_ARTIFACT_EVIDENCE_MISSING,),
        )
    if not artifact_evidence:
        return PreflightResult(
            PreflightStatus.READY_SYNTHETIC,
            SchemaStatus.VALID,
            AuthorizationStatus.AUTHORIZED,
            IntegrityStatus.NOT_REQUIRED,
            (),
        )

    results: list[ArtifactIntegrityResult] = []
    reasons: list[PreflightReason] = []
    for evidence in artifact_evidence:
        try:
            result = verify_artifact_digest(
                evidence.relative_path,
                algorithm=evidence.algorithm,
                expected_digest=evidence.expected_digest,
                base_dir=evidence.base_dir,
            )
        except ArtifactIntegrityError:
            reasons.append(PreflightReason.ARTIFACT_DECLARATION_INVALID)
            continue
        except Exception:
            reasons.append(PreflightReason.ARTIFACT_VERIFICATION_FAILED)
            continue
        results.append(result)
        if result.status == "MISSING":
            reasons.append(PreflightReason.ARTIFACT_MISSING)
        elif result.status == "MISMATCH":
            reasons.append(PreflightReason.ARTIFACT_MISMATCH)

    if reasons:
        return PreflightResult(
            PreflightStatus.BLOCKED,
            SchemaStatus.VALID,
            AuthorizationStatus.AUTHORIZED,
            IntegrityStatus.FAILED,
            tuple(dict.fromkeys(reasons)),
            tuple(results),
        )
    return PreflightResult(
        PreflightStatus.READY_SYNTHETIC,
        SchemaStatus.VALID,
        AuthorizationStatus.AUTHORIZED,
        IntegrityStatus.VERIFIED,
        (),
        tuple(results),
    )
