import os
from pathlib import Path


class AlreadyRunningError(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def acquire_lock(lock_path: Path) -> None:
    if lock_path.exists():
        content = lock_path.read_text().strip()
        if content.isdigit() and _pid_alive(int(content)):
            raise AlreadyRunningError(
                f"SagmoWhisper já está rodando (PID {content})."
            )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()))


def release_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)
