import signal
import sys
import threading

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import (
    NSDate,
    NSObject,
    NSRunLoop,
    NSUserNotification,
    NSUserNotificationCenter,
)
from groq import Groq
from pynput import keyboard

from src.audio_recorder import AudioRecorder
from src.cleaner import Cleaner
from src.config import Config
from src.pipeline import DictationPipeline
from src.text_injector import TextInjector
from src.transcriber import Transcriber
from src.waveform_overlay import WaveformOverlay

ICON_IDLE = "🎙️"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"


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
        self._app._set_title(ICON_IDLE)


class VozMenuBar:
    def __init__(self, config: Config):
        self._config = config
        self._recording = False
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
        quit_item = (
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Sair", "terminate:", "q"
            )
        )
        menu.addItem_(quit_item)
        self._status_item.setMenu_(menu)

    def run(self):
        run_loop = NSRunLoop.currentRunLoop()
        while True:
            run_loop.runUntilDate_(
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )

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
        audio_path = self._recorder.stop()
        try:
            self._pipeline.run(audio_path)
        except Exception as e:
            print(f"Erro na transcrição: {e}")
            self._show_notification("Voz — Erro", str(e))
        finally:
            self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
                "finishRecordingOnMainThread", None, False
            )

    def _show_notification(self, title: str, message: str):
        notification = NSUserNotification.alloc().init()
        notification.setTitle_(title)
        notification.setInformativeText_(message)
        NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(
            notification
        )


def main():
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory
    )
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    VozMenuBar(Config.from_env()).run()


if __name__ == "__main__":
    main()
