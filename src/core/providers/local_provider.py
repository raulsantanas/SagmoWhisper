"""faster-whisper é dependência OPCIONAL: import lazy para o app abrir sem ela."""
import importlib.util
from pathlib import Path

from src.core.providers.base import TranscriptionError

_INSTALL_HINT = (
    "faster-whisper não instalado. "
    "Instale com: pip install 'sagmowhisper[local]'"
)


class LocalTranscriber:
    def __init__(self, model_size: str = "small", language: str = "pt"):
        self._model_size = model_size
        self._language = language
        self._model = None

    def _load_model(self):
        # download automático do modelo no primeiro uso (aviso fica na UI)
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise TranscriptionError("local", _INSTALL_HINT) from e
        self._model = WhisperModel(self._model_size)
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        model = self._load_model()
        try:
            segments, _info = model.transcribe(
                str(audio_path), language=self._language
            )
            return " ".join(s.text.strip() for s in segments).strip()
        except Exception as e:
            raise TranscriptionError("local", str(e)) from e


def test_connection(
    api_key: str = "", find_spec=importlib.util.find_spec
) -> None:
    if find_spec("faster_whisper") is None:
        raise TranscriptionError("local", _INSTALL_HINT)
