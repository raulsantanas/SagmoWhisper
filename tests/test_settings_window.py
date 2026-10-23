"""Caracterização da janela de Configurações: fixa o comportamento antes do
redesenho visual. Os testes valem para a janela antiga e para a nova."""
import dataclasses
from unittest.mock import MagicMock

import pytest

pytest.importorskip("objc")

from src.core import correcoes, login_item, secrets  # noqa: E402
from src.core.config import DEFAULTS, Config  # noqa: E402
from src.core.providers import factory  # noqa: E402
from src.macos import settings_window  # noqa: E402
from src.macos.settings_window import SettingsWindowController  # noqa: E402


@pytest.fixture
def janela(monkeypatch):
    monkeypatch.setattr(login_item, "app_installed", lambda: True)
    monkeypatch.setattr(login_item, "is_enabled", lambda: False)
    monkeypatch.setattr(factory, "resolve_api_key", lambda provider: "k")
    monkeypatch.setattr(secrets, "set_api_key", MagicMock())
    monkeypatch.setattr(Config, "save", lambda self: None)
    config = dataclasses.replace(Config(**DEFAULTS), hotkey="cmd_r")
    on_save = MagicMock()
    controller = SettingsWindowController.alloc().initWithConfig_onSave_(
        config, on_save
    )
    controller._refresh_from_config()
    return controller, config, on_save


def test_ida_e_volta_preserva_config(janela):
    controller, config, _ = janela
    assert controller._collect_config() == config


def test_provider_local_esconde_api_key_e_desliga_limpeza(janela):
    controller, _, _ = janela
    controller._provider_popup.selectItemAtIndex_(
        settings_window._PROVIDER_KEYS.index("local")
    )
    controller.providerChanged_(None)
    assert controller._api_key_field.isHidden()
    assert not controller._cleanup_check.isEnabled()


def test_salvar_guarda_chave_e_chama_on_save(janela):
    controller, config, on_save = janela
    controller.saveSettings_(None)
    secrets.set_api_key.assert_called_once_with("groq", "k")
    on_save.assert_called_once_with(config)


def test_limpeza_desmarcada_e_salva_como_false(janela):
    controller, _, on_save = janela
    controller._cleanup_check.setState_(0)
    controller.saveSettings_(None)
    assert on_save.call_args[0][0].enable_cleanup is False


def test_adicionar_correcao_grava_e_reaplica_sem_reiniciar(janela):
    controller, config, on_save = janela
    controller._errado_field.setStringValue_("hostinguer")
    controller._certo_field.setStringValue_("Hostinger")

    controller.adicionarCorrecao_(None)

    assert correcoes.carregar_correcoes()["hostinguer"] == "Hostinger"
    on_save.assert_called_once_with(config)
    assert controller._errado_field.stringValue() == ""
    assert controller._certo_field.stringValue() == ""
    assert "hostinguer → Hostinger" in controller._status_label.stringValue()


def test_adicionar_correcao_vazia_avisa_e_nao_reaplica(janela):
    controller, _, on_save = janela
    controller._errado_field.setStringValue_("hostinguer")

    controller.adicionarCorrecao_(None)

    on_save.assert_not_called()
    assert controller._status_label.stringValue().startswith("✗")
