# Orb Overlay (Orbe + Barras, mockup D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o overlay de barras azul por uma orbe roxa pulsante estilo assistente de IA (mockup D aprovado) com barras discretas ao lado e estados ouvindo/transcrevendo/erro.

**Architecture:** Matemática de animação pura (escala, brilho, anel, rotação, primeira linha de erro) nasce em `src/core/orb_animation.py` com TDD e 100% de cobertura. O desenho AppKit vive em `src/macos/orb_overlay.py` (novo layer `macos/`, primeiro módulo no caminho final), dirigido por um NSTimer de 30fps — o callback de áudio só armazena o RMS sob lock. `src/waveform_overlay.py` é deletado (LEI 6).

**Tech Stack:** Python 3.11, pyobjc (AppKit/Foundation), pytest, ruff.

## Global Constraints

- TDD obrigatório: teste falha ANTES da implementação (LEI 2)
- `src/core/` é puro: proibido importar AppKit/Foundation/objc; 100% de cobertura nos módulos core
- Complexidade ciclomática ≤ 4 por método (ruff já configura `Metrics`); `ruff check src tests` limpo
- Camada `src/macos/` (AppKit) não tem teste unitário — validação por fumaça manual documentada
- Strings de UI exatas: `"🎙️ Ouvindo..."`, `"⏳ Transcrevendo..."`, `"⚠️ Áudio fraco"`, `"⚠️ Volume alto"`
- Estados do overlay (spec): **listening** (orbe roxa, escala 0.9→1.12 e brilho proporcionais ao nível, anel expandindo em loop), **transcribing** (rotação lenta, barras congeladas a 40% de alpha), **error** (orbe vermelha por 2 s + primeira linha da mensagem, depois fade-out)
- Janela: borderless, flutuante, canto superior esquerdo, mesmo mecanismo thread-safe (lock + redraw no main thread)
- Reusar `src/core/audio_level.py`: `rms_to_level(rms) -> float 0..1` e `RecentPeakClassifier().classify(rms) -> "weak"|"ok"|"loud"` (janela de 1.5s — NÃO reintroduzir classificação instantânea)
- Git: commits frequentes; o hook `rtk` mangla args de git — se `git <cmd>` falhar com erro estranho, usar `rtk proxy git <cmd>`
- O app deve continuar funcionando de ponta a ponta após cada task (o commit da Task 2 ainda não liga o orbe — waveform antigo segue ativo até a Task 3)

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `src/core/orb_animation.py` (novo) | Matemática pura da animação: escala/brilho por nível, fase do anel, ângulo de rotação, primeira linha da mensagem de erro |
| `tests/core/test_orb_animation.py` (novo) | TDD do módulo acima |
| `src/macos/__init__.py` (novo) | Pacote da camada AppKit |
| `src/macos/orb_overlay.py` (novo) | Janela + view da orbe; estados; timer 30fps; demo standalone via `python -m src.macos.orb_overlay` |
| `src/app.py` (modificar) | Troca WaveformOverlay→OrbOverlay; erro do pipeline também vai para o overlay |
| `src/waveform_overlay.py` (deletar) | Substituído pelo orb_overlay |
| `README.md` / `README.pt-BR.md` (modificar) | Feature de waveform vira orbe; remove orbe do roadmap |
| `docs/STATUS.md` (modificar) | Checkpoint |

---

### Task 1: `core/orb_animation` (TDD)

**Files:**
- Create: `src/core/orb_animation.py`
- Test: `tests/core/test_orb_animation.py`

**Interfaces:**
- Consumes: nada (módulo puro, stdlib apenas)
- Produces (usado pela Task 2, assinaturas exatas):
  - `orb_scale(level: float) -> float` — 0.0→0.9, 1.0→1.12, linear
  - `orb_glow(level: float) -> float` — 0.0→0.35, 1.0→1.0, linear
  - `ring_progress(elapsed: float) -> float` — fase 0..1 em loop de `RING_PERIOD_S = 1.2`
  - `rotation_angle(elapsed: float) -> float` — graus 0..360 em loop de `ROTATION_PERIOD_S = 4.0`
  - `first_line(message: str, max_chars: int = 60) -> str` — primeira linha, truncada com `…`
  - Constantes: `ORB_SCALE_MIN = 0.9`, `ORB_SCALE_MAX = 1.12`, `GLOW_MIN = 0.35`, `GLOW_MAX = 1.0`, `RING_PERIOD_S = 1.2`, `ROTATION_PERIOD_S = 4.0`

- [ ] **Step 1: Write the failing tests**

