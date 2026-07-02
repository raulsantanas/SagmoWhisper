import atexit
import signal
import subprocess
import sys
import threading
from pathlib import Path

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject, NSTimer
from groq import Groq
from pynput import keyboard

from src.audio_recorder import AudioRecorder
from src.cleaner import Cleaner
from src.config import Config
from src.core.app_logging import setup_logging
from src.core.single_instance import (
    AlreadyRunningError,
    acquire_lock,
    release_lock,
)
from src.pipeline import DictationPipeline
from src.text_injector import TextInjector
from src.transcriber import Transcriber
from src.waveform_overlay import WaveformOverlay

ICON_IDLE = "🎙️"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"
ICON_ERROR = "⚠️"

LOG_PATH = Path.home() / "Library" / "Logs" / "SagmoWhisper.log"
logger = setup_logging(LOG_PATH)

LOCK_PATH = (
    Path.home() / "Library" / "Application Support" / "SagmoWhisper" / "app.lock"
)


class MainThreadDispatcher(NSObject):
    def initWithApp_(self, app):
        self = objc.super(MainThreadDispatcher, self).init()
        if self is not None:
            self._app = app
        return self

    def startRecordingOnMainThread(self):
        self._app._main_start_recording()

    def stopRecordingOnMainThread(self):
        self._app._main_stop_recording()

    def setProcessingOnMainThread(self):
        self._app._set_title(ICON_PROCESSING)

    def finishRecordingOnMainThread(self):
        self._app._overlay.hide()
        if not self._app._had_error:
            self._app._set_title(ICON_IDLE)
            self._app._error_item.setHidden_(True)

    def showErrorOnMainThread_(self, message):
        self._app._show_error(str(message))

    def openLog_(self, sender):
        subprocess.run(["open", str(LOG_PATH)])


class VozMenuBar:
    def __init__(self, config: Config):
        self._config = config
        self._recording = False
        self._had_error = False
        self._overlay = WaveformOverlay()
        client = Groq(api_key=config.groq_api_key)
        self._recorder = AudioRecorder(
            config.sample_rate,
            sample_callback=self._overlay.update_bars,
        )
        self._pipeline = DictationPipeline(
            Transcriber(
                client, config.transcription_model, config.language
            ),
            Cleaner(client, config.cleanup_model),
            TextInjector(),
            config.enable_cleanup,
        )
        hotkey_str = config.hotkey.lower()
        try:
            self._hotkey = getattr(keyboard.Key, hotkey_str)
        except AttributeError:
            self._hotkey = keyboard.KeyCode.from_char(
                config.hotkey
            )

        self._dispatcher = (
            MainThreadDispatcher.alloc().initWithApp_(self)
        )
        self._status_item = self._create_status_item()
        self._set_title(ICON_IDLE)
        self._setup_menu()
        threading.Thread(
            target=self._start_listener, daemon=True
        ).start()

    def _create_status_item(self):
        status_bar = NSStatusBar.systemStatusBar()
        return status_bar.statusItemWithLength_(
            NSVariableStatusItemLength
        )

    def _set_title(self, title: str):
        self._status_item.button().setTitle_(title)

    def _setup_menu(self):
        menu = NSMenu.alloc().init()
        self._error_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "", None, ""
        )
        self._error_item.setHidden_(True)
        menu.addItem_(self._error_item)

        open_log_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Abrir log", "openLog:", ""
        )
        open_log_item.setTarget_(self._dispatcher)
        menu.addItem_(open_log_item)

        quit_item = (
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Sair", "terminate:", "q"
            )
        )
        menu.addItem_(quit_item)
        self._status_item.setMenu_(menu)

    def run(self):
        # NSRunLoop.runUntilDate_ processa timers/selectors mas NÃO despacha
        # eventos de clique do AppKit — o menu da barra ficava morto. Só o
        # event loop do NSApplication.run() entrega cliques ao status item.
        # O timer devolve controle ao Python a cada 0.5s para o handler de
        # SIGINT rodar (Ctrl+C em dev).
        NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            0.5, True, lambda timer: None
        )
        NSApplication.sharedApplication().run()

    def _start_listener(self):
        with keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        ) as listener:
            listener.join()

    def _on_press(self, key):
        if key == self._hotkey and not self._recording:
            self._recording = True
            self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
                "startRecordingOnMainThread", None, False
            )

    def _main_start_recording(self):
        self._set_title(ICON_RECORDING)
        self._overlay.show()
        self._recorder.start()

    def _on_release(self, key):
        if key == self._hotkey and self._recording:
            self._recording = False
            self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
                "stopRecordingOnMainThread", None, False
            )

    def _main_stop_recording(self):
        self._overlay.set_transcribing()
        threading.Thread(
            target=self._handle_recording, daemon=True
        ).start()

    def _handle_recording(self):
        self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setProcessingOnMainThread", None, False
        )
        try:
            audio_path = self._recorder.stop()
            self._had_error = False
            self._pipeline.run(audio_path)
        except Exception as e:
            logger.exception("Falha no ditado")
            self._notify_error(str(e))
        finally:
            self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
                "finishRecordingOnMainThread", None, False
            )

    def _show_error(self, message: str):
        self._had_error = True
        self._set_title(ICON_ERROR)
        self._error_item.setTitle_(f"Último erro: {message[:80]}")
        self._error_item.setHidden_(False)

    def _notify_error(self, message: str):
        self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showErrorOnMainThread:", message, False
        )


def main():
    try:
        acquire_lock(LOCK_PATH)
    except AlreadyRunningError as e:
        logger.error(str(e))
        sys.exit(1)
    atexit.register(release_lock, LOCK_PATH)
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory
    )
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    VozMenuBar(Config.from_env()).run()


if __name__ == "__main__":
    main()
