"""Synthetic-only tests for the fail-closed Windows access boundary."""
from __future__ import annotations

import ctypes
import json
from enum import Enum
import os
from pathlib import Path
import tempfile

import pytest

from iot_ids.provenance.windows_access import (
    AccessCode,
    StageStatus,
    RealDataAuthorizationUnavailable,
    WindowsAuthorizationProvider,
    lexical_protected_overlap,
    require_real_data_authorization,
    validate_policy_configuration,
    validate_windows_path_lexically,
)


def test_real_data_authorization_gate_is_unconditional_and_path_free() -> None:
    with pytest.raises(RealDataAuthorizationUnavailable) as blocked:
        require_real_data_authorization()
    assert blocked.value.code is AccessCode.REAL_AUTHORIZATION_DISABLED
    assert "trusted root identity" in str(blocked.value)
from iot_ids.provenance.windows_handle import (
    HandlePrimitiveCode,
    WindowsHandlePrimitiveError,
    open_child_file_readonly,
)


_POLICY_EXAMPLE = (
    Path(__file__).parents[2]
    / "results"
    / "implementation"
    / "dataset_access_policy.example.json"
)


def _draft_policy() -> dict:
    return json.loads(_POLICY_EXAMPLE.read_text(encoding="utf-8"))


def _read_synthetic_file(handle) -> bytes:
    chunks: list[bytes] = []
    while chunk := handle.read(4096):
        chunks.append(chunk)
    return b"".join(chunks)


class _SyntheticDirectoryHandle:
    """Test-owned HANDLE for a temporary directory, not an auth context."""

    def __init__(self, path: Path) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_directory = kernel32.CreateFileW
        open_directory.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        open_directory.restype = ctypes.c_void_p
        handle = open_directory(
            str(path),
            0x0001 | 0x0080,  # FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES
            0x0001 | 0x0002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,  # OPEN_EXISTING
            0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
            None,
        )
        if handle in (None, ctypes.c_void_p(-1).value):
            raise OSError("synthetic test directory handle unavailable")
        self.value = int(handle)
        self._kernel32 = kernel32

    def close(self) -> None:
        close = self._kernel32.CloseHandle
        close.argtypes = [ctypes.c_void_p]
        close.restype = ctypes.c_int
        close(ctypes.c_void_p(self.value))

    def __enter__(self) -> "_SyntheticDirectoryHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def test_lexical_local_paths_normalize_drive_only_and_preserve_component_case() -> None:
    accepted = validate_windows_path_lexically(r"c:\Synthetic\Data")
    assert accepted.status is StageStatus.VALID
    assert accepted.normalized == r"C:\Synthetic\Data"
    assert accepted.path_kind == "local_drive_syntax"


@pytest.mark.parametrize(
    "path",
    [
        r"relative\data",
        r"C:drive-relative",
        r"C:\synthetic\..\outside",
        r"C:\synthetic\.\data",
        r"\\server\share\data",
        r"\\?\C:\synthetic\data",
        r"C:\synthetic\file:stream",
        r"C:\synthetic\trailing.",
    ],
)
def test_unsupported_or_ambiguous_lexical_paths_fail_closed(path: str) -> None:
    assert validate_windows_path_lexically(path).status is StageStatus.REJECTED


def test_protected_overlap_is_component_aware_and_lexical_only() -> None:
    assert lexical_protected_overlap(
        r"C:\Synthetic\Protected\child", r"C:\Synthetic\Protected"
    ) is StageStatus.LEXICAL_OVERLAP
    assert lexical_protected_overlap(
        r"C:\Synthetic\ProtectedCopy", r"C:\Synthetic\Protected"
    ) is StageStatus.LEXICALLY_CLEAR


def test_schema_valid_policy_does_not_authenticate_or_enable_access() -> None:
    policy = _draft_policy()
    assert validate_policy_configuration(policy).status is StageStatus.VALID
    assessment = WindowsAuthorizationProvider().assess(policy, r"C:\Synthetic\Data")
    assert assessment.lexical_path is StageStatus.VALID
    assert assessment.policy_configuration is StageStatus.VALID
    assert assessment.approval_authenticity is StageStatus.UNVERIFIED
    assert assessment.filesystem_identity is StageStatus.NOT_CHECKED
    assert assessment.authorized_access is StageStatus.REFUSED
    assert assessment.error_code is AccessCode.WINDOWS_IDENTITY_PROVIDER_UNAVAILABLE


