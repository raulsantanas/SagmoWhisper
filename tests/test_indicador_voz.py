import pytest

pytest.importorskip("objc")

from src.macos import indicador_voz  # noqa: E402
from src.macos.indicador_voz import IndicadorVoz  # noqa: E402


class _Janela:
    def __init__(self):
        self.alpha = 1.0
        self.na_tela = False

    def animator(self):
        return self

    def setAlphaValue_(self, valor):
        self.alpha = valor

    def orderFront_(self, _):
        self.na_tela = True

    def orderOut_(self, _):
        self.na_tela = False


class _View:
    def reset(self):
        pass

    def set_error(self, _):
        pass

    def setNeedsDisplay_(self, _):
        pass


class _Timer:
    def __init__(self, bloco):
        self.bloco = bloco
        self.valido = True

    def invalidate(self):
        self.valido = False


class _FabricaDeTimers:
    def __init__(self):
        self.criados = []

    def scheduledTimerWithTimeInterval_repeats_block_(self, _s, _rep, bloco):
        timer = _Timer(bloco)
        self.criados.append(timer)
        return timer


class _AnimacaoPendente:
    """Guarda o fade para terminá-lo depois, como o AppKit faria 0,3 s depois."""

    def __init__(self):
        self.pendentes = []

    def runAnimationGroup_completionHandler_(self, animar, completar):
        self.pendentes.append((animar, completar))

    def terminar_tudo(self):
        pendentes, self.pendentes = self.pendentes, []
        for animar, completar in pendentes:
            animar(_Contexto())
            if completar:
                completar()


class _Contexto:
    def setDuration_(self, _):
        pass


@pytest.fixture
def indicador(monkeypatch):
    animacao = _AnimacaoPendente()
    timers = _FabricaDeTimers()
    monkeypatch.setattr(indicador_voz, "NSAnimationContext", animacao)
    monkeypatch.setattr(indicador_voz, "NSTimer", timers)
    ind = IndicadorVoz.__new__(IndicadorVoz)
    ind._window, ind._view = _Janela(), _View()
    ind._timer = ind._error_timer = None
    ind._hiding = False
    return ind, animacao, timers


def test_show_durante_fade_deixa_cartao_visivel(indicador):
    ind, animacao, _ = indicador
    ind.show()
    ind.hide()
    ind.show()
    animacao.terminar_tudo()
    assert ind._window.alpha == 1.0
    assert ind._window.na_tela


def test_segundo_erro_cancela_timer_do_primeiro(indicador):
    ind, _, timers = indicador
    ind.show_error("primeiro")
    timer_do_primeiro = ind._error_timer
    ind.show_error("segundo")
    assert not timer_do_primeiro.valido
