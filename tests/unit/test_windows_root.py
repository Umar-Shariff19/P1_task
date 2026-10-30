"""Synthetic-only tests for Windows root-handle identity observation.

All native handles in this module refer to temporary fixtures under this test
directory. No path supplied here is a research-data path. API failure tests
are mocked and are not evidence of native failure behavior.
"""
from __future__ import annotations

import ctypes
from pathlib import Path
import os
import tempfile

import pytest

from iot_ids.provenance import windows_root
from iot_ids.provenance.windows_root import (
    ObservedDirectoryIdentity,
    RootAcquisitionStatus,
    RealRootAuthorizationStatus,
    RootIdentityCode,
    RootIdentityStatus,
    WindowsRootHandleAcquisitionProvider,
    WindowsRealRootAuthorizationProvider,
    observe_directory_handle,
)


pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="native HANDLE observation requires Windows"
)


class _SyntheticHandle:
    """Test-owned handle with deterministic close and no authorization role."""

    def __init__(self, path: Path, *, directory: bool) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel32.CreateFileW
        create.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create.restype = ctypes.c_void_p
        flags = 0x00200000 | (0x02000000 if directory else 0)  # OPEN_REPARSE_POINT, BACKUP_SEMANTICS
        handle = create(
            str(path),
            0x80,  # FILE_READ_ATTRIBUTES
            0x1 | 0x2 | 0x4,  # SHARE_READ | SHARE_WRITE | SHARE_DELETE
            None,
            3,  # OPEN_EXISTING
            flags,
            None,
        )
        if handle in (None, ctypes.c_void_p(-1).value):
            raise OSError("synthetic fixture handle unavailable")
        self.value = int(handle)
        self._kernel32 = kernel32

    def close(self) -> None:
        if self.value is None:
            return
        close = self._kernel32.CloseHandle
        close.argtypes = [ctypes.c_void_p]
        close.restype = ctypes.c_int
        if not close(ctypes.c_void_p(self.value)):
            raise OSError("synthetic fixture handle close failed")
        self.value = None

    def __enter__(self) -> "_SyntheticHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def test_native_observation_reports_synthetic_directory_as_unverified() -> None:
    with tempfile.TemporaryDirectory(prefix="synthetic-root-") as raw:
        with _SyntheticHandle(Path(raw), directory=True) as handle:
            result = observe_directory_handle(handle.value)
            assert result.status is RootIdentityStatus.OBSERVED_UNVERIFIED
            assert result.identity is not None
            assert result.identity.volume_serial > 0
            assert result.identity.file_index > 0
            assert result.error_code is None


def test_invalid_and_non_directory_handles_are_rejected() -> None:
    invalid = observe_directory_handle(-1)
    assert invalid.status is RootIdentityStatus.REJECTED
    assert invalid.error_code is RootIdentityCode.INVALID_HANDLE
    with tempfile.TemporaryDirectory(prefix="synthetic-file-") as raw:
        file_path = Path(raw) / "synthetic.txt"
        file_path.write_text("synthetic only", encoding="utf-8")
        with _SyntheticHandle(file_path, directory=False) as handle:
            result = observe_directory_handle(handle.value)
            assert result.status is RootIdentityStatus.REJECTED
            assert result.error_code is RootIdentityCode.NOT_DIRECTORY


def test_final_directory_symlink_handle_is_rejected_when_supported() -> None:
    with tempfile.TemporaryDirectory(prefix="synthetic-reparse-root-") as raw:
        parent = Path(raw)
        target = parent / "target"
        target.mkdir()
        alias = parent / "alias"
        try:
            alias.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("synthetic directory symlink creation is unavailable")
        with _SyntheticHandle(alias, directory=True) as handle:
            result = observe_directory_handle(handle.value)
            assert result.status is RootIdentityStatus.REJECTED
            assert result.error_code is RootIdentityCode.REPARSE_POINT


def test_api_failure_is_sanitized_and_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory(prefix="synthetic-api-failure-") as raw:
        with _SyntheticHandle(Path(raw), directory=True) as handle:
            def fail(_handle: int):
                raise OSError("mocked inaccessible handle with private path details")

            monkeypatch.setattr(windows_root, "_query_handle_metadata", fail)
            result = observe_directory_handle(handle.value)
            assert result.status is RootIdentityStatus.UNAVAILABLE
            assert result.error_code is RootIdentityCode.HANDLE_METADATA_UNAVAILABLE
            assert "private" not in repr(result)


