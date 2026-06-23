import threading

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
    NSForegroundColorAttributeName,
    NSMakeRect,
    NSScreen,
    NSView,
    NSWindow,
    NSWindowStyleMaskBorderless,
)

from src.bar_color import bar_color

_BAR_COUNT = 30
_WIN_W = 320
_WIN_H = 80
_BAR_MAX_H = 48
_BAR_MIN_H = 4
_MARGIN_LEFT = 16


def _hex_to_nscolor(hex_color: str) -> NSColor:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithRed_green_blue_alpha_(r, g, b, 1.0)


class _WaveformView(NSView):
    def initWithFrame_(self, frame):
        self = objc.super(_WaveformView, self).initWithFrame_(frame)
        if self is None:
            return None
        self._bars = [_BAR_MIN_H] * _BAR_COUNT
        self._color_hex = "#4A90E2"
        self._label = "🎙️ Ouvindo..."
        self._transcribing = False
        self._lock = threading.Lock()
        self._pending_rms = 0.0
        return self

    def drawRect_(self, rect):
        rms = self._pending_rms
        self._apply_rms(rms)
        self._draw_content(rect)

    def _apply_rms(self, rms: float):
        with self._lock:
            if self._transcribing:
                return
            height = min(max(rms * 120, _BAR_MIN_H), _BAR_MAX_H)
            color_hex, label = bar_color(rms)
            self._bars.pop(0)
            self._bars.append(height)
            self._color_hex = color_hex
            self._label = label

    def freeze(self):
        with self._lock:
            self._transcribing = True
            self._label = "⏳ Transcrevendo..."
        self.setNeedsDisplay_(True)

    def reset(self):
        with self._lock:
            self._bars = [_BAR_MIN_H] * _BAR_COUNT
            self._transcribing = False
            self._label = "🎙️ Ouvindo..."
            self._color_hex = "#4A90E2"

    def _draw_content(self, rect):
        NSColor.clearColor().set()
        NSBezierPath.fillRect_(rect)

        bg = NSColor.colorWithRed_green_blue_alpha_(0.1, 0.1, 0.18, 0.92)
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            rect, 12.0, 12.0
        )
        bg.set()
        path.fill()

        with self._lock:
            bars = list(self._bars)
            color_hex = self._color_hex
            label = self._label
            transcribing = self._transcribing

        self._draw_bars(bars, color_hex, transcribing)
        self._draw_label(label)

    def _draw_bars(self, bars, color_hex, transcribing):
        bar_color_ns = _hex_to_nscolor(color_hex)
        if transcribing:
            bar_color_ns = bar_color_ns.colorWithAlphaComponent_(0.4)
        bar_color_ns.set()

        bar_w = 6.0
        gap = (_WIN_W - _MARGIN_LEFT * 2 - bar_w * _BAR_COUNT) / (_BAR_COUNT - 1)
        center_y = _WIN_H / 2

        for i, h in enumerate(bars):
            x = _MARGIN_LEFT + i * (bar_w + gap)
            y = center_y - h / 2
            bar_rect = NSMakeRect(x, y, bar_w, h)
            bar_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                bar_rect, 3.0, 3.0
            )
            bar_path.fill()

    def _draw_label(self, label):
        font = NSFont.systemFontOfSize_(11.0)
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: NSColor.colorWithWhite_alpha_(0.85, 1.0),
        }
        ns_label = NSAttributedString.alloc().initWithString_attributes_(label, attrs)
        ns_label.drawAtPoint_(NSMakeRect(12, _WIN_H - 18, 0, 0).origin)


class WaveformOverlay:
    def __init__(self):
        visible = NSScreen.mainScreen().visibleFrame()
        x = visible.origin.x + 20
        y = visible.origin.y + visible.size.height - _WIN_H - 20

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, _WIN_W, _WIN_H),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(NSFloatingWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(True)

        self._view = _WaveformView.alloc().initWithFrame_(
            NSMakeRect(0, 0, _WIN_W, _WIN_H)
        )
        self._window.setContentView_(self._view)

    def show(self):
        self._view.reset()
        self._window.orderFront_(None)

    def hide(self):
        NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda ctx: (ctx.setDuration_(0.3), self._window.animator().setAlphaValue_(0.0)),
            lambda: self._window.orderOut_(None) or self._window.setAlphaValue_(1.0),
        )

    def set_transcribing(self):
        self._view.freeze()

    def update_bars(self, rms: float):
        # Armazena rms e dispara redraw no main thread sem passar float como NSObject
        self._view._pending_rms = rms
        self._view.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setNeedsDisplay:", True, False
        )
