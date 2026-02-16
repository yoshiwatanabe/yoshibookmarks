"""File locking utilities for concurrent access."""

import asyncio
import time
from pathlib import Path
from typing import Optional


class FileLockError(Exception):
    """File locking error."""

    pass


class FileLocker:
    """Context manager for file locking.

    Provides simple file locking for concurrent access control.
    Uses lock files (.lock suffix) to coordinate access.
    """

    def __init__(self, file_path: Path, timeout: float = 5.0):
        """Initialize file locker.

        Args:
            file_path: Path to the file to lock
            timeout: Maximum time to wait for lock acquisition (seconds)
        """
        self.file_path = file_path
        self.lock_path = Path(str(file_path) + ".lock")
        self.timeout = timeout
        self.acquired = False

    def __enter__(self) -> "FileLocker":
        """Acquire lock (synchronous context manager)."""
        self._acquire_lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        self._release_lock()
        return False

    async def __aenter__(self) -> "FileLocker":
        """Acquire lock (async context manager)."""
        await self._acquire_lock_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        self._release_lock()
        return False

    def _acquire_lock(self) -> None:
        """Acquire lock with timeout (synchronous)."""
        start_time = time.time()

        while True:
            try:
                # Attempt to create lock file exclusively
                self.lock_path.parent.mkdir(parents=True, exist_ok=True)

                # On Windows, we need a different approach
                if self.lock_path.exists():
                    # Check if lock is stale (older than timeout)
                    if time.time() - self.lock_path.stat().st_mtime > self.timeout * 2:
                        # Remove stale lock
                        self.lock_path.unlink(missing_ok=True)
                    else:
                        # Lock exists and is fresh
                        if time.time() - start_time > self.timeout:
                            raise FileLockError(
                                f"Could not acquire lock on {self.file_path} after {self.timeout}s"
                            )
                        time.sleep(0.1)
                        continue

                # Create lock file
                self.lock_path.touch()
                self.acquired = True
                return

            except Exception as e:
                if time.time() - start_time > self.timeout:
                    raise FileLockError(
                        f"Could not acquire lock on {self.file_path}: {e}"
                    ) from e
                time.sleep(0.1)

    async def _acquire_lock_async(self) -> None:
        """Acquire lock with timeout (async)."""
        start_time = time.time()

        while True:
            try:
                # Attempt to create lock file exclusively
                await asyncio.to_thread(self.lock_path.parent.mkdir, parents=True, exist_ok=True)

                if self.lock_path.exists():
                    # Check if lock is stale
                    stat = await asyncio.to_thread(self.lock_path.stat)
                    if time.time() - stat.st_mtime > self.timeout * 2:
                        # Remove stale lock
                        await asyncio.to_thread(self.lock_path.unlink, missing_ok=True)
                    else:
                        # Lock exists and is fresh
                        if time.time() - start_time > self.timeout:
                            raise FileLockError(
                                f"Could not acquire lock on {self.file_path} after {self.timeout}s"
                            )
                        await asyncio.sleep(0.1)
                        continue

                # Create lock file
                await asyncio.to_thread(self.lock_path.touch)
                self.acquired = True
                return

            except Exception as e:
                if time.time() - start_time > self.timeout:
                    raise FileLockError(
                        f"Could not acquire lock on {self.file_path}: {e}"
                    ) from e
                await asyncio.sleep(0.1)

    def _release_lock(self) -> None:
        """Release the lock."""
        if self.acquired:
            try:
                self.lock_path.unlink(missing_ok=True)
                self.acquired = False
            except Exception:
                # Best effort - ignore errors on cleanup
                pass
