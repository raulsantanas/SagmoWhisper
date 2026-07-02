import sys
from types import SimpleNamespace

import pytest

from src.core.providers.base import TranscriptionError
from src.core.providers.local_provider import LocalTranscriber


def _fake_module(constructed: list):
    class FakeWhisperModel:
        def __init__(self, model_size):
            constructed.append(model_size)

        def transcribe(self, path, language):
            segments = [
                SimpleNamespace(text=" olá "),
                SimpleNamespace(text="mundo "),
            ]
            return segments, SimpleNamespace(language=language)

    return SimpleNamespace(WhisperModel=FakeWhisperModel)


def test_transcribe_junta_segmentos(monkeypatch, tmp_path):
    constructed = []
    monkeypatch.setitem(
        sys.modules, "faster_whisper", _fake_module(constructed)
    )
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    t = LocalTranscriber()
    assert t.transcribe(audio) == "olá mundo"
    assert constructed == ["small"]


def test_modelo_carrega_uma_vez_so(monkeypatch, tmp_path):
    constructed = []
    monkeypatch.setitem(
        sys.modules, "faster_whisper", _fake_module(constructed)
    )
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    t = LocalTranscriber()
    t.transcribe(audio)
    t.transcribe(audio)
    assert constructed == ["small"]


def test_sem_faster_whisper_vira_erro_tipado_com_instrucao(
    monkeypatch, tmp_path
):
    # sys.modules[nome] = None faz o import levantar ImportError
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber().transcribe(audio)
    assert exc.value.provider == "local"
    assert "sagmowhisper[local]" in exc.value.detail


def test_falha_do_modelo_vira_erro_tipado(monkeypatch, tmp_path):
    class Boom:
        def __init__(self, model_size):
            pass

        def transcribe(self, path, language):
            raise RuntimeError("cuda indisponível")

    monkeypatch.setitem(
        sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Boom)
    )
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber().transcribe(audio)
    assert exc.value.provider == "local"


def test_test_connection_ok_quando_instalado():
    from src.core.providers.local_provider import test_connection
    test_connection(find_spec=lambda name: object())


def test_test_connection_falha_quando_ausente():
    from src.core.providers.local_provider import test_connection
    with pytest.raises(TranscriptionError) as exc:
        test_connection(find_spec=lambda name: None)
    assert "sagmowhisper[local]" in exc.value.detail
