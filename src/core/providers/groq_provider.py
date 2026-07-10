from pathlib import Path

from groq import Groq

from src.core.providers.base import TranscriptionError, cleanup_messages


class GroqTranscriber:
    def __init__(self, client, model: str, language: str):
        self._client = client
        self._model = model
        self._language = language

    def transcribe(self, audio_path: Path) -> str:
        try:
            with open(audio_path, "rb") as audio_file:
                result = self._client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self._model,
                    language=self._language,
                )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        return result.text.strip()


class GroqCleaner:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def clean(self, text: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=cleanup_messages(text),
            )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        return completion.choices[0].message.content.strip()


def make_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def test_connection(api_key: str, client_factory=make_client) -> None:
    """Chamada mínima (lista modelos) para validar a key sem gastar tokens."""
    try:
        client_factory(api_key).models.list()
    except Exception as e:
        raise TranscriptionError("groq", str(e)) from e
