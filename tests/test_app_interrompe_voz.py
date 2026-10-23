"""ROADMAP 2.3: tocar a tecla de gravação (Control direito) interrompe a fala."""
from unittest.mock import MagicMock

import pytest

pytest.importorskip("objc")

import src.app as app_module  # noqa: E402
from src.hotkey import resolve_hotkey  # noqa: E402


def _app():
    app = app_module.VozMenuBar.__new__(app_module.VozMenuBar)
    app._voz = MagicMock()
    app._dispatcher = MagicMock()
    app._gesto = app._novo_gesto("ctrl_r")
    return app


def test_apertar_a_tecla_cala_a_voz_e_comeca_a_gravar():
    app = _app()

    app._on_press(resolve_hotkey("ctrl_r"))

    app._voz.interromper.assert_called_once_with()
    seletor = app._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_
    assert seletor.call_args[0][0] == "startRecordingOnMainThread"


def test_outra_tecla_nao_cala_a_voz():
    app = _app()

    app._on_press(resolve_hotkey("f8"))

    app._voz.interromper.assert_not_called()
