import pytest

from src.core.config import DEFAULTS, Config
from src.core.providers import factory
from src.core.resposta_duvida import AtendenteDeDuvida
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
    assert isinstance(transcriber.original, GroqTranscriber)
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
    assert isinstance(transcriber.original, OpenAITranscriber)
    assert isinstance(cleaner, OpenAICleaner)


def test_build_local_sem_key_e_sem_cleaner(monkeypatch):
    monkeypatch.setattr(
        factory, "resolve_api_key", lambda p: 1 / 0
    )  # não pode ser chamada
    transcriber, cleaner = factory.build_components(
        _cfg(provider="local", transcription_model="small")
    )
    assert isinstance(transcriber.original, LocalTranscriber)
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


def test_build_groq_leva_o_glossario_ao_transcriber(monkeypatch, tmp_path):
    from src.core import glossario

    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    monkeypatch.setattr(glossario, "CAMINHO_PADRAO", tmp_path / "nao_existe.json")
    transcriber, _ = factory.build_components(_cfg())

    assert transcriber.original._prompt == glossario.montar_prompt(
        glossario.GLOSSARIO_INICIAL
    )


def test_glossario_malformado_vira_transcription_error(monkeypatch, tmp_path):
    from src.core import glossario

    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    glossario.CAMINHO_PADRAO.write_text('{"termos": ["Claude",]}')

    with pytest.raises(TranscriptionError):
        factory.build_components(_cfg())


@pytest.mark.parametrize("provider", ["groq", "openai", "local"])
def test_todo_transcriber_sai_com_correcoes(monkeypatch, provider):
    from src.core.correcoes import TranscriberCorrigido

    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "k")
    transcriber, _ = factory.build_components(_cfg(provider=provider))

    assert isinstance(transcriber, TranscriberCorrigido)


def test_transcriber_da_factory_grava_registro_de_treino(monkeypatch):
    from src.core import registro_treino

    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "k")
    transcriber, _ = factory.build_components(_cfg())

    assert isinstance(transcriber.registro, registro_treino.RegistroTreino)


def test_groq_monta_atendente_de_duvida_com_a_voz(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    voz = object()

    atendente = factory.build_atendente_de_duvida(_cfg(provider="groq"), voz)

    assert isinstance(atendente, AtendenteDeDuvida)
    assert atendente.voz is voz


@pytest.mark.parametrize("provider", ["openai", "local"])
def test_sem_groq_nao_ha_atendente(monkeypatch, provider):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "sk_x")

    assert factory.build_atendente_de_duvida(_cfg(provider=provider), object()) is None
