import time

import pyperclip
from pynput.keyboard import Controller, Key


class TextInjector:
    def __init__(self):
        self._keyboard = Controller()

    def inject(self, text: str) -> None:
        # Clipboard + Cmd+V em vez de kb.type(): type() quebra acentos PT-BR.
        pyperclip.copy(text)
        time.sleep(0.05)
        self._paste()

    def _paste(self) -> None:
        with self._keyboard.pressed(Key.cmd):
            self._keyboard.press("v")
            self._keyboard.release("v")
