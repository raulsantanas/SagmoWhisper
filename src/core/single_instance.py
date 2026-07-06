import os
import subprocess
from pathlib import Path

_APP_PROCESS_MARKER = "SagmoWhisper"


class AlreadyRunningError(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def _pid_command(pid: int) -> str:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    return result.stdout.strip()


def _lock_holder_running(pid: int) -> bool:
    # PID vivo não basta: após crash/reboot o SO recicla PIDs e o lock
    # órfão apontaria para um processo qualquer, bloqueando o app para sempre.
    return _pid_alive(pid) and _APP_PROCESS_MARKER in _pid_command(pid)


def acquire_lock(lock_path: Path) -> None:
    if lock_path.exists():
        content = lock_path.read_text().strip()
        if content.isdigit() and _lock_holder_running(int(content)):
            raise AlreadyRunningError(
                f"SagmoWhisper já está rodando (PID {content})."
            )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()))


def release_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)