```python
# tests/core/test_orb_animation.py
import pytest

from src.core.orb_animation import (
    first_line,
    orb_glow,
    orb_scale,
    ring_progress,
    rotation_angle,
)


def test_orb_scale_e_linear_entre_09_e_112():
    assert orb_scale(0.0) == pytest.approx(0.9)
    assert orb_scale(0.5) == pytest.approx(1.01)
    assert orb_scale(1.0) == pytest.approx(1.12)


def test_orb_glow_e_linear_entre_035_e_1():
    assert orb_glow(0.0) == pytest.approx(0.35)
    assert orb_glow(1.0) == pytest.approx(1.0)


def test_ring_progress_faz_loop_de_12s():
    assert ring_progress(0.0) == pytest.approx(0.0)
    assert ring_progress(0.6) == pytest.approx(0.5)
    assert ring_progress(1.2) == pytest.approx(0.0)
    assert ring_progress(1.8) == pytest.approx(0.5)


def test_rotation_angle_faz_loop_de_4s_em_360_graus():
    assert rotation_angle(0.0) == pytest.approx(0.0)
    assert rotation_angle(2.0) == pytest.approx(180.0)
    assert rotation_angle(4.0) == pytest.approx(0.0)


def test_first_line_pega_so_a_primeira_linha():
    assert first_line("401 Invalid API Key\nstack trace...") == "401 Invalid API Key"


def test_first_line_trunca_com_reticencias():
    longa = "x" * 100
    assert first_line(longa) == "x" * 59 + "…"
    assert len(first_line(longa)) == 60


def test_first_line_curta_fica_intacta():
    assert first_line("curta") == "curta"


def test_first_line_vazia_devolve_vazio():
    assert first_line("") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/core/test_orb_animation.py -q`
Expected: FAIL na coleta com `ModuleNotFoundError: No module named 'src.core.orb_animation'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/orb_animation.py
"""Matemática pura da animação da orbe (mockup D). Sem AppKit."""

ORB_SCALE_MIN = 0.9
ORB_SCALE_MAX = 1.12
GLOW_MIN = 0.35
GLOW_MAX = 1.0
RING_PERIOD_S = 1.2
ROTATION_PERIOD_S = 4.0


def orb_scale(level: float) -> float:
    return ORB_SCALE_MIN + level * (ORB_SCALE_MAX - ORB_SCALE_MIN)


def orb_glow(level: float) -> float:
    return GLOW_MIN + level * (GLOW_MAX - GLOW_MIN)


def ring_progress(elapsed: float) -> float:
    return (elapsed % RING_PERIOD_S) / RING_PERIOD_S


def rotation_angle(elapsed: float) -> float:
    return (elapsed % ROTATION_PERIOD_S) / ROTATION_PERIOD_S * 360.0


def first_line(message: str, max_chars: int = 60) -> str:
    lines = message.splitlines()
    line = lines[0] if lines else ""
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 1] + "…"
```

- [ ] **Step 4: Run tests to verify they pass (com cobertura)**

Run: `.venv/bin/python -m pytest tests/core/test_orb_animation.py -q --cov=src/core/orb_animation`
Expected: `8 passed`, cobertura `100%` no módulo

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check src/core/orb_animation.py tests/core/test_orb_animation.py`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add src/core/orb_animation.py tests/core/test_orb_animation.py
git commit -m "feat: matemática pura da animação da orbe (escala, brilho, anel, rotação)"
```

---

### Task 2: `macos/orb_overlay` (AppKit + demo standalone)

**Files:**
- Create: `src/macos/__init__.py` (vazio)
- Create: `src/macos/orb_overlay.py`

**Interfaces:**
- Consumes: `src.core.orb_animation` (Task 1, assinaturas acima); `src.core.audio_level.rms_to_level` e `RecentPeakClassifier`
- Produces (usado pela Task 3): classe `OrbOverlay` com métodos `show()`, `hide()`, `set_transcribing()`, `update_bars(rms: float)`, `show_error(message: str)` — todos chamados no main thread, EXCETO `update_bars`, que vem do thread de áudio e só armazena o RMS sob lock

Sem teste unitário (camada AppKit) — a validação é o modo demo do Step 2.

- [ ] **Step 1: Write the module**

```python
# src/macos/orb_overlay.py
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
        gradient = NSGradient.alloc().initWithColorsAndLocations_(
            colors[0], 0.0, colors[1], 0.6, colors[2], 1.0
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

    def show(self):
        self._view.reset()
        self._window.orderFront_(None)
        self._start_timer()

    def hide(self):
        self._stop_timer()

        def animate(ctx):
            ctx.setDuration_(0.3)
            self._window.animator().setAlphaValue_(0.0)

        def complete():
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
        NSTimer.scheduledTimerWithTimeInterval_repeats_block_(
            _ERROR_HIDE_S, False, lambda timer: self.hide()
        )

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
        elif phase["n"] == 0:
            phase["n"] = 1
            overlay.set_transcribing()
        elif t > 7.0 and phase["n"] == 1:
            phase["n"] = 2
            overlay.show_error("Erro de exemplo: 401 Invalid API Key")
        elif t > 10.0:
            app.terminate_(None)

    NSTimer.scheduledTimerWithTimeInterval_repeats_block_(0.03, True, feed)
    app.run()
```

E criar `src/macos/__init__.py` vazio:

