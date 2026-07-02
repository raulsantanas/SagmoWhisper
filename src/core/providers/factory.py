import os
from collections.abc import Mapping

from src.core import secrets
from src.core.config import Config
from src.core.providers import (
    groq_provider,
    local_provider,
    openai_provider,
)
from src.core.providers.base import PROVIDER_CATALOG, TranscriptionError

_ENV_KEY_VARS = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY"}
_MODULES = {
    "groq": groq_provider,
    "openai": openai_provider,
    "local": local_provider,
}


def resolve_api_key(
    provider: str, env: Mapping | None = None
) -> str | None:
    env = os.environ if env is None else env
    env_var = _ENV_KEY_VARS.get(provider)
    if env_var and env.get(env_var):
        return env[env_var]
    return secrets.get_api_key(provider)


def _provider_info(provider: str):
    info = PROVIDER_CATALOG.get(provider)
    if info is None:
        raise TranscriptionError(
            provider, "provider desconhecido; edite Configurações…"
        )
    return info


def build_components(config: Config):
    """-> (transcriber, cleaner | None); cleaner None = sem limpeza."""
    info = _provider_info(config.provider)
    api_key = None
    if info.needs_api_key:
        api_key = resolve_api_key(config.provider)
        if not api_key:
            raise TranscriptionError(
                config.provider,
                "API key ausente. Configure em Configurações…",
            )
    return (
        _build_transcriber(config, api_key),
        _build_cleaner(config, api_key, info),
    )


def _build_transcriber(config: Config, api_key: str | None):
    if config.provider == "local":
        return local_provider.LocalTranscriber(
            config.transcription_model, config.language
        )
    module = _MODULES[config.provider]
    transcriber_cls = (
        groq_provider.GroqTranscriber
        if config.provider == "groq"
        else openai_provider.OpenAITranscriber
    )
    return transcriber_cls(
        module.make_client(api_key),
        config.transcription_model,
        config.language,
    )


def _build_cleaner(config: Config, api_key: str | None, info):
    if not config.enable_cleanup or not info.cleanup_models:
        return None
    if config.provider == "groq":
        return groq_provider.GroqCleaner(
            groq_provider.make_client(api_key), config.cleanup_model
        )
    return openai_provider.OpenAICleaner(
        openai_provider.make_client(api_key), config.cleanup_model
    )


def test_connection(provider: str, api_key: str | None) -> None:
    _provider_info(provider)
    _MODULES[provider].test_connection(api_key or "")
