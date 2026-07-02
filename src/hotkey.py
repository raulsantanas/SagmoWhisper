"""Resolve o nome da hotkey do config para objeto pynput (Mac e Linux)."""
from pynput import keyboard


def resolve_hotkey(name: str):
    try:
        return getattr(keyboard.Key, name.lower())
    except AttributeError:
        return keyboard.KeyCode.from_char(name)
