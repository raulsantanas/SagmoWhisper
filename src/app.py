import threading

import rumps
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from groq import Groq
from pynput import keyboard

from src.audio_recorder import AudioRecorder
from src.cleaner import Cleaner
from src.config import Config
from src.pipeline import DictationPipeline
from src.text_injector import TextInjector
from src.transcriber import Transcriber

ICON_IDLE = "🎙️"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"


class VozMenuBar(rumps.App):
    def __init__(self, config: Config):
        super().__init__(ICON_IDLE, quit_button="Sair")
        self._config = config
        self._recording = False
        client = Groq(api_key=config.groq_api_key)
        self._recorder = AudioRecorder(config.sample_rate)
        self._pipeline = DictationPipeline(
            Transcriber(client, config.transcription_model, config.language),
            Cleaner(client, config.cleanup_model),
            TextInjector(),
            config.enable_cleanup,
        )
        self._hotkey = getattr(keyboard.Key, config.hotkey)
        self._listener_thread = threading.Thread(
            target=self._start_listener, daemon=True
        )
        self._listener_thread.start()

    def _start_listener(self):
        with keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        ) as listener:
            listener.join()

    def _on_press(self, key):
        if key == self._hotkey and not self._recording:
            self._recording = True
            self.title = ICON_RECORDING
            self._recorder.start()

    def _on_release(self, key):
        if key == self._hotkey and self._recording:
            self._recording = False
            threading.Thread(target=self._handle_recording, daemon=True).start()

    def _handle_recording(self):
        self.title = ICON_PROCESSING
        audio_path = self._recorder.stop()
        self._pipeline.run(audio_path)
        self.title = ICON_IDLE


def main():
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory
    )
    VozMenuBar(Config.from_env()).run()


if __name__ == "__main__":
    main()
