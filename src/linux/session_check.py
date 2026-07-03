"""Pré-checagens da sessão Linux; retorna mensagem de erro pt-BR ou None."""
import os
import shutil
from collections.abc import Mapping

MSG_WAYLAND = (
    "Você está numa sessão Wayland, que bloqueia a captura global do F8.\n"
    "Na tela de login, clique na engrenagem (canto inferior direito) e\n"
    "escolha a sessão \"Ubuntu on Xorg\", depois entre de novo."
)
MSG_SEM_DISPLAY = (
    "O SagmoWhisper precisa de uma sessão gráfica para colar o texto\n"
    "no cursor — não funciona via SSH ou em servidor sem tela."
)
MSG_SEM_XCLIP = (
    "Falta o utilitário de clipboard. Rode ./install-linux.sh ou:\n"
    "  sudo apt install xclip"
)


def check_session(
    env: Mapping | None = None, which=shutil.which
) -> str | None:
    env = os.environ if env is None else env
    if env.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return MSG_WAYLAND
    if not env.get("DISPLAY"):
        return MSG_SEM_DISPLAY
    if not (which("xclip") or which("xsel")):
        return MSG_SEM_XCLIP
    return None
