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

    def __init__(self) -> None:
        super().__init__(
            "Real-data execution is disabled: trusted root identity and owner approval are unavailable"
        )


def require_real_data_authorization() -> None:
    """Refuse real-data operations until an independently reviewed provider exists.

    This check has no path argument and performs no filesystem access. A valid
    manifest, policy document, or caller-constructed identity record cannot
    change this decision.
    """
    raise RealDataAuthorizationUnavailable()


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
    error_code: AccessCode


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
