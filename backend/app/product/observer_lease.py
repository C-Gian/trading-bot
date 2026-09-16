"""Single-writer lifetime lease for the automated prospective observer.

Per-file atomic locks serialise individual writes, but they do not establish that only
one observer is scientifically active: two processes could each evaluate the same hourly
boundary and interleave correct-looking writes.  This lease is held for the observer's
whole lifetime, so a second instance cannot evaluate the market or write evidence at all.

Ownership is decided by an ordinary non-blocking OS file lock through the existing
platform abstraction.  A stale PID heuristic is never the authority: the operating system
releases the lock when the owning handle closes, including on an unclean exit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, Self

from .platform_file_io import platform_file_operations

LEASE_VERSION = "PROSPECTIVE_SHADOW_OBSERVER_LEASE_V1"
CONTENDED_ERROR = "ANOTHER_OBSERVER_INSTANCE_ACTIVE"


class ObserverLeaseError(RuntimeError):
    """The scientific observer lease is owned by another process."""


class ObserverLease:
    """Exclusive lifetime ownership of the scientific observer role."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._handle: IO[bytes] | None = None

    @property
    def held(self) -> bool:
        return self._handle is not None

    def acquire(self) -> bool:
        """Take exclusive ownership, or report that another instance already holds it."""
        if self._handle is not None:
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if not platform_file_operations().try_lock(handle.fileno()):
                handle.close()
                return False
        except BaseException:
            handle.close()
            raise
        self._handle = handle
        return True

    def require(self) -> None:
        """Acquire the lease or fail closed with the governed contention reason."""
        if not self.acquire():
            raise ObserverLeaseError(CONTENDED_ERROR)

    def release(self) -> None:
        """Release ownership; the OS also releases it if the process dies uncleanly."""
        handle, self._handle = self._handle, None
        if handle is None:
            return
        try:
            handle.seek(0)
            platform_file_operations().unlock(handle.fileno())
        except OSError:
            pass
        finally:
            handle.close()

    def __enter__(self) -> Self:
        self.require()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()


__all__ = ["CONTENDED_ERROR", "LEASE_VERSION", "ObserverLease", "ObserverLeaseError"]
