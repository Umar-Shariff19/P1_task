"""Fail-closed dataset-root authorization primitives.

This module deliberately does not discover files or inspect the filesystem.
Production use requires an explicitly configured policy and a trusted,
platform-specific identity verifier that rejects Windows aliases and reparse
points. No such repository configuration/verifier is currently supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
import os
from pathlib import PureWindowsPath
from typing import Protocol


class DatasetRootRejected(ValueError):
    """Raised when a root is missing authorization or has ambiguous identity."""


@dataclass(frozen=True)
class RootIdentityEvidence:
    """Structured identity attestation required from a trusted OS verifier.

    The type validates the verifier's report shape; it does not itself prove
    that the reported checks were performed correctly.
    """

    canonical_path: str
    volume_identity: str
    root_file_identity: str
    reparse_points_checked: bool
    case_semantics_checked: bool


class RootIdentityVerifier(Protocol):
    """Verify identity after lexical authorization without following aliases.

    Implementations must use no-follow platform handles, validate volume/root
    identity and reject reparse points in every component. Returning ``None``
    means identity could not be established safely.
    """

    def __call__(
        self, supplied_root: str, approved_root: str
    ) -> RootIdentityEvidence | None: ...


@dataclass(frozen=True)
class DatasetAccessPolicy:
    """Explicit dataset authorization and deny roots.

    Roots are Windows absolute paths. This object is configuration, not proof
    that the configured paths themselves are authoritative.
    """

    approved_roots: Mapping[str, str]
    protected_roots: tuple[str, ...]
    identity_verifier: RootIdentityVerifier | None


@dataclass(frozen=True)
class AuthorizedDatasetRoot:
    """Policy result with verifier evidence; not a handle-bound security token.

    Adapters do not accept this object. A synthetic verifier or caller-created
    evidence is not authorization for real dataset access.
    """

    dataset_id: str
    path: PureWindowsPath
    identity: RootIdentityEvidence


def _lexical_windows_path(value: str | os.PathLike[str], *, label: str) -> PureWindowsPath:
    try:
        raw = os.fspath(value)
    except TypeError as exc:
        raise DatasetRootRejected(f"{label} must be a path string") from exc
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise DatasetRootRejected(f"{label} must be a non-empty path string")
    if raw.startswith(("\\\\?\\", "\\\\.\\")):
        raise DatasetRootRejected(f"{label} uses an unsupported device namespace")

    path = PureWindowsPath(raw)
    if not path.is_absolute() or not path.drive or path.drive.startswith("\\"):
        raise DatasetRootRejected(f"{label} must be an absolute local drive path")
    if any(part == ".." for part in path.parts):
        raise DatasetRootRejected(f"{label} must not contain parent traversal")
    if any(":" in part for part in path.parts[1:]):
        raise DatasetRootRejected(f"{label} must not contain alternate data streams")
    if any(part.endswith((".", " ")) for part in path.parts[1:]):
        raise DatasetRootRejected(f"{label} contains a Windows-ambiguous component")
    invalid_characters = '<>"|?*%'
    if any(any(char in part for char in invalid_characters) for part in path.parts[1:]):
        raise DatasetRootRejected(f"{label} contains an unsupported Windows component")
    reserved_names = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    for part in path.parts[1:]:
        stem = part.split(".", 1)[0].upper()
        if stem in reserved_names or stem in {f"COM{i}" for i in range(1, 10)} | {
            f"LPT{i}" for i in range(1, 10)
        }:
            raise DatasetRootRejected(f"{label} contains a reserved Windows name")

    # Normalize only separator and drive-letter spelling. Component case is
    # preserved so a case alias cannot silently become an authorized spelling.
    drive = path.drive[0].upper() + ":\\"
    return PureWindowsPath(drive, *path.parts[1:])


def _parts_key(path: PureWindowsPath) -> tuple[str, ...]:
    return tuple(part.casefold() for part in path.parts)


def _overlaps(left: PureWindowsPath, right: PureWindowsPath) -> bool:
    """True when either root contains the other, compared by components."""
    a, b = _parts_key(left), _parts_key(right)
    return a[: len(b)] == b or b[: len(a)] == a


def authorize_dataset_root(
    dataset_id: str,
    supplied_root: str | os.PathLike[str],
    policy: DatasetAccessPolicy | None,
) -> AuthorizedDatasetRoot:
    """Authorize an exact configured root before any discovery operation.

    This function performs lexical checks only until an exact, non-protected
    dataset/root match exists. It then requires a trusted verifier. It never
    calls ``exists``, ``stat``, ``resolve``, ``open``, or directory discovery.
    """
    if policy is None:
        raise DatasetRootRejected("dataset access policy is required")
    if not isinstance(policy.approved_roots, Mapping) or not policy.approved_roots:
        raise DatasetRootRejected("approved-root policy is missing or malformed")
    if not isinstance(policy.protected_roots, tuple) or not policy.protected_roots:
        raise DatasetRootRejected("protected-root policy is not configured")

    supplied = _lexical_windows_path(supplied_root, label="supplied root")
    protected = tuple(
        _lexical_windows_path(root, label="protected root")
        for root in policy.protected_roots
    )
    if any(_overlaps(supplied, denied) for denied in protected):
        raise DatasetRootRejected("root overlaps a protected path")

    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise DatasetRootRejected("dataset ID must be a non-empty string")
    if dataset_id not in policy.approved_roots:
        raise DatasetRootRejected("dataset ID has no explicit root authorization")

    approved_roots: dict[str, PureWindowsPath] = {}
    for configured_id, configured_root in policy.approved_roots.items():
        if not isinstance(configured_id, str) or not configured_id.strip():
            raise DatasetRootRejected("approved-root policy has an invalid dataset ID")
        parsed_root = _lexical_windows_path(configured_root, label="approved root")
        if len(parsed_root.parts) == 1:
            raise DatasetRootRejected("a volume root is too broad to authorize as a dataset")
        if any(_overlaps(parsed_root, denied) for denied in protected):
            raise DatasetRootRejected("approved root overlaps a protected path")
        for other_id, other_root in approved_roots.items():
            if _overlaps(parsed_root, other_root):
                raise DatasetRootRejected(
                    f"approved roots for {configured_id!r} and {other_id!r} overlap"
                )
        approved_roots[configured_id] = parsed_root

    approved = approved_roots[dataset_id]
    if str(supplied) != str(approved):
        raise DatasetRootRejected("supplied root is not the exact authorized root")
    if not callable(policy.identity_verifier):
        raise DatasetRootRejected("trusted path-identity verifier is not configured")

    try:
        identity = policy.identity_verifier(str(supplied), str(approved))
    except Exception as exc:
        raise DatasetRootRejected("root identity could not be verified safely") from exc
    if (
        not isinstance(identity, RootIdentityEvidence)
        or not isinstance(identity.canonical_path, str)
        or identity.canonical_path != str(approved)
        or not isinstance(identity.volume_identity, str)
        or not identity.volume_identity.strip()
        or not isinstance(identity.root_file_identity, str)
        or not identity.root_file_identity.strip()
        or identity.reparse_points_checked is not True
        or identity.case_semantics_checked is not True
    ):
        raise DatasetRootRejected("root identity is ambiguous or could not be verified")
    return AuthorizedDatasetRoot(dataset_id, approved, identity)