def test_handle_observation_stays_bound_after_synthetic_directory_rename() -> None:
    with tempfile.TemporaryDirectory(prefix="synthetic-rename-") as raw:
        parent = Path(raw)
        original = parent / "root"
        original.mkdir()
        with _SyntheticHandle(original, directory=True) as handle:
            before = observe_directory_handle(handle.value)
            assert before.status is RootIdentityStatus.OBSERVED_UNVERIFIED
            moved = parent / "renamed-root"
            original.rename(moved)
            original.mkdir()
            after = observe_directory_handle(handle.value)
            assert after.status is RootIdentityStatus.OBSERVED_UNVERIFIED
            assert after.identity == before.identity
            with _SyntheticHandle(original, directory=True) as replacement:
                replacement_result = observe_directory_handle(replacement.value)
                assert replacement_result.status is RootIdentityStatus.OBSERVED_UNVERIFIED
                assert replacement_result.identity != before.identity


def test_fabricated_or_mismatched_identity_and_missing_approval_never_authorize() -> None:
    fabricated = ObservedDirectoryIdentity(
        volume_serial=0xDEADBEEF,
        file_index=0x12345678,
        attributes=0x10,
        hardlink_count=1,
    )
    provider = WindowsRealRootAuthorizationProvider()
    for untrusted_claim in (None, fabricated, {"approval": "synthetic-fabrication"}):
        decision = provider.authorize(untrusted_claim)
        assert decision.status is RealRootAuthorizationStatus.DENIED
        assert decision.error_code is RootIdentityCode.REAL_AUTHORIZATION_DISABLED


def test_root_acquisition_provider_fails_closed_without_coercing_or_opening_inputs() -> None:
    class _MustNotBeCoerced:
        def __fspath__(self):
            raise AssertionError("unavailable provider must not inspect path")

    result = WindowsRootHandleAcquisitionProvider().acquire(
        _MustNotBeCoerced(),
        {"root": "SYNTHETIC-UNAUTHENTICATED"},
        {"approval": "FABRICATED"},
    )
    assert result.status is RootAcquisitionStatus.UNAVAILABLE
    assert result.handle is None
    assert result.identity is None
    assert result.error_code is RootIdentityCode.SAFE_ACQUISITION_UNAVAILABLE

    synthetic_missing = Path(__file__).parent / "synthetic-nonexistent-root"
    absent = WindowsRootHandleAcquisitionProvider().acquire(
        synthetic_missing, synthetic_missing, {"approval": "UNAUTHENTICATED"}
    )
    assert absent.status is RootAcquisitionStatus.UNAVAILABLE
    assert absent.handle is None


def test_identity_from_replaced_synthetic_root_does_not_authorize_other_root() -> None:
    with tempfile.TemporaryDirectory(prefix="synthetic-mismatch-") as raw:
        parent = Path(raw)
        first = parent / "first"
        second = parent / "second"
        first.mkdir()
        second.mkdir()
        with _SyntheticHandle(first, directory=True) as first_handle:
            with _SyntheticHandle(second, directory=True) as second_handle:
                first_observation = observe_directory_handle(first_handle.value)
                second_observation = observe_directory_handle(second_handle.value)
                assert first_observation.status is RootIdentityStatus.OBSERVED_UNVERIFIED
                assert second_observation.status is RootIdentityStatus.OBSERVED_UNVERIFIED
                assert first_observation.identity != second_observation.identity
                # Even a mismatch detected by the test is not a trusted policy
                # comparison and cannot create owner approval.
                decision = WindowsRealRootAuthorizationProvider().authorize(
                    first_observation.identity, second_observation.identity
                )
                assert decision.status is RealRootAuthorizationStatus.DENIED
                assert decision.error_code is RootIdentityCode.REAL_AUTHORIZATION_DISABLED


def test_handle_is_closed_when_observation_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory(prefix="synthetic-close-") as raw:
        handle = _SyntheticHandle(Path(raw), directory=True)
        value = handle.value
        monkeypatch.setattr(
            windows_root,
            "_query_handle_metadata",
            lambda _handle: (_ for _ in ()).throw(RuntimeError("synthetic test failure")),
        )
        try:
            assert observe_directory_handle(value).status is RootIdentityStatus.UNAVAILABLE
        finally:
            handle.close()
        assert handle.value is None
