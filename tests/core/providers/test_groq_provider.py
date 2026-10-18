from types import SimpleNamespace

import pytest
from groq import Groq

from src.core.providers.base import TranscriptionError
from src.core.providers.groq_provider import (
    GroqCleaner,
    GroqTranscriber,
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
    t = GroqTranscriber(_FakeClient(), "whisper-large-v3-turbo", "pt")

    assert t.transcribe(audio) == "olá mundo"


def test_transcribe_passa_modelo_lingua_e_nome_do_arquivo(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    client = _FakeClient()
    GroqTranscriber(client, "whisper-large-v3", "pt").transcribe(audio)

    call = client.calls[0]
    assert call["model"] == "whisper-large-v3"
    assert call["language"] == "pt"
    assert call["file"][0] == "fala.wav"


def test_transcribe_embrulha_falha_em_transcription_error(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = GroqTranscriber(_FakeClient(fail=True), "m", "pt")

    with pytest.raises(TranscriptionError) as exc:
        t.transcribe(audio)
    assert exc.value.provider == "groq"
    assert "401" in exc.value.detail


def test_clean_usa_prompt_e_temperatura_zero():
    client = _FakeClient(text="texto corrigido")
    result = GroqCleaner(client, "llama-3.1-8b-instant").clean("texto bruto")

    assert result == "texto corrigido"
    call = client.calls[0]
    assert call["temperature"] == 0
    from src.core.providers.base import cleanup_messages

    assert call["messages"] == cleanup_messages("texto bruto")


def test_clean_embrulha_falha_em_transcription_error():
    c = GroqCleaner(_FakeClient(fail=True), "m")
    with pytest.raises(TranscriptionError) as exc:
        c.clean("x")
    assert exc.value.provider == "groq"


def test_test_connection_ok_nao_levanta():
    from src.core.providers.groq_provider import test_connection

    fake = SimpleNamespace(models=SimpleNamespace(list=lambda: []))
    test_connection("gsk_x", client_factory=lambda key: fake)


def test_test_connection_falha_vira_transcription_error():
    from src.core.providers.groq_provider import test_connection

    def boom(key):
        raise RuntimeError("rede fora")

    with pytest.raises(TranscriptionError) as exc:
        test_connection("gsk_x", client_factory=boom)
    assert exc.value.provider == "groq"


def test_make_client_retorna_cliente_groq():
    client = make_client("gsk_x")
    assert isinstance(client, Groq)


def test_transcribe_envia_glossario_no_prompt(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    client = _FakeClient()
    GroqTranscriber(client, "m", "pt", prompt="Claude, README").transcribe(audio)

    assert client.calls[0]["prompt"] == "Claude, README"


def test_transcribe_sem_glossario_nao_envia_prompt(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    client = _FakeClient()
    GroqTranscriber(client, "m", "pt").transcribe(audio)

    assert "prompt" not in client.calls[0]


@pytest.mark.parametrize(
    "eco", ["Claude, Anthropic, Claude Code.", "Claude, Anthropic, Claude Code"]
)
def test_eco_do_glossario_em_silencio_nao_vira_texto(tmp_path, eco):
    # Em áudio curto ou silencioso, o Whisper às vezes devolve o prompt.
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = GroqTranscriber(
        _FakeClient(text=eco), "m", "pt",
        prompt="Claude, Anthropic, Claude Code, README",
    )

    assert t.transcribe(audio) == ""


def test_fala_curta_com_um_termo_do_glossario_passa(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = GroqTranscriber(
        _FakeClient(text="README"), "m", "pt",
        prompt="Claude, Anthropic, Claude Code, README",
    )

    assert t.transcribe(audio) == "README"
