from src.core.providers.base import PROVIDER_CATALOG, TranscriptionError


def test_error_expoe_provider_e_detail():
    err = TranscriptionError("groq", "401 invalid key")
    assert err.provider == "groq"
    assert err.detail == "401 invalid key"
    assert str(err) == "groq: 401 invalid key"


def test_catalogo_tem_os_tres_providers():
    assert set(PROVIDER_CATALOG) == {"groq", "openai", "local"}
    assert [PROVIDER_CATALOG[k].label for k in ("groq", "openai", "local")] == [
        "Groq", "OpenAI", "Local"
    ]


def test_modelos_groq_verbatim_do_spec():
    info = PROVIDER_CATALOG["groq"]
    assert info.transcription_models == (
        "whisper-large-v3-turbo", "whisper-large-v3"
    )
    assert info.cleanup_models == ("llama-3.1-8b-instant",)
    assert info.needs_api_key is True


def test_modelos_openai_verbatim_do_spec():
    info = PROVIDER_CATALOG["openai"]
    assert info.transcription_models == ("whisper-1", "gpt-4o-transcribe")
    assert info.cleanup_models == ("gpt-4o-mini",)
    assert info.needs_api_key is True


def test_local_sem_key_e_sem_limpeza():
    info = PROVIDER_CATALOG["local"]
    assert info.transcription_models == ("small",)
    assert info.cleanup_models == ()
    assert info.needs_api_key is False
