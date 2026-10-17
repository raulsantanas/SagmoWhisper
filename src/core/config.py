"""Config persistente em JSON; .env/env vars são override de dev (env vence).

API keys NUNCA entram neste JSON — vivem no Keychain (src/core/secrets.py).
"""
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.core import secrets

def default_config_path(
    platform: str = sys.platform, env: Mapping | None = None
) -> Path:
    if platform == "darwin":
        return (
            Path.home() / "Library" / "Application Support"
            / "SagmoWhisper" / "config.json"
        )
    env = os.environ if env is None else env
    base = Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "sagmowhisper" / "config.json"


DEFAULT_CONFIG_PATH = default_config_path()

HOTKEYS_SUPORTADAS = ("ctrl_r",) + tuple(f"f{n}" for n in range(1, 13))

DEFAULTS = {
    "provider": "groq",
    "transcription_model": "whisper-large-v3-turbo",
    "cleanup_model": "meta-llama/llama-4-scout-17b-16e-instruct",
    "language": "pt",
    "enable_cleanup": True,
    "hotkey": "ctrl_r",
    "sample_rate": 16000,
}

# 17/06/2026: Groq descontinuou os Llamas 3.1/3.3 no free tier (migrou para
# gpt-oss). 09/07/2026: Groq bloqueou gpt-oss e os demais chat models no
# nível da org (403 model_permission_blocked_org) — só llama-3.3-70b-versatile
# seguia disponível, voltando a ser o default.
# 19/09/2026: llama-3.3-70b-versatile foi REMOVIDO da plataforma (404
# model_not_found) e whisper-large-v3 (sem turbo) passou a ser bloqueado no
# allowlist do projeto (403). O default de cleanup migra para
# meta-llama/llama-4-scout-17b-16e-instruct e a auto-cura passa a cobrir também
# transcription_model — antes o crash escapava porque só cleanup era saneado.
_DEPRECATED_CLEANUP_MODELS = frozenset(
    {
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
    }
)

_DEPRECATED_TRANSCRIPTION_MODELS = frozenset({"whisper-large-v3"})

_ENV_PARSERS = {
    "PROVIDER": ("provider", str.lower),
    "TRANSCRIPTION_MODEL": ("transcription_model", str),
    "CLEANUP_MODEL": ("cleanup_model", str),
    "LANGUAGE": ("language", str),
    "ENABLE_CLEANUP": ("enable_cleanup", lambda v: v.lower() == "true"),
    "HOTKEY": ("hotkey", str.lower),
    "SAMPLE_RATE": ("sample_rate", int),
}


def _real_env() -> Mapping:
    load_dotenv()
    return os.environ


def _apply_env(data: dict, env: Mapping) -> None:
    for var, (field, parse) in _ENV_PARSERS.items():
        if env.get(var):
            data[field] = parse(env[var])


# Modelo depreciado por campo → migra para o default vigente. Vale para valor
# vindo do JSON OU de env var (o vetor real do crash de 19/09 foi env var).
_DEPRECATED_BY_FIELD = {
    "cleanup_model": _DEPRECATED_CLEANUP_MODELS,
    "transcription_model": _DEPRECATED_TRANSCRIPTION_MODELS,
}


def _heal_deprecated_models(data: dict) -> None:
    for field, deprecated in _DEPRECATED_BY_FIELD.items():
        if data[field] in deprecated:
            data[field] = DEFAULTS[field]


@dataclass
class Config:
    provider: str
    transcription_model: str
    cleanup_model: str
    language: str
    enable_cleanup: bool
    hotkey: str
    sample_rate: int

    @classmethod
    def load(
        cls, path: Path = DEFAULT_CONFIG_PATH, env: Mapping | None = None
    ) -> "Config":
        if env is None:
            env = _real_env()
        data = dict(DEFAULTS)
        if path.exists():
            data.update(json.loads(path.read_text()))
        _apply_env(data, env)
        _heal_deprecated_models(data)
        return cls(**data)

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False)
        )


def migrate_env_key_if_needed(
    path: Path = DEFAULT_CONFIG_PATH,
    env: Mapping | None = None,
    set_key=secrets.set_api_key,
) -> bool:
    """Primeira execução: importa GROQ_API_KEY do .env para o Keychain."""
    if path.exists():
        return False
    if env is None:
        env = _real_env()
    key = env.get("GROQ_API_KEY")
    if not key:
        return False
    set_key("groq", key)
    Config(**DEFAULTS).save(path)
    return True
