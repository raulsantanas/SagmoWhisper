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

DEFAULTS = {
    "provider": "groq",
    "transcription_model": "whisper-large-v3-turbo",
    "cleanup_model": "llama-3.3-70b-versatile",
    "language": "pt",
    "enable_cleanup": True,
    "hotkey": "f8",
    "sample_rate": 16000,
}

# 17/06/2026: Groq descontinuou os Llamas 3.1/3.3 no free tier (migrou para
# gpt-oss). 09/07/2026: Groq bloqueou gpt-oss e os demais chat models no
# nível da org (403 model_permission_blocked_org) — só llama-3.3-70b-versatile
# segue disponível, voltando a ser o default.
_DEPRECATED_CLEANUP_MODELS = frozenset(
    {"openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.1-8b-instant"}
)

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
        if data["cleanup_model"] in _DEPRECATED_CLEANUP_MODELS:
            data["cleanup_model"] = DEFAULTS["cleanup_model"]
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
