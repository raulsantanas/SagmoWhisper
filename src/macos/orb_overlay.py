"""Overlay "Orbe + Barras" (mockup D): orbe roxa estilo assistente de IA.

Estados: listening (orbe pulsante + anel + barras), transcribing (rotação
lenta, barras congeladas a 40% de alpha), error (orbe vermelha por 2 s com a
primeira linha da mensagem, depois fade-out automático).

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
    NSColorSpace,
    NSFloatingWindowLevel,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGradient,
    NSMakePoint,
    NSMakeRect,
    NSScreen,
    NSView,
    NSWindow,
    NSWindowStyleMaskBorderless,
)
from Foundation import NSTimer

from src.core.audio_level import RecentPeakClassifier, rms_to_level
from src.core.orb_animation import (
    first_line,
    orb_glow,
    orb_scale,
    ring_progress,
    rotation_angle,
)

_WIN_W = 320
_WIN_H = 96
_FPS = 30.0
_ORB_CX = 44.0
_ORB_CY = 44.0
_ORB_RADIUS = 23.0
_RING_SPAN = 22.0
_BAR_COUNT = 20
_BARS_X0 = 92.0
_BARS_X1 = 308.0
_BAR_W = 5.0
_BAR_MAX_H = 40.0
_BAR_MIN_H = 3.0
_ERROR_HIDE_S = 2.0

_PURPLE_GRADIENT = ("#A78BFA", "#6D28D9", "#2E1065")
_RED_GRADIENT = ("#F1948A", "#C0392B", "#641E16")
_BAR_PURPLE = "#8B5CF6"
_LISTEN_STYLES = {
    "weak": ("#F39C12", "⚠️ Áudio fraco"),
    "loud": ("#E74C3C", "⚠️ Volume alto"),
    "ok": ("#8B5CF6", "🎙️ Ouvindo..."),
}


def _hex_to_nscolor(hex_color: str, alpha: float = 1.0) -> NSColor:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithRed_green_blue_alpha_(r, g, b, alpha)


class _OrbView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(_OrbView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._lock = threading.Lock()
        self._classifier = RecentPeakClassifier()
        self._t0 = time.monotonic()
        self._reset_state()
        return self

    def _reset_state(self):
        self._state = "listening"
        self._bars = [_BAR_MIN_H] * _BAR_COUNT
        self._bar_color = _BAR_PURPLE
        self._label = "🎙️ Ouvindo..."
        self._pending_rms = 0.0
        self._level = 0.0

    def reset(self):
        with self._lock:
            self._reset_state()
            self._classifier.reset()

    def freeze(self):
        with self._lock:
            self._state = "transcribing"
            self._label = "⏳ Transcrevendo..."

    def set_error(self, message: str):
        with self._lock:
            self._state = "error"
            self._label = first_line(message)

    def drawRect_(self, rect):
        with self._lock:
            if self._state == "listening":
                self._advance(self._pending_rms)
            state = self._state
            bars = list(self._bars)
            bar_color = self._bar_color
            label = self._label
            level = self._level
        elapsed = time.monotonic() - self._t0
        self._draw_background(rect)
        self._draw_orb(state, level, elapsed)
        self._draw_bars(bars, bar_color, state)
        self._draw_label(label, state)

    @objc.python_method
    def _advance(self, rms: float):
        self._level = rms_to_level(rms)
        color, label = _LISTEN_STYLES[self._classifier.classify(rms)]
        height = _BAR_MIN_H + self._level * (_BAR_MAX_H - _BAR_MIN_H)
        self._bars.pop(0)
        self._bars.append(height)
        self._bar_color = color
        self._label = label

    def _draw_background(self, rect):
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)
        bg = NSColor.colorWithRed_green_blue_alpha_(0.1, 0.1, 0.18, 0.92)
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            rect, 12.0, 12.0
        )
        bg.set()
        path.fill()

    def _draw_orb(self, state, level, elapsed):
        gradient_hex = _RED_GRADIENT if state == "error" else _PURPLE_GRADIENT
        radius = _ORB_RADIUS * orb_scale(level if state == "listening" else 0.0)
        self._draw_glow(gradient_hex[1], level, radius)
        self._draw_sphere(gradient_hex, radius)
        if state == "listening":
            self._draw_ring(elapsed)
        if state == "transcribing":
            self._draw_rotor(elapsed, radius)

    def _draw_glow(self, hex_color, level, radius):
        glow = _hex_to_nscolor(hex_color, orb_glow(level) * 0.35)
        glow.set()
        r = radius + 8.0
        NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(_ORB_CX - r, _ORB_CY - r, r * 2, r * 2)
        ).fill()

    def _draw_sphere(self, gradient_hex, radius):
        colors = [_hex_to_nscolor(h) for h in gradient_hex]
        gradient = NSGradient.alloc().initWithColors_atLocations_colorSpace_(
            colors, [0.0, 0.6, 1.0], NSColorSpace.genericRGBColorSpace()
        )
        oval = NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(
                _ORB_CX - radius, _ORB_CY - radius, radius * 2, radius * 2
            )
        )
        gradient.drawInBezierPath_relativeCenterPosition_(
            oval, NSMakePoint(-0.3, 0.3)
        )

    def _draw_ring(self, elapsed):
        progress = ring_progress(elapsed)
        radius = _ORB_RADIUS + progress * _RING_SPAN
        ring = NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(
                _ORB_CX - radius, _ORB_CY - radius, radius * 2, radius * 2
            )
        )
        ring.setLineWidth_(2.0)
        _hex_to_nscolor(_BAR_PURPLE, 0.7 * (1.0 - progress)).set()
        ring.stroke()

    def _draw_rotor(self, elapsed, radius):
        angle = math.radians(rotation_angle(elapsed))
        hx = _ORB_CX + math.cos(angle) * radius * 0.55
        hy = _ORB_CY + math.sin(angle) * radius * 0.55
        _hex_to_nscolor(_PURPLE_GRADIENT[0], 0.9).set()
        NSBezierPath.bezierPathWithOvalInRect_(
            NSMakeRect(hx - 4.0, hy - 4.0, 8.0, 8.0)
        ).fill()

    def _draw_bars(self, bars, bar_color, state):
        alpha = 0.4 if state != "listening" else 0.85
        _hex_to_nscolor(bar_color, alpha).set()
        gap = (_BARS_X1 - _BARS_X0 - _BAR_W * _BAR_COUNT) / (_BAR_COUNT - 1)
        for i, h in enumerate(bars):
            x = _BARS_X0 + i * (_BAR_W + gap)
            y = _ORB_CY - h / 2
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, y, _BAR_W, h), 2.5, 2.5
            ).fill()

    def _draw_label(self, label, state):
        color = "#F1948A" if state == "error" else "#FFFFFF"
        attrs = {
            NSFontAttributeName: NSFont.systemFontOfSize_(11.0),
            NSForegroundColorAttributeName: _hex_to_nscolor(color, 0.9),
        }
        text = NSAttributedString.alloc().initWithString_attributes_(
            label, attrs
        )
        text.drawAtPoint_(NSMakePoint(12.0, _WIN_H - 18.0))


class OrbOverlay:
    def __init__(self):
        visible = NSScreen.mainScreen().visibleFrame()
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
        self._view = _OrbView.alloc().initWithFrame_(
            NSMakeRect(0, 0, _WIN_W, _WIN_H)
        )
        self._window.setContentView_(self._view)
        self._timer = None
        self._error_timer = None
        self._hiding = False

    def show(self):
        self._cancel_error_timer()
        self._hiding = False
        self._view.reset()
        self._window.orderFront_(None)
        self._start_timer()

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
        with self._view._lock:
            self._view._pending_rms = rms

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
    # Fumaça manual: python -m src.macos.orb_overlay
    # 0-5s ouvindo com voz sintética; 5-7s transcrevendo; 7-9s erro; sai.
    from AppKit import NSApplication

    app = NSApplication.sharedApplication()
    overlay = OrbOverlay()
    overlay.show()
    t0 = time.monotonic()
    phase = {"n": 0}

    def feed(timer):
        t = time.monotonic() - t0
        if t < 5.0:
            overlay.update_bars(0.02 + 0.018 * math.sin(t * 6.0))
            return
        _advance_phase(t)

    def _advance_phase(t):
        if phase["n"] == 0:
            phase["n"] = 1
            overlay.set_transcribing()
        elif phase["n"] == 1:
            _maybe_show_error(t)
        else:
            _maybe_terminate(t)

    def _maybe_show_error(t):
        if t > 7.0:
            phase["n"] = 2
            overlay.show_error("Erro de exemplo: 401 Invalid API Key")

    def _maybe_terminate(t):
        if t > 10.0:
            app.terminate_(None)

    NSTimer.scheduledTimerWithTimeInterval_repeats_block_(0.03, True, feed)
    app.run()
