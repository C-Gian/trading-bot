"""Typed platform boundary for durable local paper-store file operations."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Protocol, cast


class PlatformFileIOError(RuntimeError):
    """The host does not provide a supported durable file-operation backend."""


class _MsvcrtModule(Protocol):
    LK_LOCK: int
    LK_NBLCK: int
    LK_UNLCK: int

    def locking(self, file_descriptor: int, mode: int, byte_count: int) -> None: ...


class _FcntlModule(Protocol):
    LOCK_EX: int
    LOCK_NB: int
    LOCK_UN: int

    def flock(self, file_descriptor: int, operation: int) -> None: ...


class _ForeignFunction(Protocol):
    argtypes: list[object]
    restype: object

    def __call__(self, source: str, target: str, flags: int) -> int: ...


class _Kernel32Library(Protocol):
    MoveFileExW: _ForeignFunction


class _CtypesModule(Protocol):
    c_wchar_p: object
    c_uint32: object
    c_int: object

    def WinDLL(self, name: str, *, use_last_error: bool) -> _Kernel32Library: ...

    def get_last_error(self) -> int: ...

    def FormatError(self, error: int) -> str: ...


def _load_msvcrt() -> _MsvcrtModule:
    return cast(_MsvcrtModule, importlib.import_module("msvcrt"))


def _load_fcntl() -> _FcntlModule:
    return cast(_FcntlModule, importlib.import_module("fcntl"))


def _load_ctypes() -> _CtypesModule:
    # Dynamic loading keeps platform-exclusive ctypes attributes outside the static
    # Linux stub surface while the protocol retains a checked call contract.
    return cast(_CtypesModule, importlib.import_module("ctypes"))


class PlatformFileOperations(Protocol):
    """Lock and durable-replacement operations selected from the host OS."""

    platform: str

    def lock(self, file_descriptor: int) -> None: ...

    def try_lock(self, file_descriptor: int) -> bool: ...

    def unlock(self, file_descriptor: int) -> None: ...

    def replace_durably(self, staging: Path, target: Path) -> None: ...


class WindowsFileOperations:
    platform = "nt"
    _MOVEFILE_REPLACE_EXISTING = 0x1
    _MOVEFILE_WRITE_THROUGH = 0x8

    def lock(self, file_descriptor: int) -> None:
        module = _load_msvcrt()
        module.locking(file_descriptor, module.LK_LOCK, 1)

    def try_lock(self, file_descriptor: int) -> bool:
        module = _load_msvcrt()
        try:
            module.locking(file_descriptor, module.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def unlock(self, file_descriptor: int) -> None:
        module = _load_msvcrt()
        module.locking(file_descriptor, module.LK_UNLCK, 1)

    def replace_durably(self, staging: Path, target: Path) -> None:
        module = _load_ctypes()
        kernel32 = module.WinDLL("kernel32", use_last_error=True)
        move = kernel32.MoveFileExW
        move.argtypes = [module.c_wchar_p, module.c_wchar_p, module.c_uint32]
        move.restype = module.c_int
        flags = self._MOVEFILE_REPLACE_EXISTING | self._MOVEFILE_WRITE_THROUGH
        if not move(str(staging), str(target), flags):
            error = module.get_last_error()
            raise OSError(error, module.FormatError(error), str(target))


class PosixFileOperations:
    platform = "posix"

    def lock(self, file_descriptor: int) -> None:
        module = _load_fcntl()
        module.flock(file_descriptor, module.LOCK_EX)

    def try_lock(self, file_descriptor: int) -> bool:
        module = _load_fcntl()
        try:
            module.flock(file_descriptor, module.LOCK_EX | module.LOCK_NB)
        except OSError:
            return False
        return True

    def unlock(self, file_descriptor: int) -> None:
        module = _load_fcntl()
        module.flock(file_descriptor, module.LOCK_UN)

    def replace_durably(self, staging: Path, target: Path) -> None:
        os.replace(staging, target)
        descriptor = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def platform_file_operations(platform_name: str | None = None) -> PlatformFileOperations:
    """Return the explicit backend for the host, or for a deterministic test target."""
    resolved = os.name if platform_name is None else platform_name
    if resolved == "nt":
        return WindowsFileOperations()
    if resolved == "posix":
        return PosixFileOperations()
    raise PlatformFileIOError(f"unsupported durable file-operation platform: {resolved}")


__all__ = [
    "PlatformFileIOError",
    "PlatformFileOperations",
    "PosixFileOperations",
    "WindowsFileOperations",
    "platform_file_operations",
]
