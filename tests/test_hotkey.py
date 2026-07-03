from pynput import keyboard

from src.hotkey import resolve_hotkey


def test_nome_de_tecla_especial_vira_key():
    assert resolve_hotkey("f8") is keyboard.Key.f8


def test_nome_maiusculo_e_normalizado():
    assert resolve_hotkey("F8") is keyboard.Key.f8


def test_caractere_simples_vira_keycode():
    assert resolve_hotkey("j") == keyboard.KeyCode.from_char("j")
