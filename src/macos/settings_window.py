"""Janela nativa de preferências. Regra de negócio zero: só liga AppKit ao core."""
import threading

import objc
from AppKit import (
    NSApp,
    NSBackingStoreBuffered,
    NSButton,
    NSButtonTypeSwitch,
    NSMakeRect,
    NSPopUpButton,
    NSSecureTextField,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

from src.core import secrets
from src.core.config import Config
from src.core.providers import factory
from src.core.providers.base import PROVIDER_CATALOG

_W, _H = 440, 340
_LABEL_X, _LABEL_W = 20, 130
_FIELD_X, _FIELD_W = 160, 260
_ROW_H = 24
_HOTKEYS = tuple(f"F{n}" for n in range(1, 13))
_PROVIDER_KEYS = tuple(PROVIDER_CATALOG)  # ("groq", "openai", "local")


class SettingsWindowController(NSObject):
    def initWithConfig_onSave_(self, config, on_save):
        self = objc.super(SettingsWindowController, self).init()
        if self is None:
            return None
        self._config = config
        self._on_save = on_save
        self._build_window()
        return self

    # ---------- construção ----------

    @objc.python_method
    def _build_window(self):
        self._window = (
            NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, _W, _H),
                NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
                NSBackingStoreBuffered,
                False,
            )
        )
        self._window.setTitle_("Configurações")
        self._window.setReleasedWhenClosed_(False)
        self._window.center()
        self._build_fields()
        self._build_buttons()

    @objc.python_method
    def _build_fields(self):
        content = self._window.contentView()
        self._provider_popup = self._popup(292, "providerChanged:")
        self._add_row(content, "Provider", 292, self._provider_popup)
        self._api_key_field = NSSecureTextField.alloc().initWithFrame_(
            NSMakeRect(_FIELD_X, 252, _FIELD_W, _ROW_H)
        )
        self._api_key_label = self._add_row(
            content, "API key", 252, self._api_key_field
        )
        self._model_popup = self._popup(212, None)
        self._add_row(content, "Modelo", 212, self._model_popup)
        self._cleanup_check = self._checkbox(172, "Limpar hesitações")
        content.addSubview_(self._cleanup_check)
        self._cleanup_popup = self._popup(132, None)
        self._add_row(content, "Modelo de limpeza", 132, self._cleanup_popup)
        self._hotkey_popup = self._popup(92, None)
        self._hotkey_popup.addItemsWithTitles_(list(_HOTKEYS))
        self._add_row(content, "Tecla de ditado", 92, self._hotkey_popup)
        self._status_label = self._label("", 56, _W - 40)
        content.addSubview_(self._status_label)

    @objc.python_method
    def _build_buttons(self):
        content = self._window.contentView()
        self._test_button = self._button(
            "Testar conexão", 20, 20, 140, "testConnection:"
        )
        self._save_button = self._button(
            "Salvar", _W - 120, 20, 100, "saveSettings:"
        )
        content.addSubview_(self._test_button)
        content.addSubview_(self._save_button)

    @objc.python_method
    def _add_row(self, content, title, y, control):
        label = self._label(title + ":", y + 3, _LABEL_W)
        content.addSubview_(label)
        content.addSubview_(control)
        return label

    @objc.python_method
    def _label(self, text, y, width):
        field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(_LABEL_X, y, width, 18)
        )
        field.setStringValue_(text)
        field.setBezeled_(False)
        field.setDrawsBackground_(False)
        field.setEditable_(False)
        field.setSelectable_(False)
        return field

    @objc.python_method
    def _popup(self, y, action):
        popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(_FIELD_X, y, _FIELD_W, _ROW_H + 2), False
        )
        if action:
            popup.setTarget_(self)
            popup.setAction_(action)
        return popup

    @objc.python_method
    def _checkbox(self, y, title):
        check = NSButton.alloc().initWithFrame_(
            NSMakeRect(_FIELD_X, y, _FIELD_W, _ROW_H)
        )
        check.setButtonType_(NSButtonTypeSwitch)
        check.setTitle_(title)
        return check

    @objc.python_method
    def _button(self, title, x, y, width, action):
        button = NSButton.alloc().initWithFrame_(
            NSMakeRect(x, y, width, 28)
        )
        button.setTitle_(title)
        button.setBezelStyle_(1)  # NSBezelStyleRounded
        button.setTarget_(self)
        button.setAction_(action)
        return button

    # ---------- estado <-> controles ----------

    @objc.python_method
    def _refresh_from_config(self):
        labels = [PROVIDER_CATALOG[k].label for k in _PROVIDER_KEYS]
        self._provider_popup.removeAllItems()
        self._provider_popup.addItemsWithTitles_(labels)
        self._provider_popup.selectItemAtIndex_(
            _PROVIDER_KEYS.index(self._config.provider)
        )
        self._cleanup_check.setState_(1 if self._config.enable_cleanup else 0)
        self._hotkey_popup.selectItemWithTitle_(self._config.hotkey.upper())
        self._status_label.setStringValue_("")
        self._reload_provider_fields(self._config.provider)

    @objc.python_method
    def _reload_provider_fields(self, provider_key):
        info = PROVIDER_CATALOG[provider_key]
        self._fill_popup(
            self._model_popup,
            info.transcription_models,
            self._config.transcription_model,
        )
        self._fill_popup(
            self._cleanup_popup,
            info.cleanup_models,
            self._config.cleanup_model,
        )
        self._api_key_field.setHidden_(not info.needs_api_key)
        self._api_key_label.setHidden_(not info.needs_api_key)
        self._cleanup_check.setEnabled_(bool(info.cleanup_models))
        self._cleanup_popup.setEnabled_(bool(info.cleanup_models))
        stored = factory.resolve_api_key(provider_key) or ""
        self._api_key_field.setStringValue_(stored)

    @objc.python_method
    def _fill_popup(self, popup, options, current):
        popup.removeAllItems()
        popup.addItemsWithTitles_(list(options))
        if current in options:
            popup.selectItemWithTitle_(current)

    @objc.python_method
    def _selected_provider(self):
        return _PROVIDER_KEYS[self._provider_popup.indexOfSelectedItem()]

    @objc.python_method
    def _collect_config(self) -> Config:
        provider = self._selected_provider()
        info = PROVIDER_CATALOG[provider]
        cleanup_model = (
            self._cleanup_popup.titleOfSelectedItem()
            or self._config.cleanup_model
        )
        return Config(
            provider=provider,
            transcription_model=self._model_popup.titleOfSelectedItem(),
            cleanup_model=cleanup_model,
            language=self._config.language,
            enable_cleanup=bool(self._cleanup_check.state())
            and bool(info.cleanup_models),
            hotkey=self._hotkey_popup.titleOfSelectedItem().lower(),
            sample_rate=self._config.sample_rate,
        )

    # ---------- ações (selectors AppKit) ----------

    def providerChanged_(self, sender):
        self._reload_provider_fields(self._selected_provider())

    def testConnection_(self, sender):
        provider = self._selected_provider()
        api_key = str(self._api_key_field.stringValue())
        self._status_label.setStringValue_("Testando…")
        threading.Thread(
            target=self._run_connection_test,
            args=(provider, api_key),
            daemon=True,
        ).start()

    @objc.python_method
    def _run_connection_test(self, provider, api_key):
        try:
            factory.test_connection(provider, api_key)
            result = "✓ Conexão OK"
        except Exception as e:
            result = f"✗ {e}"
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showTestResult:", result, False
        )

    def showTestResult_(self, message):
        self._status_label.setStringValue_(str(message))

    def saveSettings_(self, sender):
        new_config = self._collect_config()
        api_key = str(self._api_key_field.stringValue()).strip()
        if PROVIDER_CATALOG[new_config.provider].needs_api_key and api_key:
            secrets.set_api_key(new_config.provider, api_key)
        new_config.save()
        self._config = new_config
        self._on_save(new_config)
        self._status_label.setStringValue_("✓ Salvo e aplicado")

    # ---------- API pública ----------

    def show(self):
        self._refresh_from_config()
        self._window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)


if __name__ == "__main__":
    # Fumaça manual: python -m src.macos.settings_window
    # Abre a janela com config default; Salvar imprime o config no stdout.
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyAccessory,
    )

    from src.core.config import DEFAULTS

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = SettingsWindowController.alloc().initWithConfig_onSave_(
        Config(**DEFAULTS), lambda cfg: print("on_save:", cfg)
    )
    controller.show()
    app.run()
