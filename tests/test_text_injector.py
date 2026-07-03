from pynput.keyboard import Key

from src.text_injector import TextInjector


def test_no_mac_o_colar_usa_cmd():
    injector = TextInjector(platform="darwin")
    assert injector._modifier is Key.cmd


def test_no_linux_o_colar_usa_ctrl():
    injector = TextInjector(platform="linux")
    assert injector._modifier is Key.ctrl
