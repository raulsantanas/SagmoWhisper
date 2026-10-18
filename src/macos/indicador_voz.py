"""Indicador de gravação "de assistente": ponto vermelho, três ondas e tempo.

Estados: ouvindo (ondas seguem a voz; aviso de mudo após a carência),
transcrevendo (ponto amarelo, ondas pulsando devagar), erro (1ª linha da
mensagem por 2 s, depois fade-out automático).

Thread-safety: o callback de áudio (update_bars) só grava o RMS sob lock;
todo desenho acontece no main thread, dirigido por um NSTimer de 30 fps.
"""
import math
import threading
import time

import objc
from AppKit import (
    NSAnimationContext,
    NSAttributedString,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSFontAttributeName,
    NSFontWeightMedium,
    NSFontWeightSemibold,
    NSForegroundColorAttributeName,
    NSMakePoint,
    NSMakeRect,
    NSScreen,
    NSView,
    NSWindow,
    NSWindowStyleMaskBorderless,
)
from Foundation import NSTimer

from src.macos.cores import hex_to_nscolor
from src.core.indicador import (
    AMPLITUDE_TRANSCREVENDO,
    ESTILOS_ESCUTA,
    ONDAS,
    EscutaComCarencia,
    NivelDaVoz,
    PicoEntreQuadros,
    amplitude_ouvindo,
    first_line,
    formatar_tempo,
    pontos_da_onda,
)

_WIN_W = 420
_WIN_H = 124
_FPS = 30.0
_ERROR_HIDE_S = 2.0
_LINHA_Y = 72.0
_PONTO_X = 24.0
_PONTO_R = 6.0
_ONDAS_X0 = 44.0
_ONDAS_X1 = 362.0
_ONDAS_MEIA_ALTURA = 36.0
_TEMPO_X = 370.0
_TEXTO_Y = 14.0

_VERMELHO = "#FF4D6D"
_AMARELO = "#F5B942"
_TEXTO_CLARO = "#E6E7EE"
_TEXTO_ERRO = "#FFB4B4"
_TEXTO_TEMPO = "#CFD2DC"


def _texto(conteudo, fonte, cor_hex):
    attrs = {
        NSFontAttributeName: fonte,
        NSForegroundColorAttributeName: hex_to_nscolor(cor_hex),
    }
    return NSAttributedString.alloc().initWithString_attributes_(
        conteudo, attrs
    )


def _caminho_da_onda(pontos):
    path = NSBezierPath.bezierPath()
    passo = (_ONDAS_X1 - _ONDAS_X0) / (len(pontos) - 1)
    for i, p in enumerate(pontos):
        ponto = NSMakePoint(
            _ONDAS_X0 + i * passo, _LINHA_Y + p * _ONDAS_MEIA_ALTURA
        )
        if i == 0:
            path.moveToPoint_(ponto)
        else:
            path.lineToPoint_(ponto)
    path.setLineCapStyle_(1)  # NSLineCapStyleRound
    path.setLineJoinStyle_(1)  # NSLineJoinStyleRound
    return path


