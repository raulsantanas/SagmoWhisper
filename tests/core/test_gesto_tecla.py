from pynput import keyboard

from src.core.gesto_tecla import GestoTecla

CTRL_R = keyboard.Key.ctrl_r
CTRL_L = keyboard.Key.ctrl_l
TECLA_C = keyboard.KeyCode.from_char("c")


class _Relogio:
    def __init__(self):
        self.agora = 0.0

    def __call__(self):
        return self.agora


def _gesto(tecla=CTRL_R):
    eventos = []
    relogio = _Relogio()
    gesto = GestoTecla(
        tecla=tecla,
        ao_iniciar=lambda: eventos.append("iniciar"),
        ao_concluir=lambda: eventos.append("concluir"),
        ao_cancelar=lambda: eventos.append("cancelar"),
        relogio=relogio,
    )
    return gesto, eventos, relogio


def test_segurar_sozinho_e_soltar_conclui_a_gravacao():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    relogio.agora = 1.0
    gesto.soltar(CTRL_R)
    assert eventos == ["iniciar", "concluir"]


def test_combinacao_com_outra_tecla_cancela_e_descarta():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    gesto.pressionar(TECLA_C)
    relogio.agora = 1.0
    gesto.soltar(TECLA_C)
    gesto.soltar(CTRL_R)
    assert eventos == ["iniciar", "cancelar"]


def test_toque_menor_que_300ms_cancela_sem_concluir():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    relogio.agora = 0.29
    gesto.soltar(CTRL_R)
    assert eventos == ["iniciar", "cancelar"]


def test_toque_de_exatamente_300ms_conclui():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    relogio.agora = 0.3
    gesto.soltar(CTRL_R)
    assert eventos == ["iniciar", "concluir"]


def test_control_esquerdo_nunca_grava():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_L)
    relogio.agora = 1.0
    gesto.soltar(CTRL_L)
    assert eventos == []


def test_repeticao_automatica_da_tecla_nao_reinicia_a_gravacao():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    gesto.pressionar(CTRL_R)
    relogio.agora = 1.0
    gesto.soltar(CTRL_R)
    assert eventos == ["iniciar", "concluir"]


def test_outras_teclas_sem_gravacao_nao_disparam_nada():
    gesto, eventos, _ = _gesto()
    gesto.pressionar(TECLA_C)
    gesto.soltar(TECLA_C)
    assert eventos == []


def test_apos_cancelar_nova_pressao_grava_normalmente():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    gesto.pressionar(TECLA_C)
    gesto.soltar(CTRL_R)
    relogio.agora = 5.0
    gesto.pressionar(CTRL_R)
    relogio.agora = 6.0
    gesto.soltar(CTRL_R)
    assert eventos == ["iniciar", "cancelar", "iniciar", "concluir"]


def test_abandonar_faz_o_soltar_seguinte_nao_disparar_nada():
    gesto, eventos, relogio = _gesto()
    gesto.pressionar(CTRL_R)
    gesto.abandonar()
    relogio.agora = 1.0
    gesto.soltar(CTRL_R)
    gesto.pressionar(CTRL_R)
    assert eventos == ["iniciar", "iniciar"]


def test_f8_continua_funcionando_como_tecla():
    gesto, eventos, relogio = _gesto(tecla=keyboard.Key.f8)
    gesto.pressionar(keyboard.Key.f8)
    relogio.agora = 1.0
    gesto.soltar(keyboard.Key.f8)
    assert eventos == ["iniciar", "concluir"]
