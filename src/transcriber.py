from pathlib import Path


class Transcriber:
    def __init__(self, client, model: str, language: str):
        self._client = client
        self._model = model
        self._language = language

    def transcribe(self, audio_path: Path) -> str:
        with open(audio_path, "rb") as audio_file:
            result = self._client.audio.transcriptions.create(
                file=(Path(audio_path).name, audio_file.read()),
                model=self._model,
                language=self._language,
            )
        return result.text.strip()
