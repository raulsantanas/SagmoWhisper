"""Entry point do Linux: sagmowhisper setup | run | login on/off/status.

Imports do runtime (pynput/áudio) são lazy dentro de _run(): --help,
setup e login precisam funcionar sem DISPLAY.
"""
import argparse
import sys
from pathlib import Path

from src.linux import login_service, session_check, setup_wizard

LOG_PATH = Path.home() / ".local" / "state" / "sagmowhisper" / "app.log"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sagmowhisper",
        description="Ditado por voz: segure F8, fale, solte — o texto "
        "aparece no cursor.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="assistente de configuração")
    sub.add_parser("run", help="inicia o ditado (segure F8 para falar)")
    login = sub.add_parser("login", help="abrir sozinho no login")
    login.add_argument("action", choices=["on", "off", "status"])
    return parser


def main(argv=None, platform: str = sys.platform) -> int:
    if platform == "darwin":
        print("No macOS use o app nativo: ./install.sh")
        return 1
    args = _parser().parse_args(argv)
    if args.command == "setup":
        setup_wizard.run_setup()
        return 0
    if args.command == "run":
        return _run()
    return _login(args.action)


def _login(action: str) -> int:
    if action == "on":
        login_service.enable()
        print("✓ ativado: o SagmoWhisper abre sozinho no login")
    elif action == "off":
        login_service.disable()
        print("✓ desativado")
    else:
        estado = "ativado" if login_service.is_enabled() else "desativado"
        print(f"abrir no login: {estado}")
    return 0


def _run() -> int:
    error = session_check.check_session()
    if error:
        print(error)
        return 1
    return _start_dictation()


def _start_dictation() -> int:  # pragma: no cover — exige X11 e microfone
    import atexit

    from pynput import keyboard

    from src.audio_recorder import AudioRecorder
    from src.core.app_logging import setup_logging
    from src.core.config import Config, default_config_path
    from src.core.config import migrate_env_key_if_needed
    from src.core.providers import factory
    from src.core.providers.base import TranscriptionError
    from src.core.single_instance import (
        AlreadyRunningError,
        acquire_lock,
        release_lock,
    )
    from src.hotkey import resolve_hotkey
    from src.linux.app import LinuxApp
    from src.pipeline import DictationPipeline
    from src.text_injector import TextInjector

    logger = setup_logging(LOG_PATH)
    lock_path = default_config_path().parent / "app.lock"
    try:
        acquire_lock(lock_path)
    except AlreadyRunningError as e:
        print(str(e))
        return 1
    atexit.register(release_lock, lock_path)
    migrate_env_key_if_needed()
    config = Config.load()
    try:
        transcriber, cleaner = factory.build_components(config)
    except TranscriptionError:
        print("Chave de API ausente ou inválida. Rode: sagmowhisper setup")
        return 1
    pipeline = DictationPipeline(
        transcriber, cleaner, TextInjector(), enable_cleanup=cleaner is not None
    )
    app = LinuxApp(
        recorder=AudioRecorder(config.sample_rate),
        pipeline=pipeline,
        hotkey=resolve_hotkey(config.hotkey),
        logger=logger,
    )
    print(f"SagmoWhisper pronto — segure {config.hotkey.upper()} para ditar. "
          "Ctrl+C para sair.")
    with keyboard.Listener(
        on_press=app.on_press, on_release=app.on_release
    ) as listener:
        listener.join()
    return 0
