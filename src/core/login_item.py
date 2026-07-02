"""Estado "Abrir no login" via LaunchAgent: o arquivo existir É o estado.

Sem launchctl: RunAtLoad passa a valer no próximo login ao criar o plist
e deixa de valer ao removê-lo. Nenhum campo novo no config.json.
"""
import plistlib
import sys
from pathlib import Path

AGENT_LABEL = "com.raulsantana.sagmowhisper"
AGENT_PATH = (
    Path.home() / "Library" / "LaunchAgents" / f"{AGENT_LABEL}.plist"
)
APP_BINARY = Path(
    "/Applications/SagmoWhisper.app/Contents/MacOS/SagmoWhisper"
)


def plist_xml(binary: Path = APP_BINARY) -> str:
    data = {
        "Label": AGENT_LABEL,
        "ProgramArguments": [str(binary)],
        "RunAtLoad": True,
    }
    return plistlib.dumps(data, sort_keys=True).decode()


def is_enabled(path: Path = AGENT_PATH) -> bool:
    return path.exists()


def app_installed(binary: Path = APP_BINARY) -> bool:
    return binary.exists()


def enable(path: Path = AGENT_PATH, binary: Path = APP_BINARY) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist_xml(binary))


def disable(path: Path = AGENT_PATH) -> None:
    path.unlink(missing_ok=True)


def _cli(
    args: list, path: Path = AGENT_PATH, binary: Path = APP_BINARY
) -> int:
    if args == ["enable"]:
        enable(path, binary)
        return 0
    if args == ["disable"]:
        disable(path)
        return 0
    if args == ["status"]:
        print("enabled" if is_enabled(path) else "disabled")
        return 0
    print("uso: python -m src.core.login_item enable|disable|status")
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli(sys.argv[1:]))
