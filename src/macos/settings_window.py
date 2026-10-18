"""Janela nativa de preferências. Regra de negócio zero: só liga AppKit ao core."""
import threading

import objc
from AppKit import (
    NSApp,
    NSAppearance,
    NSAppearanceNameDarkAqua,
    NSAttributedString,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSButton,
    NSFont,
    NSFontAttributeName,
    NSFontWeightRegular,
    NSFontWeightSemibold,
    NSForegroundColorAttributeName,
    NSGradient,
    NSMakePoint,
    NSMakeRect,
    NSPopUpButton,
    NSSecureTextField,
    NSSwitch,
    NSTextField,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

from src.core import login_item, secrets
from src.core.config import (
    HOTKEYS_SUPORTADAS,
    Config,
    hotkey_do_rotulo,
    rotulo_hotkey,
)
from src.core.providers import factory
from src.core.providers.base import PROVIDER_CATALOG
from src.macos.cores import hex_to_nscolor

_W, _H = 460, 520
_MARGEM = 20
_LINHA_H = 40
_ROTULO_X = _MARGEM + 14
_CONTROLE_W = 220
_CONTROLE_X = _W - _MARGEM - 12 - _CONTROLE_W
_HOTKEYS = tuple(rotulo_hotkey(t) for t in HOTKEYS_SUPORTADAS)
_PROVIDER_KEYS = tuple(PROVIDER_CATALOG)  # ("groq", "openai", "local")

_FUNDO = "#14141C"
_GRUPO = "#1E1E29"
_DIVISOR = "#2A2A38"
_TEXTO = "#E6E7EE"
_FAIXA = ("#7C5CFF", "#36D1FF", "#FF5CB4")
_SALVAR = ("#7C5CFF", "#36D1FF")
_SECUNDARIO = (_DIVISOR, _DIVISOR)


class _Faixa(NSView):
    def drawRect_(self, rect):
        _degrade(_FAIXA).drawInBezierPath_angle_(
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                self.bounds(), 2.0, 2.0
            ),
            0.0,
        )


class _BotaoColorido(NSButton):
    def drawRect_(self, rect):
        caminho = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            self.bounds(), 8.0, 8.0
        )
        _degrade(self.cores).drawInBezierPath_angle_(caminho, 0.0)
        if self.isHighlighted():
            hex_to_nscolor("#000000", 0.25).set()
            caminho.fill()
        self._desenhar_titulo()

    @objc.python_method
    def _desenhar_titulo(self):
        titulo = NSAttributedString.alloc().initWithString_attributes_(
            self.title(),
            {
                NSFontAttributeName: NSFont.systemFontOfSize_weight_(
                    13.0, NSFontWeightSemibold
                ),
                NSForegroundColorAttributeName: hex_to_nscolor("#FFFFFF"),
            },
        )
        tamanho, caixa = titulo.size(), self.bounds().size
        titulo.drawAtPoint_(
            NSMakePoint(
                (caixa.width - tamanho.width) / 2,
                (caixa.height - tamanho.height) / 2,
            )
        )


def _degrade(cores):
    return NSGradient.alloc().initWithColors_([hex_to_nscolor(c) for c in cores])


class _Caixa(NSView):
    def drawRect_(self, rect):
        hex_to_nscolor(self.cor).set()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            self.bounds(), self.raio, self.raio
        ).fill()