class _IndicadorView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(_IndicadorView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._lock = threading.Lock()
        self._escuta = EscutaComCarencia()
        self._reset_state()
        return self

    def _reset_state(self):
        self._estado = "ouvindo"
        self._pico = PicoEntreQuadros()
        self._nivel_voz = NivelDaVoz()
        self._nivel = 0.0
        self._inicio = time.monotonic()
        self._texto, self._cor_texto = ESTILOS_ESCUTA["ok"]

    def reset(self):
        with self._lock:
            self._reset_state()
            self._escuta.reiniciar()

    def freeze(self):
        with self._lock:
            self._estado = "transcrevendo"
            self._texto, self._cor_texto = "Transcrevendo…", _TEXTO_CLARO

    def set_error(self, message: str):
        with self._lock:
            self._estado = "erro"
            self._texto, self._cor_texto = first_line(message), _TEXTO_ERRO

    @objc.python_method
    def registrar_rms(self, rms: float):
        with self._lock:
            self._pico.registrar(rms)

    def drawRect_(self, rect):
        with self._lock:
            if self._estado == "ouvindo":
                self._avancar()
            estado, nivel = self._estado, self._nivel
            texto, cor_texto = self._texto, self._cor_texto
            decorrido = time.monotonic() - self._inicio
        self._desenhar_fundo(rect)
        if estado != "erro":
            self._desenhar_ponto(estado, nivel)
            self._desenhar_ondas(estado, nivel, decorrido)
        if estado == "ouvindo":
            self._desenhar_tempo(decorrido)
        self._desenhar_texto(texto, cor_texto)

    @objc.python_method
    def _avancar(self):
        rms = self._pico.consumir()
        self._nivel = self._nivel_voz.avancar(rms)
        escuta = self._escuta.classificar(rms)
        self._texto, self._cor_texto = ESTILOS_ESCUTA[escuta]

    @objc.python_method
    def _desenhar_fundo(self, rect):
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        cartao = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            rect, 24.0, 24.0
        )
        hex_to_nscolor("#0E0E16", 0.85).set()
        cartao.fill()
        hex_to_nscolor("#FFFFFF", 0.07).set()
        cartao.setLineWidth_(1.0)
        cartao.stroke()

    @objc.python_method
    def _desenhar_ponto(self, estado, nivel):
        cor = _AMARELO if estado == "transcrevendo" else _VERMELHO
        halo_r = _PONTO_R + 3.0 + 6.0 * nivel
        hex_to_nscolor(cor, 0.3).set()
        NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(
                _PONTO_X - halo_r, _LINHA_Y - halo_r, halo_r * 2, halo_r * 2
            )
        ).fill()
        hex_to_nscolor(cor).set()
        NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(
                _PONTO_X - _PONTO_R, _LINHA_Y - _PONTO_R,
                _PONTO_R * 2, _PONTO_R * 2,
            )
        ).fill()

    @objc.python_method
    def _desenhar_ondas(self, estado, nivel, decorrido):
        amplitude = _amplitude(estado, nivel, decorrido)
        for indice, (cor, ciclos, velocidade) in enumerate(ONDAS):
            fase = velocidade * decorrido + indice
            path = _caminho_da_onda(pontos_da_onda(amplitude, ciclos, fase))
            _tracar(path, cor, 7.0, 0.18)  # brilho
            _tracar(path, cor, 2.5, 0.85)

    @objc.python_method
    def _desenhar_tempo(self, decorrido):
        fonte = NSFont.monospacedDigitSystemFontOfSize_weight_(
            13.0, NSFontWeightMedium
        )
        texto = _texto(formatar_tempo(decorrido), fonte, _TEXTO_TEMPO)
        texto.drawAtPoint_(
            NSMakePoint(_TEMPO_X, _LINHA_Y - texto.size().height / 2)
        )

    @objc.python_method
    def _desenhar_texto(self, conteudo, cor):
        fonte = NSFont.systemFontOfSize_weight_(12.0, NSFontWeightSemibold)
        texto = _texto(conteudo, fonte, cor)
        x = (_WIN_W - texto.size().width) / 2
        texto.drawAtPoint_(NSMakePoint(x, _TEXTO_Y))


def _amplitude(estado, nivel, decorrido):
    if estado == "transcrevendo":
        return AMPLITUDE_TRANSCREVENDO * (0.6 + 0.4 * math.sin(2 * decorrido))
    return amplitude_ouvindo(nivel)


def _tracar(path, cor, largura, alpha):
    hex_to_nscolor(cor, alpha).set()
    path.setLineWidth_(largura)
    path.stroke()


