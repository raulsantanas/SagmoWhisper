"""RED (bug de produção 2026-09-19): _main_start_recording() não trata falha
de start().

Quando o microfone está indisponível (TCC revogado), self._recorder.start()
lança e a exceção sobe sem tratamento pelo dispatcher do PyObjC (app.py:178,
sem try/except). Consequências reais:
  - self._recording fica True (foi setado em _on_press, app.py:170), então o
    release da tecla dispara _handle_recording -> stop() sobre um recorder
    inconsistente;
  - o overlay de gravação fica aceso como "gravando";
  - nenhum erro limpo é mostrado ao usuário.

Contrato fixado aqui (ainda NÃO implementado): no caminho de falha,
_main_start_recording deve
  - resetar self._recording = False;
  - esconder o overlay de gravação;
  - acionar o mecanismo de erro limpo já existente (_notify_error);
  - NÃO deixar a exceção vazar pro dispatcher.

VozMenuBar.__init__ é acoplado ao AppKit (status bar, overlay, listener de
teclado), então o teste constrói a instância via __new__ e injeta só os
colaboradores que o método toca — comportamento sobre o método, sem subir a UI.
"""
import pytest
from unittest.mock import MagicMock

# src.app importa AppKit/objc: só existe no macOS (o job test-linux não tem).
pytest.importorskip("objc")

import src.app as app_module  # noqa: E402


def _voz_stub_with_failing_recorder():
    voz = app_module.VozMenuBar.__new__(app_module.VozMenuBar)
    voz._recording = True  # estado deixado por _on_press antes do start
    voz._overlay = MagicMock()
    voz._recorder = MagicMock()
    voz._recorder.start.side_effect = RuntimeError("mic indisponível (TCC)")
    voz._set_title = MagicMock()
    voz._notify_error = MagicMock()
    return voz


def test_main_start_recording_does_not_leak_exception_on_start_failure():
    voz = _voz_stub_with_failing_recorder()
    try:
        voz._main_start_recording()
    except Exception as e:
        pytest.fail(
            "_main_start_recording deixou a exceção vazar pro dispatcher "
            f"PyObjC: {e!r}"
        )


def test_main_start_recording_resets_recording_flag_on_start_failure():
    voz = _voz_stub_with_failing_recorder()
    try:
        voz._main_start_recording()
    except Exception:
        pass

    assert voz._recording is False, (
        "_recording ficou True após falha no start — o release da tecla "
        "tentaria stop() sobre um recorder inconsistente"
    )


def test_main_start_recording_notifies_error_and_hides_overlay_on_start_failure():
    voz = _voz_stub_with_failing_recorder()
    try:
        voz._main_start_recording()
    except Exception:
        pass

    voz._notify_error.assert_called_once()
    assert voz._overlay.hide.called or voz._overlay.show_error.called, (
        "overlay de gravação ficou aceso após falha no start — deve ser "
        "escondido / trocado para estado de erro"
    )
