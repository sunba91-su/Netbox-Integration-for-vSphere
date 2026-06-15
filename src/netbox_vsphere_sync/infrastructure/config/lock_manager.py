from __future__ import annotations

import os

from netbox_vsphere_sync.domain.constants import DEFAULT_LOCK_PATH
from netbox_vsphere_sync.domain.ports import LockManager


class PidLockManager(LockManager):
    def __init__(self, lock_path: str = DEFAULT_LOCK_PATH) -> None:
        self._lock_path = lock_path
        self._acquired = False

    def acquire(self) -> bool:
        if os.path.exists(self._lock_path):
            try:
                with open(self._lock_path) as f:
                    pid_str = f.read().strip()
                if pid_str:
                    pid = int(pid_str)
                    os.kill(pid, 0)
                    return False
            except (ValueError, OSError, ProcessLookupError):
                pass

        with open(self._lock_path, "w") as f:
            f.write(str(os.getpid()))

        self._acquired = True
        return True

    def release(self) -> None:
        if self._acquired:
            try:
                if os.path.exists(self._lock_path):
                    os.remove(self._lock_path)
            except Exception:
                pass
            self._acquired = False

    def is_locked(self) -> bool:
        if not os.path.exists(self._lock_path):
            return False
        try:
            with open(self._lock_path) as f:
                pid_str = f.read().strip()
            if pid_str:
                pid = int(pid_str)
                os.kill(pid, 0)
                return True
        except (ValueError, OSError, ProcessLookupError):
            pass
        return False