class IndicadorVoz:
    def __init__(self):
        # screens()[0] é o monitor principal (o da barra de menu);
        # mainScreen() seria a tela da janela com foco, que muda com o uso.
        screens = NSScreen.screens()
        primary = screens[0] if screens else NSScreen.mainScreen()
        visible = primary.visibleFrame()
        x = visible.origin.x + 20
        y = visible.origin.y + visible.size.height - _WIN_H - 20
        self._window = (
            NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(x, y, _WIN_W, _WIN_H),
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
            )
        )
        self._window.setLevel_(NSFloatingWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(True)
        self._view = _IndicadorView.alloc().initWithFrame_(
            NSMakeRect(0, 0, _WIN_W, _WIN_H)
        )
        self._window.setContentView_(self._view)
        self._timer = None
        self._error_timer = None
        self._hiding = False

    def show(self):
        self._cancel_error_timer()
        self._reaparecer()
        self._view.reset()
        self._window.orderFront_(None)
        self._start_timer()

    def _reaparecer(self):
        # Um fade de hide() ainda em curso terminaria em alpha 0 e deixaria o
        # cartão invisível na gravação seguinte; uma animação de duração 0
        # sobrescreve a que está rodando.
        self._hiding = False

        def animate(ctx):
            ctx.setDuration_(0.0)
            self._window.animator().setAlphaValue_(1.0)

        NSAnimationContext.runAnimationGroup_completionHandler_(animate, None)

    def hide(self):
        self._cancel_error_timer()
        self._hiding = True
        self._stop_timer()

        def animate(ctx):
            ctx.setDuration_(0.3)
            self._window.animator().setAlphaValue_(0.0)

        def complete():
            if self._hiding:
                self._window.orderOut_(None)
                self._window.setAlphaValue_(1.0)

        NSAnimationContext.runAnimationGroup_completionHandler_(
            animate, complete
        )

    def set_transcribing(self):
        self._view.freeze()

    def show_error(self, message: str):
        self._cancel_error_timer()
        self._reaparecer()
        self._view.set_error(message)
        self._window.orderFront_(None)
        self._start_timer()
        self._error_timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            _ERROR_HIDE_S, False, lambda timer: self.hide()
        )

    def _cancel_error_timer(self):
        if self._error_timer is not None:
            self._error_timer.invalidate()
            self._error_timer = None

    def update_bars(self, rms: float):
        # Chamado no thread de áudio: só armazena; o timer de 30fps desenha.
        self._view.registrar_rms(rms)

    def _start_timer(self):
        if self._timer is not None:
            return
        self._timer = NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            1.0 / _FPS, True,
            lambda timer: self._view.setNeedsDisplay_(True),
        )

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None


if __name__ == "__main__":
    # Fumaça manual: python -m src.macos.indicador_voz
    # 0-4s voz sintética; 4-7s silêncio (aviso de mudo perto de 5,5s);
    # 7-9s transcrevendo; 9-11s erro; sai.
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

    app = NSApplication.sharedApplication()
    # Accessory evita o ícone do Python no Dock durante a fumaça manual.
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    indicador = IndicadorVoz()
    indicador.show()
    t0 = time.monotonic()
    fase = {"n": 0}

    def voz_sintetica(t):
        silaba = max(0.0, math.sin(t * 9.3) * math.sin(t * 2.1 + 1) + 0.25)
        return 0.002 + 0.12 * silaba

    def alimentar(timer):
        t = time.monotonic() - t0
        if t < 7.0:
            indicador.update_bars(voz_sintetica(t) if t < 4.0 else 1e-5)
            return
        _avancar_fase(t)

    def _avancar_fase(t):
        if fase["n"] == 0:
            fase["n"] = 1
            indicador.set_transcribing()
        elif fase["n"] == 1:
            _talvez_erro(t)
        else:
            _talvez_sair(t)

    def _talvez_erro(t):
        if t > 9.0:
            fase["n"] = 2
            indicador.show_error("Erro de exemplo: 401 Invalid API Key")

    def _talvez_sair(t):
        if t > 12.0:
            app.terminate_(None)

    NSTimer.scheduledTimerWithTimeInterval_repeats_block_(0.03, True, alimentar)
    app.run()
