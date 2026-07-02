from types import SimpleNamespace

import pytest
from openai import OpenAI

from src.core.providers.base import CLEANUP_SYSTEM_PROMPT, TranscriptionError
from src.core.providers.openai_provider import (
    OpenAICleaner,
    OpenAITranscriber,
    make_client,
)


class _FakeClient:
    def __init__(self, text="  olá mundo  ", fail=False):
        self.calls = []
        fake = self

        def create(**kwargs):
            fake.calls.append(kwargs)
            if fail:
                raise RuntimeError("401 invalid api key")
            return SimpleNamespace(
                text=text,
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=text))
                ],
            )

        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(create=create)
        )
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )


def test_transcribe_retorna_texto_limpo(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = OpenAITranscriber(_FakeClient(), "whisper-1", "pt")

    assert t.transcribe(audio) == "olá mundo"


def test_transcribe_passa_modelo_lingua_e_nome_do_arquivo(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    client = _FakeClient()
    OpenAITranscriber(client, "gpt-4o-transcribe", "pt").transcribe(audio)

    call = client.calls[0]
    assert call["model"] == "gpt-4o-transcribe"
    assert call["language"] == "pt"
    assert call["file"][0] == "fala.wav"


def test_transcribe_embrulha_falha_em_transcription_error(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = OpenAITranscriber(_FakeClient(fail=True), "m", "pt")

    with pytest.raises(TranscriptionError) as exc:
        t.transcribe(audio)
    assert exc.value.provider == "openai"
    assert "401" in exc.value.detail


def test_clean_usa_prompt_e_temperatura_baixa():
    client = _FakeClient(text="texto corrigido")
    result = OpenAICleaner(client, "gpt-4o-mini").clean("texto bruto")

    assert result == "texto corrigido"
    call = client.calls[0]
    assert call["temperature"] == 0.2
    assert call["messages"][0] == {
        "role": "system",
        "content": CLEANUP_SYSTEM_PROMPT,
    }
    assert call["messages"][1] == {"role": "user", "content": "texto bruto"}


def test_clean_embrulha_falha_em_transcription_error():
    c = OpenAICleaner(_FakeClient(fail=True), "m")
    with pytest.raises(TranscriptionError) as exc:
        c.clean("x")
    assert exc.value.provider == "openai"


def test_test_connection_ok_nao_levanta():
    from src.core.providers.openai_provider import test_connection

    fake = SimpleNamespace(models=SimpleNamespace(list=lambda: []))
    test_connection("sk_x", client_factory=lambda key: fake)


def test_test_connection_falha_vira_transcription_error():
    from src.core.providers.openai_provider import test_connection

    def boom(key):
        raise RuntimeError("rede fora")

    with pytest.raises(TranscriptionError) as exc:
        test_connection("sk_x", client_factory=boom)
    assert exc.value.provider == "openai"


def test_make_client_retorna_cliente_openai():
    client = make_client("sk_x")
    assert isinstance(client, OpenAI)
