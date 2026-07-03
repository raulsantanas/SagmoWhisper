"""Loop de ditado push-to-talk no Linux — sem AppKit, feedback no terminal."""
import logging


class LinuxApp:
    def __init__(self, recorder, pipeline, hotkey, echo=print, logger=None):
        self._recorder = recorder
        self._pipeline = pipeline
        self._hotkey = hotkey
        self._echo = echo
        self._logger = logger or logging.getLogger("sagmowhisper")
        self._recording = False

    def on_press(self, key):
        if key == self._hotkey and not self._recording:
            self._recording = True
            self._echo("🎙 gravando… (solte a tecla para transcrever)")
            self._recorder.start()

    def on_release(self, key):
        if key != self._hotkey or not self._recording:
            return
        self._recording = False
        self._transcribe()

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
