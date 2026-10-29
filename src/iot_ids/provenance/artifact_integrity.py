"""Explicit-path artifact digest checks for isolated prospective workflows.

This helper checks byte integrity only. It does not establish authorization,
artifact provenance, or scientific validity. Use only with a caller-selected
safe base; it is not a Windows filesystem authorization boundary and is not
connected to research runners.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path, PureWindowsPath
import re
import stat
from typing import Any, Literal


class ArtifactIntegrityError(ValueError):
    """Raised when a digest declaration or artifact path is invalid/ambiguous."""


@dataclass(frozen=True)
class ArtifactIntegrityResult:
    status: Literal["MATCH", "MISMATCH", "MISSING"]
    algorithm: Literal["sha256"]
    expected_digest: str
    actual_digest: str | None
    authorization_verified: bool = False
    scientific_validity_verified: bool = False
    provenance_verified: bool = False


def validate_digest_declaration(algorithm: str, digest: str) -> tuple[str, str]:
    """Validate a digest declaration without reading a file or artifact."""
    if algorithm != "sha256":
        raise ArtifactIntegrityError("unsupported artifact digest algorithm")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
        raise ArtifactIntegrityError("malformed SHA-256 digest declaration")
    return "sha256", digest.lower()


def _relative_artifact_path(value: str | os.PathLike[str]) -> Path:
    try:
        raw = os.fspath(value)
    except TypeError as exc:
        raise ArtifactIntegrityError("artifact path must be a relative path") from exc
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ArtifactIntegrityError("artifact path must be a non-empty relative path")
    windows_path = PureWindowsPath(raw)
    path = Path(raw)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or any(part == ".." for part in path.parts)
        or any(part == ".." for part in windows_path.parts)
        or any(":" in part or part.endswith((".", " ")) for part in windows_path.parts)
    ):
        raise ArtifactIntegrityError("artifact path escapes or is outside the supplied base")
    return path


def verify_artifact_digest(
    relative_path: str | os.PathLike[str],
    *,
    algorithm: str,
    expected_digest: str,
    base_dir: str | os.PathLike[str],
) -> ArtifactIntegrityResult:
    """Compare an explicitly named file with a declared digest under ``base_dir``.

    The base must be explicit and absolute. Only the named relative path is
    inspected; this function never traverses or discovers sibling artifacts.
    Symlink/reparse components are rejected. Concurrent filesystem mutation is
    not prevented, so this is not a production authorization/security boundary.
    """
    normalized_algorithm, expected = validate_digest_declaration(algorithm, expected_digest)
    relative = _relative_artifact_path(relative_path)
    try:
        base = Path(base_dir)
    except TypeError as exc:
        raise ArtifactIntegrityError("an explicit absolute artifact base is required") from exc
    if not base.is_absolute():
        raise ArtifactIntegrityError("an explicit absolute artifact base is required")
    try:
        base = base.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ArtifactIntegrityError("artifact base is unavailable or ambiguous") from exc
    if not base.is_dir():
        raise ArtifactIntegrityError("artifact base is not a directory")

    candidate = base / relative
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ArtifactIntegrityError("artifact path escapes the supplied base") from exc

    current = base
    parts = relative.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return ArtifactIntegrityResult("MISSING", normalized_algorithm, expected, None)
        except OSError as exc:
            raise ArtifactIntegrityError("artifact path could not be inspected safely") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if stat.S_ISLNK(info.st_mode) or attributes & reparse_flag:
            raise ArtifactIntegrityError("artifact path contains a symlink or reparse point")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise ArtifactIntegrityError("artifact path has a non-directory parent")
        if index == len(parts) - 1 and not stat.S_ISREG(info.st_mode):
            raise ArtifactIntegrityError("artifact is not a regular file")

    digest = hashlib.sha256()
    try:
        with candidate.open("rb") as artifact_file:
            for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ArtifactIntegrityError("artifact could not be read safely") from exc
    actual = digest.hexdigest()
    status: Literal["MATCH", "MISMATCH"] = "MATCH" if actual == expected else "MISMATCH"
    return ArtifactIntegrityResult(status, normalized_algorithm, expected, actual)


def verify_and_read_artifact(
    relative_path: str | os.PathLike[str],
    *,
    expected_digest: str,
    base_dir: str | os.PathLike[str],
    algorithm: str = "sha256",
) -> bytes:
    """Read an artifact file into memory ONLY after verifying its digest matches expected_digest.

    Uses constant-time comparison (hmac.compare_digest) and safe path checks.
    Reading the verified bytes once into memory prevents TOCTOU / file-swapping bypasses.
    """
    normalized_algorithm, expected = validate_digest_declaration(algorithm, expected_digest)
    relative = _relative_artifact_path(relative_path)
    try:
        base = Path(base_dir)
    except TypeError as exc:
        raise ArtifactIntegrityError("an explicit absolute artifact base is required") from exc
    if not base.is_absolute():
        raise ArtifactIntegrityError("an explicit absolute artifact base is required")
    try:
        base = base.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ArtifactIntegrityError("artifact base is unavailable or ambiguous") from exc
    if not base.is_dir():
        raise ArtifactIntegrityError("artifact base is not a directory")

    candidate = base / relative
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ArtifactIntegrityError("artifact path escapes the supplied base") from exc

    current = base
    parts = relative.parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            raise ArtifactIntegrityError(f"artifact file is missing: {relative.name}") from None
        except OSError as exc:
            raise ArtifactIntegrityError("artifact path could not be inspected safely") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if stat.S_ISLNK(info.st_mode) or attributes & reparse_flag:
            raise ArtifactIntegrityError("artifact path contains a symlink or reparse point")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise ArtifactIntegrityError("artifact path has a non-directory parent")
        if index == len(parts) - 1 and not stat.S_ISREG(info.st_mode):
            raise ArtifactIntegrityError("artifact is not a regular file")

    try:
        with candidate.open("rb") as artifact_file:
            content = artifact_file.read()
    except OSError as exc:
        raise ArtifactIntegrityError("artifact could not be read safely") from exc

    actual = hashlib.sha256(content).hexdigest()
    if not hmac.compare_digest(actual.lower(), expected.lower()):
        raise ArtifactIntegrityError(
            f"Digest mismatch for '{relative.name}': expected {expected}, got {actual}"
        )

    return content


def load_verified_joblib(
    relative_path: str | os.PathLike[str],
    *,
    expected_digest: str,
    base_dir: str | os.PathLike[str],
) -> Any:
    """Securely deserializes a joblib artifact from in-memory verified bytes.

    Verifies the SHA-256 digest before deserialization, and deserializes
    exclusively from the verified in-memory byte buffer to eliminate TOCTOU risks.
    """
    import io
    import joblib

    content = verify_and_read_artifact(
        relative_path, expected_digest=expected_digest, base_dir=base_dir
    )
    try:
        return joblib.load(io.BytesIO(content))
    except Exception as exc:
        raise TypeError(
            f"Failed to safely deserialize artifact '{Path(relative_path).name}': {type(exc).__name__}"
        ) from exc

