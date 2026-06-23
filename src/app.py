from groq import Groq
from pynput import keyboard

from src.audio_recorder import AudioRecorder
from src.cleaner import Cleaner
from src.config import Config
from src.pipeline import DictationPipeline
from src.text_injector import TextInjector
from src.transcriber import Transcriber


class VozApp:
    def __init__(self, config: Config):
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

    def on_press(self, key):
        if key == self._hotkey and not self._recording:
            self._recording = True
            self._recorder.start()
            print("🎙️  Gravando...")

    def on_release(self, key):
        if key == self._hotkey and self._recording:
            self._recording = False
            self._handle_recording()

    def _handle_recording(self):
        print("⏳ Transcrevendo...")
        audio_path = self._recorder.stop()
        text = self._pipeline.run(audio_path)
        print(f"✅ {text}" if text else "⚠️  Nada captado.")

    def run(self):
        print(f"Voz ativo. Segure {self._config.hotkey.upper()} para ditar.")
        with keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        ) as listener:
            listener.join()


def main():
    VozApp(Config.from_env()).run()


if __name__ == "__main__":
    main()
