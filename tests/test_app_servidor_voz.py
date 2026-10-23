"""ROADMAP 3.2: o app sobe o servidor local de voz na porta da config."""
from unittest.mock import MagicMock

import pytest

pytest.importorskip("objc")

import src.app as app_module  # noqa: E402
from src.core.config import DEFAULTS, Config  # noqa: E402


def test_app_sobe_o_servidor_com_a_voz_e_a_porta_da_config(monkeypatch):
    servidor = MagicMock()
    criar = MagicMock(return_value=servidor)
    monkeypatch.setattr(app_module, "ServidorVoz", criar)
    app = app_module.VozMenuBar.__new__(app_module.VozMenuBar)
    app._config = Config(**{**DEFAULTS, "voice_port": 50123})
    app._voz = MagicMock()

    resultado = app._iniciar_servidor_de_voz()

    criar.assert_called_once_with(app._voz, 50123)
    servidor.iniciar.assert_called_once_with()
    assert resultado is servidor
