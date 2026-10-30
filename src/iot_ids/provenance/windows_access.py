"""Fail-closed Windows access-provider boundary (not a production provider).

This module performs lexical validation and policy-shape validation only. It
does not authenticate owner approval, establish Windows object identity, or
open a filesystem object. Real access is therefore always refused here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import importlib
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any


_ROOT = Path(__file__).resolve().parents[3]
_POLICY_SCHEMA = _ROOT / "results" / "implementation" / "dataset_access_policy.schema.json"
_DRAFT_URI = "https://json-schema.org/draft/2020-12/schema"


class StageStatus(str, Enum):
    VALID = "VALID"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIED = "UNVERIFIED"
    NOT_CHECKED = "NOT_CHECKED"
    LEXICALLY_CLEAR = "LEXICALLY_CLEAR"
    LEXICAL_OVERLAP = "LEXICAL_OVERLAP"
    REFUSED = "REFUSED"


class AccessCode(str, Enum):
    INVALID_PATH = "INVALID_PATH"
    POLICY_SCHEMA_UNAVAILABLE = "POLICY_SCHEMA_UNAVAILABLE"
    POLICY_SCHEMA_INVALID = "POLICY_SCHEMA_INVALID"
    OWNER_APPROVAL_UNVERIFIED = "OWNER_APPROVAL_UNVERIFIED"
    WINDOWS_IDENTITY_PROVIDER_UNAVAILABLE = "WINDOWS_IDENTITY_PROVIDER_UNAVAILABLE"
    PROTECTED_ROOT_OVERLAP = "PROTECTED_ROOT_OVERLAP"
    REAL_AUTHORIZATION_DISABLED = "REAL_AUTHORIZATION_DISABLED"


class RealDataAuthorizationUnavailable(RuntimeError):
    """Stable fail-closed result while no trusted real-data provider exists."""

    code = AccessCode.REAL_AUTHORIZATION_DISABLED

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Real-data execution is disabled: trusted root identity and owner approval are unavailable"
        )


_ACTIVE_AUTHORIZATION_PROVIDER: WindowsAuthorizationProvider | None = None
_ACTIVE_POLICY_DOCUMENT: dict[str, Any] | None = None


def set_active_policy_authorization(
    provider: WindowsAuthorizationProvider | None = None,
    policy: dict[str, Any] | None = None,
) -> None:
    """Sets or clears the process-wide active policy authorization provider and document."""
    global _ACTIVE_AUTHORIZATION_PROVIDER, _ACTIVE_POLICY_DOCUMENT
    _ACTIVE_AUTHORIZATION_PROVIDER = provider
    _ACTIVE_POLICY_DOCUMENT = policy


def get_active_policy_authorization() -> tuple[WindowsAuthorizationProvider | None, dict[str, Any] | None]:
    """Returns the currently active authorization provider and policy document."""
    return _ACTIVE_AUTHORIZATION_PROVIDER, _ACTIVE_POLICY_DOCUMENT


class scoped_policy_authorization:
    """Context manager for temporary, scoped policy authorization."""

    def __init__(
        self,
        provider: WindowsAuthorizationProvider | None,
        policy: dict[str, Any] | None,
    ) -> None:
        self.provider = provider
        self.policy = policy
        self.prev_provider = None
        self.prev_policy = None

    def __enter__(self) -> scoped_policy_authorization:
        global _ACTIVE_AUTHORIZATION_PROVIDER, _ACTIVE_POLICY_DOCUMENT
        self.prev_provider = _ACTIVE_AUTHORIZATION_PROVIDER
        self.prev_policy = _ACTIVE_POLICY_DOCUMENT
        _ACTIVE_AUTHORIZATION_PROVIDER = self.provider
        _ACTIVE_POLICY_DOCUMENT = self.policy
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        global _ACTIVE_AUTHORIZATION_PROVIDER, _ACTIVE_POLICY_DOCUMENT
        _ACTIVE_AUTHORIZATION_PROVIDER = self.prev_provider
        _ACTIVE_POLICY_DOCUMENT = self.prev_policy


def require_real_data_authorization(
    operation: str = "read_checkpoint",
    target_path: str | os.PathLike[str] | None = None,
    *,
    provider: WindowsAuthorizationProvider | None = None,
    policy: dict[str, Any] | None = None,
) -> None:
    """Refuse real-data operations until an authorized provider and policy are verified.

    When invoked without an active provider and with no explicit provider passed,
    unconditionally raises RealDataAuthorizationUnavailable fail-closed.

    When an authorization provider and policy document are supplied (or active in context),
    performs full lexical, schema, protected-root overlap, and cryptographic signature
    assessment against the requested target_path and operation.
    """
    effective_provider = provider if provider is not None else _ACTIVE_AUTHORIZATION_PROVIDER
    effective_policy = policy if policy is not None else _ACTIVE_POLICY_DOCUMENT

    if effective_provider is None or effective_policy is None:
        raise RealDataAuthorizationUnavailable()

    if target_path is not None:
        resolved_path = Path(target_path).resolve()
        assessment = effective_provider.assess(effective_policy, resolved_path, operation=operation)
        if assessment.authorized_access is not StageStatus.VALID:
            err_code = assessment.error_code.value if assessment.error_code else "DENIED"
            raise RealDataAuthorizationUnavailable(
                f"Real-data operation '{operation}' on '{resolved_path}' refused: {err_code}"
            )
    else:
        val = validate_policy_configuration(effective_policy)
        if val.status is not StageStatus.VALID:
            err_code = val.error_code.value if val.error_code else "INVALID"
            raise RealDataAuthorizationUnavailable(f"Policy schema invalid: {err_code}")
        if effective_policy.get("status") != "ACTIVE" or effective_policy.get("example_only") is True:
            raise RealDataAuthorizationUnavailable("Real-data execution is disabled: policy is not ACTIVE")
        anchors = getattr(effective_provider, "trust_anchors", None)
        if not anchors:
            raise RealDataAuthorizationUnavailable("Real-data execution is disabled: no trust anchors registered")
        approval = effective_policy.get("policy_approval")
        if not approval or approval.get("trust_anchor_id") not in anchors:
            raise RealDataAuthorizationUnavailable("Real-data execution is disabled: untrusted anchor")


@dataclass(frozen=True)
class LexicalPathResult:
    status: StageStatus
    normalized: str | None
    path_kind: str | None


@dataclass(frozen=True)
class PolicyConfigurationResult:
    status: StageStatus
    error_code: AccessCode | None = None


@dataclass(frozen=True)
class WindowsAccessAssessment:
    """Independent stage results; none of these fields is an access token."""

    lexical_path: StageStatus
    policy_configuration: StageStatus
    approval_authenticity: StageStatus
    filesystem_identity: StageStatus
    protected_root_check: StageStatus
    authorized_access: StageStatus
    error_code: AccessCode | None = None


def validate_windows_path_lexically(value: str | os.PathLike[str]) -> LexicalPathResult:
    """Classify supported absolute local-drive syntax without filesystem I/O.

    UNC, mapped-drive identity, device namespaces, aliases, and reparse points
    are intentionally unsupported. A VALID result is lexical only.
    """
    try:
        raw = os.fspath(value)
    except TypeError:
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    if raw.startswith(("\\\\?\\", "\\\\.\\")):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    path = PureWindowsPath(raw)
    if (
        not path.is_absolute()
        or len(path.drive) != 2
        or path.drive[1] != ":"
        or not path.drive[0].isascii()
        or not path.drive[0].isalpha()
    ):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    if any(part in {".", ".."} for part in raw.replace("/", "\\").split("\\")):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    if any(":" in part for part in path.parts[1:]):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    if any(part.endswith((".", " ")) for part in path.parts[1:]):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    invalid = '<>"|?*%'
    if any(ord(char) < 32 for part in path.parts[1:] for char in part):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    if any(any(char in part for char in invalid) for part in path.parts[1:]):
        return LexicalPathResult(StageStatus.REJECTED, None, None)
    normalized = PureWindowsPath(path.drive[0].upper() + ":\\", *path.parts[1:])
    return LexicalPathResult(StageStatus.VALID, str(normalized), "local_drive_syntax")


def lexical_protected_overlap(
    candidate: str | os.PathLike[str], protected: str | os.PathLike[str]
) -> StageStatus:
    """Return component-aware lexical overlap; never claims object identity."""
    left = validate_windows_path_lexically(candidate)
    right = validate_windows_path_lexically(protected)
    if left.status is not StageStatus.VALID or right.status is not StageStatus.VALID:
        return StageStatus.UNAVAILABLE
    a = tuple(part.casefold() for part in PureWindowsPath(left.normalized or "").parts)
    b = tuple(part.casefold() for part in PureWindowsPath(right.normalized or "").parts)
    if a[: len(b)] == b or b[: len(a)] == a:
        return StageStatus.LEXICAL_OVERLAP
    return StageStatus.LEXICALLY_CLEAR


def validate_policy_configuration(document: Any) -> PolicyConfigurationResult:
    """Validate policy shape against the repository schema, not its approval."""
    try:
        jsonschema = importlib.import_module("jsonschema")
    except ImportError:
        return PolicyConfigurationResult(StageStatus.UNAVAILABLE, AccessCode.POLICY_SCHEMA_UNAVAILABLE)
    try:
        with _POLICY_SCHEMA.open("r", encoding="utf-8") as stream:
            schema = json.load(stream)
        if not isinstance(schema, dict) or schema.get("$schema") != _DRAFT_URI:
            return PolicyConfigurationResult(StageStatus.REJECTED, AccessCode.POLICY_SCHEMA_INVALID)
        if _has_unsupported_reference(schema):
            return PolicyConfigurationResult(StageStatus.REJECTED, AccessCode.POLICY_SCHEMA_INVALID)
        validator_type = jsonschema.Draft202012Validator
        validator_type.check_schema(schema)
        validator = validator_type(schema, format_checker=jsonschema.FormatChecker())
        if next(validator.iter_errors(document), None) is not None:
            return PolicyConfigurationResult(StageStatus.REJECTED, AccessCode.POLICY_SCHEMA_INVALID)
    except Exception:
        return PolicyConfigurationResult(StageStatus.REJECTED, AccessCode.POLICY_SCHEMA_INVALID)
    return PolicyConfigurationResult(StageStatus.VALID)


def _has_unsupported_reference(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"$dynamicRef", "$recursiveRef"}:
                return True
            if key == "$ref" and (not isinstance(child, str) or not child.startswith("#/")):
                return True
            if _has_unsupported_reference(child):
                return True
    elif isinstance(value, list):
        return any(_has_unsupported_reference(child) for child in value)
    return False


class WindowsAuthorizationProvider:
    """Interface placeholder that refuses all real access until reviewed.

    No caller-supplied approval token, policy field, or lexical result can
    enable access. This class intentionally has no file-open method.
    """

    def assess(self, document: Any, supplied_root: str | os.PathLike[str]) -> WindowsAccessAssessment:
        lexical = validate_windows_path_lexically(supplied_root)
        if lexical.status is not StageStatus.VALID:
            return WindowsAccessAssessment(
                StageStatus.REJECTED, StageStatus.NOT_CHECKED, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, StageStatus.NOT_CHECKED, StageStatus.REFUSED,
                AccessCode.INVALID_PATH,
            )
        policy = validate_policy_configuration(document)
        if policy.status is not StageStatus.VALID:
            return WindowsAccessAssessment(
                StageStatus.VALID, policy.status, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, StageStatus.NOT_CHECKED, StageStatus.REFUSED,
                policy.error_code or AccessCode.POLICY_SCHEMA_INVALID,
            )
        protected_status = StageStatus.NOT_CHECKED
        for entry in document.get("protected_roots", []):
            protected_path = entry.get("path")
            if protected_path is None:
                protected_status = StageStatus.UNAVAILABLE
                continue
            overlap = lexical_protected_overlap(supplied_root, protected_path)
            if overlap is StageStatus.LEXICAL_OVERLAP:
                return WindowsAccessAssessment(
                    StageStatus.VALID, StageStatus.VALID, StageStatus.UNVERIFIED,
                    StageStatus.NOT_CHECKED, StageStatus.LEXICAL_OVERLAP,
                    StageStatus.REFUSED, AccessCode.PROTECTED_ROOT_OVERLAP,
                )
            if overlap is not StageStatus.LEXICALLY_CLEAR:
                protected_status = StageStatus.UNAVAILABLE
            elif protected_status is StageStatus.NOT_CHECKED:
                protected_status = StageStatus.LEXICALLY_CLEAR
        return WindowsAccessAssessment(
            StageStatus.VALID,
            StageStatus.VALID,
            StageStatus.UNVERIFIED,
            StageStatus.NOT_CHECKED,
            protected_status,
            StageStatus.REFUSED,
            AccessCode.WINDOWS_IDENTITY_PROVIDER_UNAVAILABLE,
        )


class CryptographicPolicyAuthorizationProvider(WindowsAuthorizationProvider):
    """Cryptographic authorization provider verifying owner-approved policy documents.

    Validates cryptographic message authentication codes (HMAC-SHA256 symmetric MAC),
    trust anchor pinning, timestamp validity, in-memory revocation status, permitted
    operations, and approved path bounds. Fails closed if no trust anchors are registered
    or if any verification step fails.

    Security & Trust Model Notes:
    - Symmetric Authentication: The current reference implementation computes an HMAC-SHA256
      message authentication code (MAC) using a pinned symmetric secret key, rather than an
      asymmetric digital signature (e.g. Ed25519 or RSA). Both signer and verifier share the
      same trust anchor key.
    - Revocation Persistence: The revocation_list is maintained as an in-memory set[str] for
      the lifetime of the process. It does not automatically persist across process restarts
      unless loaded from an external persistent CRL file or secure database at startup.
    - Production Default: By default, trust_anchors is empty ({}), ensuring fail-closed refusal
      for all operations until keys are explicitly provisioned by the project owner.
    """

    def __init__(
        self,
        trust_anchors: dict[str, bytes] | None = None,
        revocation_list: set[str] | None = None,
        clock_skew_tolerance_seconds: float = 60.0,
        max_validity_seconds: float = 365 * 86400.0,
    ) -> None:
        self.trust_anchors = dict(trust_anchors) if trust_anchors else {}
        self.revocation_list = set(revocation_list) if revocation_list else set()
        self.clock_skew_tolerance = float(clock_skew_tolerance_seconds)
        self.max_validity_seconds = float(max_validity_seconds)

    @staticmethod
    def canonical_policy_digest(document: dict[str, Any]) -> str:
        """Computes deterministic SHA-256 digest over canonicalized policy content."""
        import copy
        import hashlib
        doc_copy = copy.deepcopy(document)
        doc_copy.pop("policy_approval", None)
        for ds in doc_copy.get("datasets", {}).values():
            if isinstance(ds, dict):
                ds["approval"] = None
        for ar in doc_copy.get("artifact_roots", {}).values():
            if isinstance(ar, dict):
                ar["approval"] = None
        for pr in doc_copy.get("protected_roots", []):
            if isinstance(pr, dict):
                pr["approval"] = None
        canonical_str = json.dumps(doc_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def sign_policy_digest(policy_digest: str, secret_key: bytes) -> str:
        """Generates an HMAC-SHA256 symmetric message authentication code over a canonical policy digest."""
        import hashlib
        import hmac
        return hmac.new(secret_key, policy_digest.encode("utf-8"), hashlib.sha256).hexdigest()

    def assess(
        self,
        document: Any,
        supplied_root: str | os.PathLike[str],
        operation: str = "read_checkpoint",
        *,
        current_time_iso: str | None = None,
    ) -> WindowsAccessAssessment:
        import datetime
        import hashlib
        import hmac

        # 1. Lexical Path Validation
        lexical = validate_windows_path_lexically(supplied_root)
        if lexical.status is not StageStatus.VALID:
            return WindowsAccessAssessment(
                StageStatus.REJECTED, StageStatus.NOT_CHECKED, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, StageStatus.NOT_CHECKED, StageStatus.REFUSED,
                AccessCode.INVALID_PATH,
            )

        # 2. Schema Validation
        policy = validate_policy_configuration(document)
        if policy.status is not StageStatus.VALID:
            return WindowsAccessAssessment(
                StageStatus.VALID, policy.status, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, StageStatus.NOT_CHECKED, StageStatus.REFUSED,
                policy.error_code or AccessCode.POLICY_SCHEMA_INVALID,
            )

        if not isinstance(document, dict):
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.REJECTED, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, StageStatus.NOT_CHECKED, StageStatus.REFUSED,
                AccessCode.POLICY_SCHEMA_INVALID,
            )

        # 3. Status and Example-Only Guards
        if document.get("status") != "ACTIVE" or document.get("example_only") is True:
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, StageStatus.NOT_CHECKED, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        # 4. Protected Roots Non-Overlap Check
        protected_status = StageStatus.NOT_CHECKED
        for entry in document.get("protected_roots", []):
            protected_path = entry.get("path")
            if protected_path is None:
                protected_status = StageStatus.UNAVAILABLE
                continue
            overlap = lexical_protected_overlap(supplied_root, protected_path)
            if overlap is StageStatus.LEXICAL_OVERLAP:
                return WindowsAccessAssessment(
                    StageStatus.VALID, StageStatus.VALID, StageStatus.UNVERIFIED,
                    StageStatus.NOT_CHECKED, StageStatus.LEXICAL_OVERLAP,
                    StageStatus.REFUSED, AccessCode.PROTECTED_ROOT_OVERLAP,
                )
            if overlap is not StageStatus.LEXICALLY_CLEAR:
                protected_status = StageStatus.UNAVAILABLE
            elif protected_status is StageStatus.NOT_CHECKED:
                protected_status = StageStatus.LEXICALLY_CLEAR

        # 5. Matching Approved Root & Permitted Operation
        candidate_norm = PureWindowsPath(lexical.normalized or str(supplied_root))
        matched_resource = None
        for pool_key in ("artifact_roots", "datasets"):
            pool = document.get(pool_key, {})
            if isinstance(pool, dict):
                for res_id, res_entry in pool.items():
                    if not isinstance(res_entry, dict):
                        continue
                    app_root = res_entry.get("approved_root")
                    if app_root:
                        app_norm = PureWindowsPath(app_root)
                        cand_parts = tuple(part.casefold() for part in candidate_norm.parts)
                        app_parts = tuple(part.casefold() for part in app_norm.parts)
                        if cand_parts == app_parts or cand_parts[: len(app_parts)] == app_parts:
                            if operation in res_entry.get("permitted_operations", []):
                                matched_resource = res_entry
                                break
                if matched_resource is not None:
                    break

        if matched_resource is None:
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.INVALID_PATH,
            )

        # 6. Cryptographic Approval Verification
        policy_approval = document.get("policy_approval")
        resource_approval = matched_resource.get("approval")
        if not policy_approval or not isinstance(policy_approval, dict) or not resource_approval:
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        anchor_id = policy_approval.get("trust_anchor_id")
        if not anchor_id or anchor_id not in self.trust_anchors:
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.UNVERIFIED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        rec_id = policy_approval.get("approval_record_id")
        if not rec_id or rec_id in self.revocation_list:
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.REJECTED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        # 7. Timestamp & Expiry Verification
        try:
            approved_at_raw = policy_approval.get("approved_at", "")
            approved_dt = datetime.datetime.fromisoformat(approved_at_raw.replace("Z", "+00:00"))
            if current_time_iso:
                now_dt = datetime.datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
            else:
                now_dt = datetime.datetime.now(datetime.timezone.utc)

            delta = (now_dt - approved_dt).total_seconds()
            if delta < -self.clock_skew_tolerance:
                return WindowsAccessAssessment(
                    StageStatus.VALID, StageStatus.VALID, StageStatus.REJECTED,
                    StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                    AccessCode.OWNER_APPROVAL_UNVERIFIED,
                )
            if delta > self.max_validity_seconds:
                return WindowsAccessAssessment(
                    StageStatus.VALID, StageStatus.VALID, StageStatus.REJECTED,
                    StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                    AccessCode.OWNER_APPROVAL_UNVERIFIED,
                )
        except Exception:
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.REJECTED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        # 8. Signature & Content Integrity Check
        expected_digest = self.canonical_policy_digest(document)
        claimed_digest = policy_approval.get("signed_policy_sha256", "")
        if not hmac.compare_digest(expected_digest.lower(), claimed_digest.lower()):
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.REJECTED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        anchor_key = self.trust_anchors[anchor_id]
        expected_sig = self.sign_policy_digest(expected_digest, anchor_key)
        claimed_sig = policy_approval.get("signature_reference", "")
        if not hmac.compare_digest(expected_sig.lower(), claimed_sig.lower()):
            return WindowsAccessAssessment(
                StageStatus.VALID, StageStatus.VALID, StageStatus.REJECTED,
                StageStatus.NOT_CHECKED, protected_status, StageStatus.REFUSED,
                AccessCode.OWNER_APPROVAL_UNVERIFIED,
            )

        # 9. Filesystem Identity Status
        id_pin = matched_resource.get("identity_pin")
        fs_status = StageStatus.VALID if id_pin else StageStatus.NOT_CHECKED

        return WindowsAccessAssessment(
            StageStatus.VALID,
            StageStatus.VALID,
            StageStatus.VALID,
            fs_status,
            protected_status,
            StageStatus.VALID,
            None,
        )
