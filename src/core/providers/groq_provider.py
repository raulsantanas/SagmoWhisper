from pathlib import Path

from groq import Groq

from src.core.providers.base import TranscriptionError, cleanup_messages


class GroqTranscriber:
    def __init__(self, client, model: str, language: str, prompt: str = ""):
        self._client = client
        self._model = model
        self._language = language
        self._prompt = prompt

    def transcribe(self, audio_path: Path) -> str:
        extras = {"prompt": self._prompt} if self._prompt else {}
        try:
            with open(audio_path, "rb") as audio_file:
                result = self._client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self._model,
                    language=self._language,
                    **extras,
                )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        texto = result.text.strip()
        return "" if self._e_eco_do_prompt(texto) else texto

    def _e_eco_do_prompt(self, texto: str) -> bool:
        # Em áudio curto ou silencioso o Whisper às vezes devolve o próprio
        # prompt. Dois ou mais termos seguidos da lista não são fala real.
        trecho = texto.rstrip(".!?… ")
        return bool(self._prompt) and ", " in trecho and trecho in self._prompt


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
