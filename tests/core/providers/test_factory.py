import pytest

from src.core.config import DEFAULTS, Config
from src.core.providers import factory
from src.core.providers.base import TranscriptionError
from src.core.providers.groq_provider import GroqCleaner, GroqTranscriber
from src.core.providers.local_provider import LocalTranscriber
from src.core.providers.openai_provider import (
    OpenAICleaner,
    OpenAITranscriber,
)


def _cfg(**overrides) -> Config:
    return Config(**{**DEFAULTS, **overrides})


def test_resolve_api_key_env_vence_keychain(monkeypatch):
    monkeypatch.setattr(
        factory.secrets, "get_api_key", lambda p: "do_keychain"
    )
    assert (
        factory.resolve_api_key("groq", env={"GROQ_API_KEY": "do_env"})
        == "do_env"
    )


def test_resolve_api_key_cai_no_keychain(monkeypatch):
    monkeypatch.setattr(
        factory.secrets, "get_api_key", lambda p: "do_keychain"
    )
    assert factory.resolve_api_key("openai", env={}) == "do_keychain"


def test_resolve_api_key_local_nao_tem_env_var(monkeypatch):
    monkeypatch.setattr(factory.secrets, "get_api_key", lambda p: None)
    assert factory.resolve_api_key("local", env={}) is None


def test_build_groq(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    transcriber, cleaner = factory.build_components(_cfg())
    assert isinstance(transcriber, GroqTranscriber)
    assert isinstance(cleaner, GroqCleaner)


def test_build_openai(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "sk_x")
    transcriber, cleaner = factory.build_components(
        _cfg(
            provider="openai",
            transcription_model="whisper-1",
            cleanup_model="gpt-4o-mini",
        )
    )
    assert isinstance(transcriber, OpenAITranscriber)
    assert isinstance(cleaner, OpenAICleaner)


def test_build_local_sem_key_e_sem_cleaner(monkeypatch):
    monkeypatch.setattr(
        factory, "resolve_api_key", lambda p: 1 / 0
    )  # não pode ser chamada
    transcriber, cleaner = factory.build_components(
        _cfg(provider="local", transcription_model="small")
    )
    assert isinstance(transcriber, LocalTranscriber)
    assert cleaner is None


def test_build_cleanup_desligado_vira_none(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    _, cleaner = factory.build_components(_cfg(enable_cleanup=False))
    assert cleaner is None


def test_build_sem_key_levanta_erro_com_dica(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: None)
    with pytest.raises(TranscriptionError) as exc:
        factory.build_components(_cfg())
    assert "Configurações" in exc.value.detail


def test_test_connection_despacha_para_o_provider(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        factory.groq_provider,
        "test_connection",
        lambda key: chamadas.append(("groq", key)),
    )
    factory.test_connection("groq", "gsk_x")
    assert chamadas == [("groq", "gsk_x")]


def test_build_components_provider_desconhecido_erro_tipado():
    with pytest.raises(TranscriptionError) as exc:
        factory.build_components(_cfg(provider="inexistente"))
    assert "inexistente" in str(exc.value)
    assert type(exc.value) is TranscriptionError


def test_test_connection_provider_desconhecido_erro_tipado():
    with pytest.raises(TranscriptionError) as exc:
        factory.test_connection("inexistente", "chave")
    assert "inexistente" in str(exc.value)
    assert type(exc.value) is TranscriptionError
