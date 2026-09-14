"""Host-independent contracts for paper-store platform dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.product import platform_file_io


class FakeMsvcrt:
    LK_LOCK = 11
    LK_UNLCK = 12

    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def locking(self, file_descriptor: int, mode: int, byte_count: int) -> None:
        self.calls.append((file_descriptor, mode, byte_count))


class FakeMoveFile:
    def __init__(self, result: int = 1) -> None:
        self.argtypes: list[object] = []
        self.restype: object = None
        self.result = result
        self.calls: list[tuple[str, str, int]] = []

    def __call__(self, source: str, target: str, flags: int) -> int:
        self.calls.append((source, target, flags))
        return self.result


class FakeKernel32:
    def __init__(self, move: FakeMoveFile) -> None:
        self.MoveFileExW = move


class FakeCtypes:
    c_wchar_p = object()
    c_uint32 = object()
    c_int = object()

    def __init__(self, move: FakeMoveFile) -> None:
        self.kernel32 = FakeKernel32(move)
        self.loaded: list[tuple[str, bool]] = []

    def WinDLL(self, name: str, *, use_last_error: bool) -> FakeKernel32:
        self.loaded.append((name, use_last_error))
        return self.kernel32

    def get_last_error(self) -> int:
        return 5

    def FormatError(self, error: int) -> str:
        return f"error {error}"


class FakeFcntl:
    LOCK_EX = 21
    LOCK_UN = 22

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def flock(self, file_descriptor: int, operation: int) -> None:
        self.calls.append((file_descriptor, operation))


def test_platform_dispatch_is_explicit_and_fails_closed() -> None:
    assert isinstance(
        platform_file_io.platform_file_operations("nt"),
        platform_file_io.WindowsFileOperations,
    )
    assert isinstance(
        platform_file_io.platform_file_operations("posix"),
        platform_file_io.PosixFileOperations,
    )
    with pytest.raises(platform_file_io.PlatformFileIOError, match="unsupported"):
        platform_file_io.platform_file_operations("unknown")


def test_windows_locking_retains_one_byte_blocking_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    module = FakeMsvcrt()
    monkeypatch.setattr(platform_file_io, "_load_msvcrt", lambda: module)
    operations = platform_file_io.WindowsFileOperations()

    operations.lock(7)
    operations.unlock(7)

    assert module.calls == [(7, module.LK_LOCK, 1), (7, module.LK_UNLCK, 1)]


def test_windows_replace_retains_replace_and_write_through_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    move = FakeMoveFile()
    module = FakeCtypes(move)
    monkeypatch.setattr(platform_file_io, "_load_ctypes", lambda: module)

    platform_file_io.WindowsFileOperations().replace_durably(
        Path("staging.json"), Path("target.json")
    )

    assert module.loaded == [("kernel32", True)]
    assert move.calls == [("staging.json", "target.json", 0x1 | 0x8)]
    assert move.argtypes == [module.c_wchar_p, module.c_wchar_p, module.c_uint32]
    assert move.restype is module.c_int


def test_windows_replace_reports_native_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    module = FakeCtypes(FakeMoveFile(result=0))
    monkeypatch.setattr(platform_file_io, "_load_ctypes", lambda: module)

    with pytest.raises(OSError, match="error 5"):
        platform_file_io.WindowsFileOperations().replace_durably(
            Path("staging.json"), Path("target.json")
        )


def test_posix_locking_retains_exclusive_and_unlock_modes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = FakeFcntl()
    monkeypatch.setattr(platform_file_io, "_load_fcntl", lambda: module)
    operations = platform_file_io.PosixFileOperations()

    operations.lock(9)
    operations.unlock(9)

    assert module.calls == [(9, module.LOCK_EX), (9, module.LOCK_UN)]


def test_posix_replace_flushes_the_parent_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, Any]] = []

    def open_directory(path: Path, flags: int) -> int:
        calls.append(("open", (path, flags)))
        return 17

    monkeypatch.setattr(
        platform_file_io.os,
        "replace",
        lambda source, target: calls.append(("replace", (source, target))),
    )
    monkeypatch.setattr(platform_file_io.os, "open", open_directory)
    monkeypatch.setattr(
        platform_file_io.os, "fsync", lambda descriptor: calls.append(("fsync", descriptor))
    )
    monkeypatch.setattr(
        platform_file_io.os, "close", lambda descriptor: calls.append(("close", descriptor))
    )

    staging = Path("store") / "stage.json"
    target = Path("store") / "paper.json"
    platform_file_io.PosixFileOperations().replace_durably(staging, target)

    assert calls == [
        ("replace", (staging, target)),
        ("open", (target.parent, platform_file_io.os.O_RDONLY)),
        ("fsync", 17),
        ("close", 17),
    ]
