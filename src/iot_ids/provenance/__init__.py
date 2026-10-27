"""Prospective experiment provenance utilities.

These utilities validate record structure; they do not authorize data access or
verify that recorded provenance is true.
"""

from iot_ids.provenance.manifest_validation import (
    ManifestValidationError,
    ManifestValidatorUnavailable,
    ManifestValidationResult,
    validate_manifest,
    validate_manifest_json,
)
from iot_ids.provenance.artifact_integrity import (
    ArtifactIntegrityError,
    ArtifactIntegrityResult,
    validate_digest_declaration,
    verify_artifact_digest,
)
from iot_ids.provenance.preflight import (
    ArtifactEvidence,
    AuthorizationDecision,
    AuthorizationPolicy,
    AuthorizationScope,
    AuthorizationStatus,
    EvidenceStatus,
    IntegrityStatus,
    PreflightReason,
    PreflightOperationBlocked,
    PreflightResult,
    PreflightStatus,
    SchemaStatus,
    evaluate_preflight,
    execute_after_preflight,
)
from iot_ids.provenance.windows_access import (
    AccessCode,
    LexicalPathResult,
    PolicyConfigurationResult,
    StageStatus,
    WindowsAccessAssessment,
    WindowsAuthorizationProvider,
    RealDataAuthorizationUnavailable,
    require_real_data_authorization,
    lexical_protected_overlap,
    validate_policy_configuration,
    validate_windows_path_lexically,
)
from iot_ids.provenance.windows_handle import (
    HandleObjectIdentity,
    HandlePrimitiveCode,
    WindowsHandlePrimitiveError,
    WindowsReadHandle,
    is_supported_windows_runtime,
    open_child_file_readonly,
)

__all__ = [
    "ManifestValidationError",
    "ManifestValidatorUnavailable",
    "ManifestValidationResult",
    "validate_manifest",
    "validate_manifest_json",
    "ArtifactIntegrityError",
    "ArtifactIntegrityResult",
    "validate_digest_declaration",
    "verify_artifact_digest",
    "ArtifactEvidence",
    "AuthorizationDecision",
    "AuthorizationPolicy",
    "AuthorizationScope",
    "AuthorizationStatus",
    "EvidenceStatus",
    "IntegrityStatus",
    "PreflightReason",
    "PreflightOperationBlocked",
    "PreflightResult",
    "PreflightStatus",
    "SchemaStatus",
    "evaluate_preflight",
    "execute_after_preflight",
    "AccessCode",
    "LexicalPathResult",
    "PolicyConfigurationResult",
    "StageStatus",
    "WindowsAccessAssessment",
    "WindowsAuthorizationProvider",
    "RealDataAuthorizationUnavailable",
    "require_real_data_authorization",
    "lexical_protected_overlap",
    "validate_policy_configuration",
    "validate_windows_path_lexically",
    "HandleObjectIdentity",
    "HandlePrimitiveCode",
    "WindowsHandlePrimitiveError",
    "WindowsReadHandle",
    "is_supported_windows_runtime",
    "open_child_file_readonly",
]
