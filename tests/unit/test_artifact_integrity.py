"""Synthetic temporary-file tests for explicit artifact digest checks."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

import pytest

from iot_ids.provenance import (
    ArtifactIntegrityError,
    validate_digest_declaration,
    verify_artifact_digest,
)


_REPO_ROOT = Path(__file__).parents[1]


@pytest.fixture
def synthetic_tree():
    with tempfile.TemporaryDirectory(prefix=".synthetic-artifact-integrity-") as temp_dir:
        yield Path(temp_dir)


def test_digest_declaration_accepts_sha256_only() -> None:
    digest = "A" * 64
    assert validate_digest_declaration("sha256", digest) == ("sha256", "a" * 64)
    with pytest.raises(ArtifactIntegrityError, match="unsupported"):
        validate_digest_declaration("md5", "a" * 32)
    with pytest.raises(ArtifactIntegrityError, match="malformed"):
        validate_digest_declaration("sha256", "not-a-digest")


def test_matching_synthetic_file_reports_integrity_only(synthetic_tree: Path) -> None:
    contents = b"synthetic artifact bytes; not an IDS result\n"
    artifact = synthetic_tree / "result.bin"
    artifact.write_bytes(contents)
    expected = hashlib.sha256(contents).hexdigest()
    result = verify_artifact_digest(
        "result.bin", algorithm="sha256", expected_digest=expected, base_dir=synthetic_tree
    )
    assert result.status == "MATCH"
    assert result.actual_digest == expected
    assert result.authorization_verified is False
    assert result.scientific_validity_verified is False
    assert result.provenance_verified is False


def test_missing_synthetic_file_is_reported(synthetic_tree: Path) -> None:
    result = verify_artifact_digest(
        "missing.bin", algorithm="sha256", expected_digest="0" * 64, base_dir=synthetic_tree
    )
    assert result.status == "MISSING"
    assert result.actual_digest is None


def test_modified_synthetic_file_reports_digest_mismatch(synthetic_tree: Path) -> None:
    artifact = synthetic_tree / "result.bin"
    artifact.write_bytes(b"initial synthetic bytes")
    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.write_bytes(b"modified synthetic bytes")
    result = verify_artifact_digest(
        "result.bin", algorithm="sha256", expected_digest=expected, base_dir=synthetic_tree
    )
    assert result.status == "MISMATCH"
    assert result.actual_digest != expected


@pytest.mark.parametrize("relative_path", ["../escape.bin", "nested/../../escape.bin"])
def test_relative_path_escape_is_rejected_before_file_access(
    synthetic_tree: Path, relative_path: str
) -> None:
    with pytest.raises(ArtifactIntegrityError, match="escapes"):
        verify_artifact_digest(
            relative_path,
            algorithm="sha256",
            expected_digest="0" * 64,
            base_dir=synthetic_tree,
        )


def test_absolute_manifest_path_is_rejected(synthetic_tree: Path) -> None:
    outside = synthetic_tree / "outside.bin"
    with pytest.raises(ArtifactIntegrityError, match="escapes"):
        verify_artifact_digest(
            str(outside),
            algorithm="sha256",
            expected_digest="0" * 64,
            base_dir=synthetic_tree,
        )


def test_relative_base_is_rejected_before_artifact_access() -> None:
    with pytest.raises(ArtifactIntegrityError, match="absolute artifact base"):
        verify_artifact_digest(
            "result.bin", algorithm="sha256", expected_digest="0" * 64, base_dir="relative-base"
        )


def test_symlink_escape_is_rejected_when_supported(synthetic_tree: Path) -> None:
    base = synthetic_tree / "base"
    outside = synthetic_tree / "outside"
    base.mkdir()
    outside.mkdir()
    (outside / "result.bin").write_bytes(b"synthetic outside bytes")
    alias = base / "alias"
    try:
        alias.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable in this synthetic environment")
    with pytest.raises(ArtifactIntegrityError, match="symlink or reparse"):
        verify_artifact_digest(
            "alias/result.bin",
            algorithm="sha256",
            expected_digest="0" * 64,
            base_dir=base,
        )


def test_reparse_point_rejection_without_elevation(synthetic_tree: Path) -> None:
    """Deterministically verifies that verify_artifact_digest rejects reparse points even without elevation."""
    import stat
    from unittest.mock import patch, MagicMock

    base = synthetic_tree / "base_reparse"
    base.mkdir()
    target_file = base / "artifact.bin"
    target_file.write_bytes(b"deterministic content")

    orig_lstat = os.lstat

    def mock_lstat(path):
        st = orig_lstat(path)
        if "artifact.bin" in str(path):
            mock_stat = MagicMock()
            mock_stat.st_mode = st.st_mode
            # Inject Windows FILE_ATTRIBUTE_REPARSE_POINT (0x400)
            mock_stat.st_file_attributes = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            return mock_stat
        return st

    with patch("os.lstat", side_effect=mock_lstat):
        with pytest.raises(ArtifactIntegrityError, match="symlink or reparse"):
            verify_artifact_digest(
                "artifact.bin",
                algorithm="sha256",
                expected_digest="0" * 64,
                base_dir=base,
            )

