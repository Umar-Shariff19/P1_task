"""Observe an already-open Windows directory handle; never authorize a root.

This module deliberately does not open a path. ``observe_directory_handle``
queries metadata for a caller-owned HANDLE and labels the result
``OBSERVED_UNVERIFIED``. The caller remains responsible for keeping that handle
open and closing it. Neither this observation nor a schema-valid policy can
establish path provenance or owner approval. Real-data authorization is
unconditionally disabled until those independent mechanisms are reviewed.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import Enum
import os
import sys
from typing import Any


class RootIdentityStatus(str, Enum):
    OBSERVED_UNVERIFIED = "OBSERVED_UNVERIFIED"
    REJECTED = "REJECTED"
    UNAVAILABLE = "UNAVAILABLE"


class RootIdentityCode(str, Enum):
    INVALID_HANDLE = "INVALID_HANDLE"
    PLATFORM_UNSUPPORTED = "PLATFORM_UNSUPPORTED"
    HANDLE_METADATA_UNAVAILABLE = "HANDLE_METADATA_UNAVAILABLE"
    NOT_DIRECTORY = "NOT_DIRECTORY"
    REPARSE_POINT = "REPARSE_POINT"
    OBSERVATION_FAILED = "OBSERVATION_FAILED"
    SAFE_ACQUISITION_UNAVAILABLE = "SAFE_ACQUISITION_UNAVAILABLE"
    REAL_AUTHORIZATION_DISABLED = "REAL_AUTHORIZATION_DISABLED"


class RealRootAuthorizationStatus(str, Enum):
    DENIED = "DENIED"


@dataclass(frozen=True)
class ObservedDirectoryIdentity:
    """Windows metadata observed from a handle, not a trusted identity pin."""

    volume_serial: int
    file_index: int
    attributes: int
    hardlink_count: int


@dataclass(frozen=True)
class RootIdentityResult:
    status: RootIdentityStatus
    identity: ObservedDirectoryIdentity | None = None
    error_code: RootIdentityCode | None = None


class RootAcquisitionStatus(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class RootHandleAcquisitionResult:
    """Fail-closed acquisition result; no path was opened by this provider."""

    status: RootAcquisitionStatus
    handle: None = None
    identity: None = None
    error_code: RootIdentityCode = RootIdentityCode.SAFE_ACQUISITION_UNAVAILABLE


@dataclass(frozen=True)
class RealRootAuthorizationResult:
    status: RealRootAuthorizationStatus
    error_code: RootIdentityCode


if os.name == "nt":
    _ULONG = ctypes.c_ulong
    _HANDLE = ctypes.c_void_p
    _FILE_ATTRIBUTE_DIRECTORY = 0x10
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x400

    class _FileTime(ctypes.Structure):
        _fields_ = [("low", _ULONG), ("high", _ULONG)]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("attributes", _ULONG),
            ("creation_time", _FileTime),
            ("last_access_time", _FileTime),
            ("last_write_time", _FileTime),
            ("volume_serial", _ULONG),
            ("size_high", _ULONG),
            ("size_low", _ULONG),
            ("link_count", _ULONG),
            ("file_index_high", _ULONG),
            ("file_index_low", _ULONG),
        ]


def _query_handle_metadata(handle: int) -> Any:
    """Return GetFileInformationByHandle data, or a sanitized OS failure."""
    if os.name != "nt" or sys.platform != "win32":
        raise OSError(RootIdentityCode.PLATFORM_UNSUPPORTED.value)
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        function = kernel32.GetFileInformationByHandle
        function.argtypes = [_HANDLE, ctypes.POINTER(_ByHandleFileInformation)]
        function.restype = ctypes.c_int
        info = _ByHandleFileInformation()
        if not function(_HANDLE(handle), ctypes.byref(info)):
            raise OSError(RootIdentityCode.HANDLE_METADATA_UNAVAILABLE.value)
        return info
    except OSError:
        raise
    except Exception:
        raise OSError(RootIdentityCode.HANDLE_METADATA_UNAVAILABLE.value) from None


def observe_directory_handle(handle: int) -> RootIdentityResult:
    """Observe a caller-owned directory HANDLE without taking ownership.

    The handle must already be open. This function does not inspect a path,
    acquire a root, or verify how the handle was obtained. A successful result
    is explicitly unverified and must never be used as an authorization token.
    """
    if type(handle) is not int or handle <= 0:
        return RootIdentityResult(
            RootIdentityStatus.REJECTED, error_code=RootIdentityCode.INVALID_HANDLE
        )
    if os.name != "nt" or sys.platform != "win32":
        return RootIdentityResult(
            RootIdentityStatus.UNAVAILABLE,
            error_code=RootIdentityCode.PLATFORM_UNSUPPORTED,
        )
    try:
        info = _query_handle_metadata(handle)
    except OSError as error:
        code = next(
            (item for item in RootIdentityCode if item.value == str(error)),
            RootIdentityCode.HANDLE_METADATA_UNAVAILABLE,
        )
        return RootIdentityResult(RootIdentityStatus.UNAVAILABLE, error_code=code)
    except Exception:
        return RootIdentityResult(
            RootIdentityStatus.UNAVAILABLE,
            error_code=RootIdentityCode.OBSERVATION_FAILED,
        )

    attributes = int(info.attributes)
    if not attributes & _FILE_ATTRIBUTE_DIRECTORY:
        return RootIdentityResult(
            RootIdentityStatus.REJECTED, error_code=RootIdentityCode.NOT_DIRECTORY
        )
    if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        return RootIdentityResult(
            RootIdentityStatus.REJECTED, error_code=RootIdentityCode.REPARSE_POINT
        )
    index = (int(info.file_index_high) << 32) | int(info.file_index_low)
    identity = ObservedDirectoryIdentity(
        volume_serial=int(info.volume_serial),
        file_index=index,
        attributes=attributes,
        hardlink_count=int(info.link_count),
    )
    return RootIdentityResult(RootIdentityStatus.OBSERVED_UNVERIFIED, identity=identity)


class WindowsRealRootAuthorizationProvider:
    """Explicit unavailable boundary; never grants real-data access."""

    def authorize(self, *_untrusted_evidence: object) -> RealRootAuthorizationResult:
        # Deliberately ignores caller-constructible claims, including observed
        # identities and schema-valid approval documents.
        return RealRootAuthorizationResult(
            RealRootAuthorizationStatus.DENIED,
            RootIdentityCode.REAL_AUTHORIZATION_DISABLED,
        )


class WindowsRootHandleAcquisitionProvider:
    """Unavailable root opener until safe traversal and approval are established.

    The interface accepts path/policy/approval inputs for future integration,
    but deliberately does not coerce, normalize, inspect, or open them. In
    particular, this implementation cannot be used as a path-based fallback.
    """

    def acquire(
        self,
        supplied_path: str | os.PathLike[str] | object,
        policy_selected_root: object,
        approval_evidence: object | None = None,
    ) -> RootHandleAcquisitionResult:
        del supplied_path, policy_selected_root, approval_evidence
        return RootHandleAcquisitionResult(RootAcquisitionStatus.UNAVAILABLE)
