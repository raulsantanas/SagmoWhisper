"""Linha de status do menu e estado do ícone, sem subir a UI (padrão __new__)."""
import pytest
from unittest.mock import MagicMock

pytest.importorskip("objc")

import src.app as app_module  # noqa: E402


def _voz(hotkey="ctrl_r"):
    voz = app_module.VozMenuBar.__new__(app_module.VozMenuBar)
    voz._config = MagicMock(hotkey=hotkey)
    voz._ultimo_erro = None
    voz._had_error = False
    voz._linha_status = MagicMock()
    voz._set_estado = MagicMock()
    voz._overlay = MagicMock()
    voz._rebuild_pipeline = MagicMock()
    return voz


def _titulo_da_linha(voz):
    return voz._linha_status.setAttributedTitle_.call_args[0][0].string()


def test_show_error_poe_erro_na_linha_de_status_e_estado_erro():
    voz = _voz()
    voz._show_error("401 Invalid API Key")
    voz._set_estado.assert_called_with("erro")
    assert _titulo_da_linha(voz).startswith("Último erro:")


def test_apply_config_atualiza_linha_de_status_com_tecla_nova():
    voz = _voz()
    voz._apply_config(MagicMock(hotkey="cmd_r"))
    assert _titulo_da_linha(voz).endswith("Command direito")


def test_finish_sem_erro_volta_para_pronto():
    voz = _voz()
    voz._show_error("falhou antes")
    voz._had_error = False
    dispatcher = app_module.MainThreadDispatcher.alloc().initWithApp_(voz)
    dispatcher.finishRecordingOnMainThread()
    voz._set_estado.assert_called_with("parado")
    assert _titulo_da_linha(voz).startswith("● Pronto")
