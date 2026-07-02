from pathlib import Path

from src.core.providers.base import cleanup_reuses_dictated_words


class DictationPipeline:
    def __init__(self, transcriber, cleaner, injector, enable_cleanup: bool):
        self._transcriber = transcriber
        self._cleaner = cleaner
        self._injector = injector
        self._enable_cleanup = enable_cleanup

    def run(self, audio_path: Path) -> str:
        text = self._transcriber.transcribe(audio_path).strip()
        if not text:
            return ""
        return self._finalize(text)

    def _finalize(self, text: str) -> str:
        final_text = self._maybe_clean(text)
        if not final_text:
            return ""
        self._injector.inject(final_text)
        return final_text

    def _maybe_clean(self, text: str) -> str:
        if not self._enable_cleanup:
            return text
        cleaned = self._cleaner.clean(text).strip()
        if cleaned and not cleanup_reuses_dictated_words(text, cleaned):
            return text
        return cleaned
