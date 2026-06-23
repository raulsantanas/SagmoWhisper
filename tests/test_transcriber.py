from pathlib import Path

from src.transcriber import Transcriber


class _FakeResult:
    def __init__(self, text):
        self.text = text


class _FakeTranscriptions:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResult(self._text)


class _FakeAudio:
    def __init__(self, text):
        self.transcriptions = _FakeTranscriptions(text)


class _FakeClient:
    def __init__(self, text):
        self.audio = _FakeAudio(text)


def test_transcribe_returns_text(tmp_path):
    audio = tmp_path / "rec.wav"
    audio.write_bytes(b"fake-wav")
    client = _FakeClient("olá mundo")

    transcriber = Transcriber(client, "whisper-large-v3-turbo", "pt")
    result = transcriber.transcribe(audio)

    assert result == "olá mundo"


def test_transcribe_strips_whitespace(tmp_path):
    audio = tmp_path / "rec.wav"
    audio.write_bytes(b"fake-wav")
    client = _FakeClient("  texto com espaços  \n")

    transcriber = Transcriber(client, "whisper-large-v3-turbo", "pt")
    result = transcriber.transcribe(audio)

    assert result == "texto com espaços"


def test_transcribe_passes_model_and_language(tmp_path):
    audio = tmp_path / "rec.wav"
    audio.write_bytes(b"fake-wav")
    client = _FakeClient("ok")

    transcriber = Transcriber(client, "whisper-large-v3-turbo", "pt")
    transcriber.transcribe(Path(audio))

    call = client.audio.transcriptions.calls[0]
    assert call["model"] == "whisper-large-v3-turbo"
    assert call["language"] == "pt"
