"""Low-level Windows handle-relative file primitive; not authorization.

The caller must already hold a directory HANDLE. This module opens exactly
one child component relative to that handle, requests FILE_OPEN_REPARSE_POINT,
and returns the opened object handle. It rejects reparse points and files with
multiple hard links. It does not authenticate or approve the parent handle,
validate how that handle was obtained, enumerate directories, or authorize
research data. The real-data provider remains unconditionally disabled.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from enum import Enum
import os
import sys
from typing import Any


class HandlePrimitiveCode(str, Enum):
    PLATFORM_UNSUPPORTED = "PLATFORM_UNSUPPORTED"
    INVALID_CHILD_NAME = "INVALID_CHILD_NAME"
    INVALID_DIRECTORY_HANDLE = "INVALID_DIRECTORY_HANDLE"
    OPEN_FAILED = "OPEN_FAILED"
    REPARSE_POINT_REJECTED = "REPARSE_POINT_REJECTED"
    NOT_REGULAR_FILE = "NOT_REGULAR_FILE"
    HARDLINK_AMBIGUOUS = "HARDLINK_AMBIGUOUS"
    HANDLE_METADATA_UNAVAILABLE = "HANDLE_METADATA_UNAVAILABLE"
    HANDLE_READ_FAILED = "HANDLE_READ_FAILED"
    HANDLE_CLOSED = "HANDLE_CLOSED"


class WindowsHandlePrimitiveError(OSError):
    """Sanitized, stable failure from a native handle operation."""

    def __init__(self, code: HandlePrimitiveCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True)
class HandleObjectIdentity:
    """Identity observed from the open handle; metadata is not authorization."""

    volume_serial: int
    file_index: int
    hardlink_count: int


if os.name == "nt":
    _ULONG = ctypes.c_ulong
    _USHORT = ctypes.c_ushort
    _HANDLE = ctypes.c_void_p

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

    class _UnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", _USHORT),
            ("maximum_length", _USHORT),
            ("buffer", ctypes.c_wchar_p),
        ]

    class _ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("length", _ULONG),
            ("root_directory", _HANDLE),
            ("object_name", ctypes.POINTER(_UnicodeString)),
            ("attributes", _ULONG),
            ("security_descriptor", ctypes.c_void_p),
            ("security_quality_of_service", ctypes.c_void_p),
        ]

    class _IoStatusBlock(ctypes.Structure):
        _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]

    _FILE_ATTRIBUTE_DIRECTORY = 0x10
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    _FILE_SHARE_ALL = 0x1 | 0x2 | 0x4
    _SYNCHRONIZE = 0x00100000
    _FILE_READ_DATA = 0x1
    _FILE_READ_ATTRIBUTES = 0x80
    _FILE_OPEN = 1
    _FILE_NON_DIRECTORY_FILE = 0x40
    _FILE_SYNCHRONOUS_IO_NONALERT = 0x20
    _FILE_OPEN_REPARSE_POINT = 0x00200000
    _OBJ_CASE_INSENSITIVE = 0x40
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _windows_apis() -> tuple[Any, Any]:
    if os.name != "nt":
        raise WindowsHandlePrimitiveError(HandlePrimitiveCode.PLATFORM_UNSUPPORTED)
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        ntdll = ctypes.WinDLL("ntdll")
    except (AttributeError, OSError):
        raise WindowsHandlePrimitiveError(HandlePrimitiveCode.PLATFORM_UNSUPPORTED) from None
    return kernel32, ntdll


def _query_information(
    kernel32: Any,
    handle: int,
    failure_code: HandlePrimitiveCode = HandlePrimitiveCode.INVALID_DIRECTORY_HANDLE,
) -> _ByHandleFileInformation:
    information = _ByHandleFileInformation()
    function = kernel32.GetFileInformationByHandle
    function.argtypes = [_HANDLE, ctypes.POINTER(_ByHandleFileInformation)]
    function.restype = ctypes.c_int
    if not function(_HANDLE(handle), ctypes.byref(information)):
        raise WindowsHandlePrimitiveError(failure_code)
    return information


def _close_handle(kernel32: Any, handle: int) -> None:
    function = kernel32.CloseHandle
    function.argtypes = [_HANDLE]
    function.restype = ctypes.c_int
    function(_HANDLE(handle))


def _identity(information: _ByHandleFileInformation) -> HandleObjectIdentity:
    file_index = (int(information.file_index_high) << 32) | int(information.file_index_low)
    return HandleObjectIdentity(
        int(information.volume_serial), file_index, int(information.link_count)
    )


def _validate_single_component(name: str) -> None:
    if (
        not isinstance(name, str)
        or not name
        or name in {".", ".."}
        or any(char in name for char in ("\\", "/", ":", "\x00", "<", ">", '"', "|", "?", "*"))
        or any(ord(char) < 32 for char in name)
        or name.endswith((".", " "))
    ):
        raise WindowsHandlePrimitiveError(HandlePrimitiveCode.INVALID_CHILD_NAME)
    stem = name.split(".", 1)[0].upper()
    if stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} or stem in {
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }:
        raise WindowsHandlePrimitiveError(HandlePrimitiveCode.INVALID_CHILD_NAME)


class WindowsReadHandle:
    """Owns the returned file HANDLE and performs reads through that handle."""

    def __init__(self, handle: int, identity: HandleObjectIdentity) -> None:
        self._handle = handle
        self.identity = identity

    def read(self, size: int = 64 * 1024) -> bytes:
        if self._handle is None:
            raise WindowsHandlePrimitiveError(HandlePrimitiveCode.HANDLE_CLOSED)
        if type(size) is not int or size <= 0 or size > 1024 * 1024:
            raise ValueError("read size must be between 1 and 1048576 bytes")
        kernel32, _ = _windows_apis()
        read_file = kernel32.ReadFile
        read_file.argtypes = [
            _HANDLE,
            ctypes.c_void_p,
            _ULONG,
            ctypes.POINTER(_ULONG),
            ctypes.c_void_p,
        ]
        read_file.restype = ctypes.c_int
        buffer = ctypes.create_string_buffer(size)
        amount = _ULONG()
        if not read_file(
            _HANDLE(self._handle), buffer, size, ctypes.byref(amount), None
        ):
            raise WindowsHandlePrimitiveError(HandlePrimitiveCode.HANDLE_READ_FAILED)
        return buffer.raw[: amount.value]

    def close(self) -> None:
        if self._handle is not None:
            kernel32, _ = _windows_apis()
            _close_handle(kernel32, self._handle)
            self._handle = None

    def __enter__(self) -> "WindowsReadHandle":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def open_child_file_readonly(directory_handle: int, child_name: str) -> WindowsReadHandle:
    """Open a regular, single-link child relative to an already-open directory.

    The supplied handle must be a directory handle. Its authorization and the
    path used to obtain it are not verified here. The name must be one relative
    component. The opened file is read through its returned HANDLE, not by
    reopening a path. This primitive alone must never be used to authorize
    real-data access.
    """
    _validate_single_component(child_name)
    kernel32, ntdll = _windows_apis()
    parent_info = _query_information(kernel32, directory_handle)
    if (
        not parent_info.attributes & _FILE_ATTRIBUTE_DIRECTORY
        or parent_info.attributes & _FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise WindowsHandlePrimitiveError(HandlePrimitiveCode.INVALID_DIRECTORY_HANDLE)

    name_buffer = ctypes.create_unicode_buffer(child_name)
    name = _UnicodeString(
        len(child_name.encode("utf-16-le")),
        len(child_name.encode("utf-16-le")) + 2,
        ctypes.cast(name_buffer, ctypes.c_wchar_p),
    )
    attributes = _ObjectAttributes(
        ctypes.sizeof(_ObjectAttributes),
        _HANDLE(directory_handle),
        ctypes.pointer(name),
        _OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    io_status = _IoStatusBlock()
    opened = _HANDLE()
    create = ntdll.NtCreateFile
    create.argtypes = [
        ctypes.POINTER(_HANDLE),
        _ULONG,
        ctypes.POINTER(_ObjectAttributes),
        ctypes.POINTER(_IoStatusBlock),
        ctypes.c_void_p,
        _ULONG,
        _ULONG,
        _ULONG,
        _ULONG,
        ctypes.c_void_p,
        _ULONG,
    ]
    create.restype = ctypes.c_long
    status = create(
        ctypes.byref(opened),
        _FILE_READ_DATA | _FILE_READ_ATTRIBUTES | _SYNCHRONIZE,
        ctypes.byref(attributes),
        ctypes.byref(io_status),
        None,
        0,
        _FILE_SHARE_ALL,
        _FILE_OPEN,
        _FILE_NON_DIRECTORY_FILE | _FILE_SYNCHRONOUS_IO_NONALERT | _FILE_OPEN_REPARSE_POINT,
        None,
        0,
    )
    if status < 0 or opened.value in (None, _INVALID_HANDLE_VALUE):
        raise WindowsHandlePrimitiveError(HandlePrimitiveCode.OPEN_FAILED)

    try:
        information = _query_information(
            kernel32,
            int(opened.value),
            HandlePrimitiveCode.HANDLE_METADATA_UNAVAILABLE,
        )
        if information.attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise WindowsHandlePrimitiveError(HandlePrimitiveCode.REPARSE_POINT_REJECTED)
        if information.attributes & _FILE_ATTRIBUTE_DIRECTORY:
            raise WindowsHandlePrimitiveError(HandlePrimitiveCode.NOT_REGULAR_FILE)
        identity = _identity(information)
        if identity.hardlink_count != 1:
            raise WindowsHandlePrimitiveError(HandlePrimitiveCode.HARDLINK_AMBIGUOUS)
        return WindowsReadHandle(int(opened.value), identity)
    except Exception:
        _close_handle(kernel32, int(opened.value))
        raise


def is_supported_windows_runtime() -> bool:
    """Expose capability only; true does not indicate authorization."""
    return sys.platform == "win32" and os.name == "nt"