def test_schema_valid_active_synthetic_approval_fields_still_do_not_authorize() -> None:
    policy = _draft_policy()
    pin = {
        "path_kind": "local_drive",
        "volume_identity": "SYNTHETIC-UNVERIFIED-VOLUME",
        "root_file_identity": "SYNTHETIC-UNVERIFIED-FILE-ID",
        "case_policy": "case_insensitive",
    }
    fake_approval = {
        "approval_record_id": "SYNTHETIC-FAKE-RECORD",
        "approver_identity": "SYNTHETIC-UNVERIFIED-APPROVER",
        "approved_at": "2026-10-28T00:00:00Z",
        "trust_anchor_id": "SYNTHETIC-NO-TRUST-ANCHOR",
        "signed_policy_sha256": "a" * 64,
        "signature_reference": "SYNTHETIC-NOT-A-SIGNATURE",
    }
    policy.update(
        {
            "example_only": False,
            "status": "ACTIVE",
            "policy_revision": "SYNTHETIC-UNAUTHENTICATED-REVISION",
            "filesystem_policy_version": "SYNTHETIC-UNREVIEWED-POLICY",
            "policy_approval": fake_approval,
        }
    )
    policy["datasets"]["synthetic-example-only"].update(
        {
            "approved_root": r"C:\Synthetic\Dataset",
            "permitted_operations": ["discover_dataset_files"],
            "identity_pin": pin,
            "approval": fake_approval,
        }
    )
    policy["protected_roots"] = [
        {
            "root_id": "synthetic-protected-only",
            "path": r"C:\Synthetic\Protected",
            "coverage": "ancestors_and_descendants",
            "identity_pin": pin,
            "approval": fake_approval,
        }
    ]
    assert validate_policy_configuration(policy).status is StageStatus.VALID
    assessment = WindowsAuthorizationProvider().assess(policy, r"C:\Synthetic\Dataset")
    assert assessment.policy_configuration is StageStatus.VALID
    assert assessment.approval_authenticity is StageStatus.UNVERIFIED
    assert assessment.filesystem_identity is StageStatus.NOT_CHECKED
    assert assessment.authorized_access is StageStatus.REFUSED


def test_invalid_policy_and_protected_overlap_are_refused_without_access() -> None:
    policy = _draft_policy()
    policy["unknown"] = "synthetic"
    invalid = WindowsAuthorizationProvider().assess(policy, r"C:\Synthetic\Data")
    assert invalid.policy_configuration is StageStatus.REJECTED
    assert invalid.authorized_access is StageStatus.REFUSED

    overlapping = _draft_policy()
    overlapping["protected_roots"][0]["path"] = r"C:\Synthetic"
    result = WindowsAuthorizationProvider().assess(overlapping, r"C:\Synthetic\Data")
    assert result.protected_root_check is StageStatus.LEXICAL_OVERLAP
    assert result.authorized_access is StageStatus.REFUSED
    assert result.error_code is AccessCode.PROTECTED_ROOT_OVERLAP


class _SyntheticDecision(Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"


class _TestOnlySyntheticPolicy:
    """Local test fixture; deliberately absent from the production package."""

    def __init__(self, approved_root: Path) -> None:
        self._approved_root = approved_root.resolve()

    def decide(self, dataset_id: str, root: Path) -> _SyntheticDecision:
        if dataset_id != "SYNTHETIC_FIXTURE_ONLY":
            return _SyntheticDecision.DENY
        try:
            supplied = root.resolve(strict=True)
        except OSError:
            return _SyntheticDecision.DENY
        if root.is_symlink():
            return _SyntheticDecision.DENY
        return (
            _SyntheticDecision.PERMIT
            if supplied == self._approved_root
            else _SyntheticDecision.DENY
        )


def test_test_local_synthetic_policy_permits_and_denies_only_temp_paths() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-auth-"
    ) as directory:
        base = Path(directory)
        approved = base / "approved"
        denied = base / "outside"
        approved.mkdir()
        denied.mkdir()
        provider = _TestOnlySyntheticPolicy(approved)
        output: list[str] = []

        if provider.decide("SYNTHETIC_FIXTURE_ONLY", approved) is _SyntheticDecision.PERMIT:
            output.append("SYNTHETIC_OPERATION")
        assert output == ["SYNTHETIC_OPERATION"]
        assert provider.decide("SYNTHETIC_FIXTURE_ONLY", denied) is _SyntheticDecision.DENY
        assert provider.decide("SYNTHETIC_FIXTURE_ONLY", base / "missing") is _SyntheticDecision.DENY
        assert provider.decide("REAL_DATA_ID", approved) is _SyntheticDecision.DENY