def _caixa_colorida(frame, cor, raio=0.0):
    caixa = _Caixa.alloc().initWithFrame_(frame)
    caixa.cor, caixa.raio = cor, raio
    return caixa


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
        self._window.setAppearance_(
            NSAppearance.appearanceNamed_(NSAppearanceNameDarkAqua)
        )
        self._window.setBackgroundColor_(hex_to_nscolor(_FUNDO))
        self._window.setTitlebarAppearsTransparent_(True)
        self._window.center()
        self._build_fields()
        self._build_buttons()

    @objc.python_method
    def _build_fields(self):
        content = self._window.contentView()
        self._topo = 14
        content.addSubview_(
            _Faixa.alloc().initWithFrame_(
                NSMakeRect(_MARGEM, _H - self._topo - 4, _W - 2 * _MARGEM, 4)
            )
        )
        self._topo += 20
        self._build_geral(content)
        self._build_transcricao(content)
        self._build_limpeza(content)
        self._status_label = self._label(
            "", NSMakeRect(_MARGEM, 64, _W - 2 * _MARGEM, 18), 12.0, 0.8
        )
        content.addSubview_(self._status_label)

    @objc.python_method
    def _build_geral(self, content):
        self._login_check = self._switch()
        self._login_check.setTarget_(self)
        self._login_check.setAction_("loginToggled:")
        self._hotkey_popup = self._popup(None)
        self._hotkey_popup.addItemsWithTitles_(list(_HOTKEYS))
        rotulos = self._grupo(content, "GERAL", (
            ("Abrir no login", self._login_check),
            ("Tecla de ditado", self._hotkey_popup),
        ))
        y = rotulos[0].frame().origin.y
        self._login_hint = self._label(
            "Instale o app (./install.sh) para ativar",
            NSMakeRect(_ROTULO_X + 100, y, 240, 18), 11.0, 0.5,
        )
        content.addSubview_(self._login_hint)

    @objc.python_method
    def _build_transcricao(self, content):
        self._provider_popup = self._popup("providerChanged:")
        self._api_key_field = NSSecureTextField.alloc().initWithFrame_(
            NSMakeRect(0, 0, _CONTROLE_W, 22)
        )
        self._model_popup = self._popup(None)
        rotulos = self._grupo(content, "TRANSCRIÇÃO", (
            ("Provider", self._provider_popup),
            ("API key", self._api_key_field),
            ("Modelo", self._model_popup),
        ))
        self._api_key_label = rotulos[1]

    @objc.python_method
    def _build_limpeza(self, content):
        self._cleanup_check = self._switch()
        self._cleanup_popup = self._popup(None)
        self._grupo(content, "LIMPEZA DO TEXTO", (
            ("Limpar hesitações", self._cleanup_check),
            ("Modelo de limpeza", self._cleanup_popup),
        ))

    @objc.python_method
    def _grupo(self, content, titulo, linhas):
        content.addSubview_(self._label(
            titulo,
            NSMakeRect(_ROTULO_X - 14, _H - self._topo - 14, 200, 14),
            11.0, 0.6, NSFontWeightSemibold,
        ))
        self._topo += 20
        altura = len(linhas) * _LINHA_H
        content.addSubview_(_caixa_colorida(
            NSMakeRect(_MARGEM, _H - self._topo - altura,
                       _W - 2 * _MARGEM, altura),
            _GRUPO, 10.0,
        ))
        rotulos = [
            self._linha(content, i, texto, controle)
            for i, (texto, controle) in enumerate(linhas)
        ]
        self._topo += altura + 18
        return rotulos

    @objc.python_method
    def _linha(self, content, indice, texto, controle):
        base = _H - self._topo - (indice + 1) * _LINHA_H
        centro = base + _LINHA_H / 2
        if indice > 0:
            content.addSubview_(_caixa_colorida(
                NSMakeRect(_ROTULO_X, base + _LINHA_H,
                           _W - 2 * _ROTULO_X, 1),
                _DIVISOR,
            ))
        rotulo = self._label(texto, NSMakeRect(_ROTULO_X, centro - 9, 160, 18))
        content.addSubview_(rotulo)
        tamanho = controle.frame().size
        controle.setFrameOrigin_(NSMakePoint(
            _W - _MARGEM - 12 - tamanho.width, centro - tamanho.height / 2
        ))
        content.addSubview_(controle)
        return rotulo

    @objc.python_method
    def _build_buttons(self):
        content = self._window.contentView()
        self._test_button = self._button(
            "Testar conexão", _MARGEM, 140, "testConnection:", _SECUNDARIO
        )
        self._save_button = self._button(
            "Salvar", _W - _MARGEM - 120, 120, "saveSettings:", _SALVAR
        )
        content.addSubview_(self._test_button)
        content.addSubview_(self._save_button)

    @objc.python_method
    def _label(self, text, frame, tamanho=13.0, alpha=1.0,
               peso=NSFontWeightRegular):
        field = NSTextField.alloc().initWithFrame_(frame)
        field.setStringValue_(text)
        field.setFont_(NSFont.systemFontOfSize_weight_(tamanho, peso))
        field.setTextColor_(hex_to_nscolor(_TEXTO, alpha))
        field.setBezeled_(False)
        field.setDrawsBackground_(False)
        field.setEditable_(False)
        field.setSelectable_(False)
        return field

    @objc.python_method
    def _popup(self, action):
        popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(0, 0, _CONTROLE_W, 26), False
        )
        if action:
            popup.setTarget_(self)
            popup.setAction_(action)
        return popup

    @objc.python_method
    def _switch(self):
        # NSSwitch não aceita tint próprio no PyObjC atual: usa a cor de
        # destaque do sistema.
        return NSSwitch.alloc().initWithFrame_(NSMakeRect(0, 0, 38, 22))

    @objc.python_method
    def _button(self, title, x, width, action, cores):
        button = _BotaoColorido.alloc().initWithFrame_(
            NSMakeRect(x, 20, width, 32)
        )
        button.cores = cores
        button.setTitle_(title)
        button.setBordered_(False)
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
        self._hotkey_popup.selectItemWithTitle_(
            rotulo_hotkey(self._config.hotkey)
        )
        self._status_label.setStringValue_("")
        self._reload_provider_fields(self._config.provider)
        self._refresh_login_controls()

    @objc.python_method
    def _refresh_login_controls(self):
        installed = login_item.app_installed()
        self._login_check.setEnabled_(installed)
        self._login_check.setState_(1 if login_item.is_enabled() else 0)
        self._login_hint.setHidden_(installed)

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
            hotkey=hotkey_do_rotulo(self._hotkey_popup.titleOfSelectedItem()),
            sample_rate=self._config.sample_rate,
        )

    # ---------- ações (selectors AppKit) ----------

    def loginToggled_(self, sender):
        if self._login_check.state():
            login_item.enable()
        else:
            login_item.disable()

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