```bash
touch src/macos/__init__.py
```

- [ ] **Step 2: Run the demo (fumaça manual)**

Run: `.venv/bin/python -m src.macos.orb_overlay`
Expected: janela flutuante no canto superior esquerdo por ~10s mostrando, em sequência: (1) orbe roxa pulsando com anel expandindo e ~20 barras roxas se movendo com o "áudio" sintético + "🎙️ Ouvindo..."; (2) ponto claro orbitando a orbe com barras congeladas esmaecidas + "⏳ Transcrevendo..."; (3) orbe vermelha + "Erro de exemplo: 401 Invalid API Key" por 2s com fade-out. O processo termina sozinho.

Se algum estado não aparecer como descrito, corrigir antes de commitar.

- [ ] **Step 3: Confirmar que a suíte e o lint continuam verdes**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: todos os testes passam (o módulo novo não é importado por nenhum teste), `All checks passed!`

- [ ] **Step 4: Commit**

```bash
git add src/macos/__init__.py src/macos/orb_overlay.py
git commit -m "feat: overlay Orbe + Barras (mockup D) com estados ouvindo/transcrevendo/erro"
```

---

### Task 3: Integrar OrbOverlay no app e deletar o waveform antigo

**Files:**
- Modify: `src/app.py` (import na linha 33, `__init__` linha 82, `showErrorOnMainThread_` linhas 70-71, `finishRecordingOnMainThread` linhas 64-68)
- Delete: `src/waveform_overlay.py`
- Modify: `README.md`, `README.pt-BR.md`, `docs/STATUS.md`

**Interfaces:**
- Consumes: `OrbOverlay` da Task 2 (`show()`, `hide()`, `set_transcribing()`, `update_bars(rms)`, `show_error(message)`)
- Produces: app final usando a orbe; nenhum consumidor posterior

- [ ] **Step 1: Trocar o overlay no app.py**

Substituir o import:

```python
# antes
from src.waveform_overlay import WaveformOverlay
# depois
from src.macos.orb_overlay import OrbOverlay
```

No `__init__` de `VozMenuBar`:

```python
# antes
self._overlay = WaveformOverlay()
# depois
self._overlay = OrbOverlay()
```

- [ ] **Step 2: Erro do pipeline também aparece no overlay**

No `MainThreadDispatcher`, substituir os dois métodos:

```python
def finishRecordingOnMainThread(self):
    if self._app._had_error:
        # overlay em estado de erro se esconde sozinho após 2s;
        # ícone ⚠️ e item "Último erro" permanecem no menu
        return
    self._app._overlay.hide()
    self._app._set_title(ICON_IDLE)
    self._app._error_item.setHidden_(True)

def showErrorOnMainThread_(self, message):
    self._app._show_error(str(message))
    self._app._overlay.show_error(str(message))
```

(A ordem já garante `_had_error=True` antes de `finishRecordingOnMainThread`, porque `showErrorOnMainThread:` é enfileirado antes no `_handle_recording`.)

- [ ] **Step 3: Deletar o waveform antigo e verificar referências**

```bash
git rm src/waveform_overlay.py
grep -rn "waveform_overlay\|WaveformOverlay" src tests docs/STATUS.md || echo "sem referências"
```

Expected: nenhuma referência restante em `src/` e `tests/` (referências em `docs/superpowers/` históricos podem ficar). Se `docs/STATUS.md` mencionar, atualizar no Step 5.

- [ ] **Step 4: Suíte + lint + fumaça real**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: todos os testes passam, lint limpo.

Fumaça real (matar instância antiga antes — o lock de instância única bloqueia a segunda):

```bash
pkill -f "src.app" || true
sleep 1
.venv/bin/python -u -m src.app > /tmp/sagmowhisper.log 2>&1 &
sleep 3
pgrep -fl "src.app"
```

Expected: processo vivo, ícone 🎙️ na barra. (O teste de F8 com voz real fica para o humano; documentar isso no report.)

- [ ] **Step 5: Atualizar docs**

`README.md`: no bullet de features, substituir a linha do waveform por:

```markdown
- **Live orb overlay** — a pulsing AI-assistant-style orb with dB-scaled bars and weak/loud signal warnings
```

E no Roadmap, remover "pulsing-orb overlay, " da linha (mantendo pipx/CI).

`README.pt-BR.md`: bullet equivalente:

```markdown
- **Orbe ao vivo** — orbe pulsante estilo assistente de IA com barras em escala dB e avisos de sinal fraco/alto
```

E remover "overlay com orbe pulsante," do Roadmap (mantendo pipx/CI).

`docs/STATUS.md`: registrar a entrega do orb overlay (arquivos novos `src/core/orb_animation.py`, `src/macos/orb_overlay.py`; deletado `src/waveform_overlay.py`; estado dos testes) e que a próxima etapa é o milestone de Providers + Configurações.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: app usa overlay Orbe + Barras; remove waveform antigo"
```
