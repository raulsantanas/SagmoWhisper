import sys

import pytest

from src.core.app_em_foco import app_em_foco


class _App:
    def __init__(self, nome):
        self._nome = nome

    def localizedName(self):
        return self._nome


class _Workspace:
    def __init__(self, app):
        self._app = app

    def frontmostApplication(self):
        return self._app


def test_macos_devolve_o_nome_do_app_na_frente():
    assert app_em_foco("darwin", _Workspace(_App("Code"))) == "Code"


def test_macos_sem_app_na_frente_devolve_none():
    assert app_em_foco("darwin", _Workspace(None)) is None


def test_linux_devolve_none_sem_tocar_no_appkit():
    class _Explode:
        def frontmostApplication(self):
            raise AssertionError("não devia consultar")

    assert app_em_foco("linux", _Explode()) is None


@pytest.mark.skipif(sys.platform != "darwin", reason="só no macOS")
def test_macos_de_verdade_devolve_texto_ou_none():
    pytest.importorskip("AppKit")

    nome = app_em_foco()

    assert nome is None or (isinstance(nome, str) and nome)
