import sys

import pytest

from src.core.app_em_foco import app_em_foco


class _App:
    def __init__(self, bundle_id, nome="Mensagens"):
        self._bundle_id = bundle_id
        self._nome = nome

    def bundleIdentifier(self):
        return self._bundle_id

    def localizedName(self):
        return self._nome


class _Workspace:
    def __init__(self, app):
        self._app = app

    def frontmostApplication(self):
        return self._app


def test_macos_devolve_o_bundle_id_que_nao_muda_com_o_idioma():
    app = _App("com.apple.MobileSMS", nome="Mensagens")

    assert app_em_foco("darwin", _Workspace(app)) == "com.apple.MobileSMS"


def test_app_sem_bundle_id_devolve_none():
    assert app_em_foco("darwin", _Workspace(_App(None))) is None


def test_macos_sem_app_na_frente_devolve_none():
    assert app_em_foco("darwin", _Workspace(None)) is None


def test_linux_devolve_none_sem_tocar_no_appkit():
    class _Explode:
        def frontmostApplication(self):
            raise AssertionError("não devia consultar")

    assert app_em_foco("linux", _Explode()) is None


@pytest.mark.skipif(sys.platform != "darwin", reason="só no macOS")
def test_macos_de_verdade_devolve_bundle_id_ou_none():
    pytest.importorskip("AppKit")

    nome = app_em_foco()

    assert nome is None or "." in nome