def test_synthetic_symlink_alias_is_denied_by_test_local_fixture() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-alias-"
    ) as directory:
        base = Path(directory)
        approved = base / "approved"
        approved.mkdir()
        alias = base / "alias"
        try:
            alias.symlink_to(approved, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("directory symlink creation is unavailable")
        # This checks only the test fixture's obvious symlink alias. The
        # production module does not verify symlinks or Windows reparse tags.
        provider = _TestOnlySyntheticPolicy(approved)
        assert provider.decide("SYNTHETIC_FIXTURE_ONLY", alias) is _SyntheticDecision.DENY


def test_native_handle_relative_open_reads_only_named_synthetic_child() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-handle-"
    ) as directory:
        root = Path(directory)
        (root / "metric.txt").write_bytes(b"SYNTHETIC_METRIC=0.125; NOT IDS PERFORMANCE")
        with _SyntheticDirectoryHandle(root) as handle:
            with open_child_file_readonly(handle.value, "metric.txt") as opened:
                assert _read_synthetic_file(opened) == b"SYNTHETIC_METRIC=0.125; NOT IDS PERFORMANCE"
                assert opened.identity.hardlink_count == 1
                assert opened.identity.volume_serial > 0
                assert opened.identity.file_index > 0


def test_native_handle_open_rejects_traversal_and_missing_child() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-handle-invalid-"
    ) as directory:
        with _SyntheticDirectoryHandle(Path(directory)) as handle:
            with pytest.raises(WindowsHandlePrimitiveError) as traversal:
                open_child_file_readonly(handle.value, "..")
            assert traversal.value.code is HandlePrimitiveCode.INVALID_CHILD_NAME
            with pytest.raises(WindowsHandlePrimitiveError) as missing:
                open_child_file_readonly(handle.value, "missing.txt")
            assert missing.value.code is HandlePrimitiveCode.OPEN_FAILED


def test_native_handle_keeps_open_object_across_synthetic_path_replacement() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-handle-race-"
    ) as directory:
        root = Path(directory)
        target = root / "value.txt"
        target.write_bytes(b"synthetic-original")
        with _SyntheticDirectoryHandle(root) as handle:
            with open_child_file_readonly(handle.value, "value.txt") as held:
                original_identity = held.identity
                target.replace(root / "moved.txt")
                target.write_bytes(b"synthetic-replacement")
                assert _read_synthetic_file(held) == b"synthetic-original"
                with open_child_file_readonly(handle.value, "value.txt") as current:
                    assert _read_synthetic_file(current) == b"synthetic-replacement"
                    assert current.identity != original_identity


def test_native_handle_rejects_synthetic_hardlink_when_supported() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-hardlink-"
    ) as directory:
        root = Path(directory)
        outside = root / "outside.txt"
        outside.write_bytes(b"synthetic-hardlink-content")
        alias = root / "alias.txt"
        try:
            os.link(outside, alias)
        except (OSError, NotImplementedError):
            pytest.skip("synthetic hard links are unavailable on this filesystem")
        with _SyntheticDirectoryHandle(root) as handle:
            with pytest.raises(WindowsHandlePrimitiveError) as rejected:
                open_child_file_readonly(handle.value, "alias.txt")
            assert rejected.value.code is HandlePrimitiveCode.HARDLINK_AMBIGUOUS


def test_native_handle_rejects_synthetic_leaf_symlink_when_supported() -> None:
    with tempfile.TemporaryDirectory(
        prefix="synthetic-reparse-"
    ) as directory:
        root = Path(directory) / "root"
        root.mkdir()
        target = Path(directory) / "outside.txt"
        target.write_bytes(b"synthetic-target")
        alias = root / "alias.txt"
        try:
            alias.symlink_to(target)
        except (OSError, NotImplementedError):
            pytest.skip("synthetic file symlink creation is unavailable")
        with _SyntheticDirectoryHandle(root) as handle:
            with pytest.raises(WindowsHandlePrimitiveError) as rejected:
                open_child_file_readonly(handle.value, "alias.txt")
            assert rejected.value.code is HandlePrimitiveCode.REPARSE_POINT_REJECTED
