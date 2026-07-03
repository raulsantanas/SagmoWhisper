"""Integração real com X11 — roda no CI Linux sob Xvfb (xvfb-run pytest).

No Mac estes testes são pulados: o alvo é exatamente o backend X11.
"""
import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="integração X11 só faz sentido no Linux (Xvfb no CI)",
)


def test_clipboard_real_faz_roundtrip_com_acentos():
    import pyperclip

    pyperclip.copy("olá, transcrição com acentuação çãé")
    assert pyperclip.paste() == "olá, transcrição com acentuação çãé"


def test_emitir_ctrl_v_no_display_virtual_nao_falha():
    from pynput.keyboard import Controller, Key

    kb = Controller()
    with kb.pressed(Key.ctrl):
        kb.press("v")
        kb.release("v")


def test_text_injector_completo_copia_para_o_clipboard_real():
    import pyperclip

    from src.text_injector import TextInjector

    TextInjector().inject("ditado de verdade no X11")
    assert pyperclip.paste() == "ditado de verdade no X11"
