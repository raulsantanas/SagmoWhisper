import atexit
import signal
import subprocess
import sys
import threading
from pathlib import Path

import objc
from AppKit import (
    NSAppearance,
    NSAppearanceNameDarkAqua,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSAttributedString,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject, NSTimer
from pynput import keyboard

from src.audio_recorder import AudioRecorder
from src.core.app_logging import setup_logging
from src.core.config import Config, migrate_env_key_if_needed, rotulo_hotkey
from src.core.gesto_tecla import GestoTecla
from src.core.menu_status import linha_de_status
from src.core.providers import factory
from src.core.providers.base import TranscriptionError
from src.core.single_instance import (
    AlreadyRunningError,
    acquire_lock,
    release_lock,
)
from src.hotkey import resolve_hotkey
from src.macos.cores import hex_to_nscolor
from src.macos.icone_barra import imagem_do_icone
from src.macos.indicador_voz import IndicadorVoz
from src.macos.settings_window import SettingsWindowController
from src.pipeline import DictationPipeline
from src.text_injector import TextInjector

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

    def cancelRecordingOnMainThread(self):
        self._app._main_cancel_recording()

    def setProcessingOnMainThread(self):
        self._app._set_estado("transcrevendo")

    def finishRecordingOnMainThread(self):
        if self._app._had_error:
            # overlay em estado de erro se esconde sozinho após 2s;
            # ícone de erro e "Último erro" permanecem no menu
            return
        self._app._overlay.hide()
        self._app._set_estado("parado")
        self._app._ultimo_erro = None
        self._app._atualizar_linha_de_status()

    def showErrorOnMainThread_(self, message):
        self._app._show_error(str(message))
        self._app._overlay.show_error(str(message))

    def openLog_(self, sender):
        subprocess.run(["open", str(LOG_PATH)])

    def openSettings_(self, sender):
        self._app._settings.show()


class VozMenuBar:
    def __init__(self, config: Config):
        self._config = config
        self._had_error = False
        self._ultimo_erro = None
        self._overlay = IndicadorVoz()
        self._recorder = AudioRecorder(
            config.sample_rate,
            sample_callback=self._overlay.update_bars,
        )
        self._pipeline = None
        self._settings = (
            SettingsWindowController.alloc().initWithConfig_onSave_(
                config, self._apply_config
            )
        )
        self._gesto = self._novo_gesto(config.hotkey)

        self._dispatcher = (
            MainThreadDispatcher.alloc().initWithApp_(self)
        )
        self._status_item = self._create_status_item()
        self._set_estado("parado")
        self._setup_menu()
        self._rebuild_pipeline()
        threading.Thread(
            target=self._start_listener, daemon=True
        ).start()

    def _create_status_item(self):
        status_bar = NSStatusBar.systemStatusBar()
        return status_bar.statusItemWithLength_(
            NSVariableStatusItemLength
        )

    def _set_estado(self, estado: str):
        botao = self._status_item.button()
        botao.setImage_(imagem_do_icone(estado))
        botao.setTitle_("")

    def _atualizar_linha_de_status(self):
        texto, cor = linha_de_status(
            rotulo_hotkey(self._config.hotkey), self._ultimo_erro
        )
        attrs = {
            NSFontAttributeName: NSFont.menuFontOfSize_(13.0),
            NSForegroundColorAttributeName: hex_to_nscolor(cor),
        }
        self._linha_status.setAttributedTitle_(
            NSAttributedString.alloc().initWithString_attributes_(texto, attrs)
        )

    def _setup_menu(self):
        menu = NSMenu.alloc().init()
        menu.setAppearance_(
            NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua)
        )
        self._linha_status = (
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("", None, "")
        )
        self._linha_status.setEnabled_(False)
        self._atualizar_linha_de_status()
        menu.addItem_(self._linha_status)
        menu.addItem_(NSMenuItem.separatorItem())

        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Configurações…", "openSettings:", ","
        )
        settings_item.setTarget_(self._dispatcher)
        menu.addItem_(settings_item)

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

    def _novo_gesto(self, hotkey_name):
        return GestoTecla(
            tecla=resolve_hotkey(hotkey_name),
            ao_iniciar=lambda: self._on_main("startRecordingOnMainThread"),
            ao_concluir=lambda: self._on_main("stopRecordingOnMainThread"),
            ao_cancelar=lambda: self._on_main("cancelRecordingOnMainThread"),
        )

    def _on_main(self, selector):
        self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            selector, None, False
        )

    def _on_press(self, key):
        self._gesto.pressionar(key)

    def _main_start_recording(self):
        self._set_estado("gravando")
        self._overlay.show()
        try:
            self._recorder.start()
        except Exception as e:
            self._handle_start_recording_failure(e)

    def _handle_start_recording_failure(self, error):
        logger.exception("Falha ao iniciar gravação")
        self._gesto.abandonar()
        self._overlay.hide()
        self._set_estado("parado")
        self._notify_error(str(error))

    def _on_release(self, key):
        self._gesto.soltar(key)

    def _main_cancel_recording(self):
        self._overlay.hide()
        self._set_estado("parado")
        threading.Thread(target=self._discard_recording, daemon=True).start()

    def _discard_recording(self):
        try:
            self._recorder.stop()
        except Exception:
            logger.exception("Falha ao descartar gravação cancelada")

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
            if self._pipeline is None:
                raise TranscriptionError(
                    self._config.provider,
                    "API key ausente. Configure em Configurações…",
                )
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
        self._ultimo_erro = message
        self._set_estado("erro")
        self._atualizar_linha_de_status()

    def _notify_error(self, message: str):
        self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showErrorOnMainThread:", message, False
        )

    def _rebuild_pipeline(self):
        try:
            transcriber, cleaner = factory.build_components(self._config)
        except TranscriptionError as e:
            self._pipeline = None
            logger.error("Pipeline indisponível: %s", e)
            self._show_error(str(e))
            return
        self._pipeline = DictationPipeline(
            transcriber,
            cleaner,
            TextInjector(),
            enable_cleanup=cleaner is not None,
        )

    def _apply_config(self, new_config):
        # chamado pela janela de Configurações (main thread) — aplica na hora
        self._config = new_config
        self._gesto = self._novo_gesto(new_config.hotkey)
        self._had_error = False
        self._ultimo_erro = None
        self._set_estado("parado")
        self._atualizar_linha_de_status()
        self._rebuild_pipeline()


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
    migrate_env_key_if_needed()
    VozMenuBar(Config.load()).run()


if __name__ == "__main__":
    main()
