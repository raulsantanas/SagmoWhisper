from pathlib import Path

from src.pipeline import DictationPipeline


class _SpyTranscriber:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def transcribe(self, audio_path):
        self.calls.append(audio_path)
        return self._text


class _SpyCleaner:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def clean(self, text):
        self.calls.append(text)
        return self._text


class _SpyInjector:
    def __init__(self):
        self.calls = []

    def inject(self, text):
        self.calls.append(text)


def test_cleanup_enabled_injects_cleaned_text():
    transcriber = _SpyTranscriber("texto cru")
    cleaner = _SpyCleaner("texto limpo")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=True)

    result = pipeline.run(Path("rec.wav"))

    assert cleaner.calls == ["texto cru"]
    assert injector.calls == ["texto limpo"]
    assert result == "texto limpo"


def test_cleanup_disabled_injects_raw_text_and_skips_cleaner():
    transcriber = _SpyTranscriber("texto cru")
    cleaner = _SpyCleaner("nunca usado")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=False)

    result = pipeline.run(Path("rec.wav"))

    assert cleaner.calls == []
    assert injector.calls == ["texto cru"]
    assert result == "texto cru"


def test_empty_transcription_skips_cleaner_and_injector():
    transcriber = _SpyTranscriber("   ")
    cleaner = _SpyCleaner("x")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=True)

    result = pipeline.run(Path("rec.wav"))

    assert cleaner.calls == []
    assert injector.calls == []
    assert result == ""


def test_cleanup_yielding_empty_text_skips_injector():
    transcriber = _SpyTranscriber("texto cru")
    cleaner = _SpyCleaner("   ")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=True)

    result = pipeline.run(Path("rec.wav"))

    assert injector.calls == []
    assert result == ""
