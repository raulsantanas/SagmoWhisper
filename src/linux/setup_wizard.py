"""Assistente de configuração no terminal (Linux). Chave SÓ no cofre."""
from getpass import getpass
from pathlib import Path

from src.core import secrets
from src.core.config import DEFAULT_CONFIG_PATH, DEFAULTS, Config
from src.core.providers.base import PROVIDER_CATALOG, ProviderInfo
from src.linux import login_service


def _ask_provider(ask) -> str:
    options = "/".join(PROVIDER_CATALOG)
    while True:
        answer = (
            ask(f"Provider [{options}] (Enter = groq): ").strip().lower()
            or "groq"
        )
        if answer in PROVIDER_CATALOG:
            return answer


def _ask_yes(ask, prompt: str) -> bool:
    return ask(f"{prompt} [S/n]: ").strip().lower() != "n"


def _store_key(info: ProviderInfo, ask_secret, set_key, echo) -> None:
    key = ask_secret(
        f"Chave de API do {info.label} (não aparece ao digitar): "
    ).strip()
    if key:
        set_key(info.key, key)
    else:
        echo(
            "⚠️  Sem chave o ditado vai falhar — rode "
            "`sagmowhisper setup` de novo quando tiver a chave."
        )


def _build_config(info: ProviderInfo, enable_cleanup: bool) -> Config:
    data = dict(DEFAULTS)
    data["provider"] = info.key
    data["transcription_model"] = info.transcription_models[0]
    if info.cleanup_models:
        data["cleanup_model"] = info.cleanup_models[0]
    data["enable_cleanup"] = enable_cleanup
    return Config(**data)


def run_setup(
    ask=input,
    ask_secret=getpass,
    echo=print,
    set_key=secrets.set_api_key,
    config_path: Path = DEFAULT_CONFIG_PATH,
    login=login_service,
) -> None:
    info = PROVIDER_CATALOG[_ask_provider(ask)]
    if info.needs_api_key:
        _store_key(info, ask_secret, set_key, echo)
    cleanup = bool(info.cleanup_models) and _ask_yes(
        ask, "Ativar limpeza do texto (remove hesitações)?"
    )
    _build_config(info, cleanup).save(config_path)
    if _ask_yes(ask, "Abrir o SagmoWhisper sozinho no login?"):
        login.enable()
    else:
        login.disable()
    echo("✓ Configuração salva. Agora rode: sagmowhisper run")
