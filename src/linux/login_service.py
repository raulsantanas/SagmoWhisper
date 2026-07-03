"""Abrir no login via systemd user unit (espelho do login_item do macOS).

ExecStart precisa de caminho ABSOLUTO (%h = home): systemd não herda o
PATH do shell do usuário.
"""
import subprocess
from pathlib import Path

UNIT_NAME = "sagmowhisper.service"
UNIT_PATH = Path.home() / ".config" / "systemd" / "user" / UNIT_NAME


def unit_text() -> str:
    return (
        "[Unit]\n"
        "Description=SagmoWhisper — ditado por voz (segure F8)\n"
        "\n"
        "[Service]\n"
        "ExecStart=%h/.local/bin/sagmowhisper run\n"
        "Restart=on-failure\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def enable(path: Path = UNIT_PATH, run=subprocess.run) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(unit_text())
    run(["systemctl", "--user", "daemon-reload"], check=False)
    run(["systemctl", "--user", "enable", UNIT_NAME], check=False)


def disable(path: Path = UNIT_PATH, run=subprocess.run) -> None:
    run(["systemctl", "--user", "disable", UNIT_NAME], check=False)
    path.unlink(missing_ok=True)
    run(["systemctl", "--user", "daemon-reload"], check=False)


def is_enabled(run=subprocess.run) -> bool:
    result = run(
        ["systemctl", "--user", "is-enabled", UNIT_NAME],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0
