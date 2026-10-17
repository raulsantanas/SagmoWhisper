"""Loop de ditado push-to-talk no Linux — sem AppKit, feedback no terminal."""
import logging
import time

from src.core.gesto_tecla import GestoTecla


class LinuxApp:
    def __init__(self, recorder, pipeline, hotkey, echo=print, logger=None,
                 relogio=time.monotonic):
        self._recorder = recorder
        self._pipeline = pipeline
        self._echo = echo
        self._logger = logger or logging.getLogger("sagmowhisper")
        self._gesto = GestoTecla(
            tecla=hotkey,
            ao_iniciar=self._start,
            ao_concluir=self._transcribe,
            ao_cancelar=self._discard,
            relogio=relogio,
        )

    def on_press(self, key):
        self._gesto.pressionar(key)

    def on_release(self, key):
        self._gesto.soltar(key)

    def _start(self):
        self._echo("🎙 gravando… (solte a tecla para transcrever)")
        self._recorder.start()

    def _discard(self):
        self._recorder.stop()
        self._echo("(cancelado — atalho ou toque curto, nada colado)")

    def _transcribe(self):
        self._echo("⏳ transcrevendo…")
        try:
            text = self._pipeline.run(self._recorder.stop())
        except Exception as e:
            self._logger.exception("Falha no ditado")
            self._echo(f"⚠️  {e}")
            return
        if text:
            self._echo(f"✓ colado: {text[:60]}")
        else:
            self._echo("(gravação vazia — nada a colar)")
