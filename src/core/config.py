"""Config persistente em JSON; .env/env vars são override de dev (env vence).

API keys NUNCA entram neste JSON — vivem no Keychain (src/core/secrets.py).
"""
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.core import secrets

DEFAULT_CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "SagmoWhisper"
    / "config.json"
)

DEFAULTS = {
    "provider": "groq",
    "transcription_model": "whisper-large-v3-turbo",
    "cleanup_model": "llama-3.1-8b-instant",
    "language": "pt",
    "enable_cleanup": True,
    "hotkey": "f8",
    "sample_rate": 16000,
}

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
