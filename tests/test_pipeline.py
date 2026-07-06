import logging
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
    transcriber = _SpyTranscriber("é texto cru né")
    cleaner = _SpyCleaner("Texto cru.")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=True)

    result = pipeline.run(Path("rec.wav"))

    assert cleaner.calls == ["é texto cru né"]
    assert injector.calls == ["Texto cru."]
    assert result == "Texto cru."


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


class _ExplodingCleaner:
    def clean(self, text):
        raise RuntimeError("groq fora do ar")


def test_erro_na_limpeza_cai_para_transcricao_crua_e_loga(caplog):
    transcriber = _SpyTranscriber("texto ditado sem pontuação")
    injector = _SpyInjector()
    pipeline = DictationPipeline(
        transcriber, _ExplodingCleaner(), injector, enable_cleanup=True
    )

    with caplog.at_level(logging.ERROR, logger="sagmowhisper"):
        result = pipeline.run(Path("rec.wav"))

    assert injector.calls == ["texto ditado sem pontuação"]
    assert result == "texto ditado sem pontuação"
    assert "Limpeza falhou" in caplog.text


def test_limpeza_bem_sucedida_loga_antes_e_depois(caplog):
    transcriber = _SpyTranscriber("oi rose tudo bem")
    cleaner = _SpyCleaner("Oi, Rose, tudo bem?")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=True)

    with caplog.at_level(logging.INFO, logger="sagmowhisper"):
        pipeline.run(Path("rec.wav"))

    assert "oi rose tudo bem" in caplog.text
    assert "Oi, Rose, tudo bem?" in caplog.text


def test_resposta_do_editor_e_aceita_sem_guard():
    # Decisão da spec: sem guard automático — o editor reescreve livremente.
    transcriber = _SpyTranscriber("quanto é dois mais dois")
    cleaner = _SpyCleaner("Quanto é dois mais dois?")
    injector = _SpyInjector()
    pipeline = DictationPipeline(transcriber, cleaner, injector, enable_cleanup=True)

    result = pipeline.run(Path("rec.wav"))

    assert injector.calls == ["Quanto é dois mais dois?"]
    assert result == "Quanto é dois mais dois?"
