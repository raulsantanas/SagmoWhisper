# Waveform Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exibir janela flutuante nativa macOS com waveform em tempo real durante gravação F8, com alertas visuais de qualidade de áudio.

**Architecture:** Novo `WaveformOverlay` (NSWindow + NSView via AppKit/PyObjC) isolado em `src/waveform_overlay.py`. `AudioRecorder` ganha callback de RMS. `app.py` orquestra show/hide do overlay nos eventos de F8.

**Tech Stack:** PyObjC (AppKit, Foundation), numpy (já instalado), sounddevice (já instalado), pytest.

## Global Constraints

- Python 3.11, macOS only
- Complexidade ciclomática ≤ 4 por método (ruff mccabe)
- Sem novas dependências (AppKit e numpy já estão no venv)
- TDD: teste RED antes de qualquer implementação
- Pytest runner: `cd voz && source .venv/bin/activate && pytest`
- Arquivos de teste em `tests/`, src em `src/`

---

## File Map

| Ação | Arquivo | Responsabilidade |
|------|---------|-----------------|
| Criar | `src/waveform_overlay.py` | NSWindow + NSView + lógica de cor/estado |
| Criar | `src/bar_color.py` | Função pura: RMS → cor hex (testável sem AppKit) |
| Modificar | `src/audio_recorder.py` | Aceitar `sample_callback`, chamar com RMS |
| Modificar | `src/app.py` | Instanciar overlay, conectar eventos F8 |
| Criar | `tests/test_bar_color.py` | Testes unitários de cor por RMS |
| Criar | `tests/test_audio_recorder_callback.py` | Testa que callback é chamado com float |

---

## Task 1: Lógica de cor isolada (TDD puro)

**Files:**
- Create: `src/bar_color.py`
- Create: `tests/test_bar_color.py`

**Interfaces:**
- Produces: `bar_color(rms: float) -> tuple[str, str]` — retorna `(hex_color, label)` onde label é o texto do estado

- [ ] **Step 1: Escrever o teste RED**

```python
# tests/test_bar_color.py
from src.bar_color import bar_color


def test_normal_volume_returns_blue():
    color, label = bar_color(0.3)
    assert color == "#4A90E2"
    assert label == "🎙️ Ouvindo..."


def test_high_volume_returns_red():
    color, label = bar_color(0.7)
    assert color == "#E74C3C"
    assert label == "⚠️ Volume alto"


def test_low_volume_returns_yellow():
    color, label = bar_color(0.01)
    assert color == "#F39C12"
    assert label == "⚠️ Áudio fraco"


def test_boundary_high_is_inclusive():
    color, label = bar_color(0.6)
    assert color == "#E74C3C"


def test_boundary_low_is_exclusive():
    color, label = bar_color(0.02)
    assert color == "#4A90E2"
```

- [ ] **Step 2: Rodar e verificar FAIL**

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && source .venv/bin/activate && pytest tests/test_bar_color.py -v
```
Esperado: `ERROR` — `ModuleNotFoundError: No module named 'src.bar_color'`

- [ ] **Step 3: Implementar `src/bar_color.py`**

```python
def bar_color(rms: float) -> tuple[str, str]:
    if rms >= 0.6:
        return "#E74C3C", "⚠️ Volume alto"
    if rms < 0.02:
        return "#F39C12", "⚠️ Áudio fraco"
    return "#4A90E2", "🎙️ Ouvindo..."
```

- [ ] **Step 4: Rodar e verificar PASS**

```bash
pytest tests/test_bar_color.py -v
```
Esperado: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/bar_color.py tests/test_bar_color.py
git commit -m "feat: add bar_color logic with audio quality thresholds"
```

---

## Task 2: sample_callback no AudioRecorder (TDD)

**Files:**
- Modify: `src/audio_recorder.py`
- Create: `tests/test_audio_recorder_callback.py`

**Interfaces:**
- Consumes: nada de tasks anteriores
- Produces: `AudioRecorder(sample_rate, sample_callback=None)` — callback chamado com `float` RMS a cada bloco de áudio

- [ ] **Step 1: Escrever o teste RED**

```python
# tests/test_audio_recorder_callback.py
import numpy as np
from unittest.mock import MagicMock, patch


def test_sample_callback_called_with_float_rms():
    callback = MagicMock()

    with patch("sounddevice.InputStream") as mock_stream_cls:
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000, sample_callback=callback)

        # Simula bloco de áudio chegando
        indata = np.array([[0.3], [0.4], [0.5]], dtype=np.float32)
        recorder._on_audio(indata, 3, None, None)

    assert callback.called
    rms_value = callback.call_args[0][0]
    assert isinstance(rms_value, float)
    assert rms_value > 0.0


def test_no_callback_does_not_raise():
    with patch("sounddevice.InputStream"):
        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000)
        indata = np.array([[0.3]], dtype=np.float32)
        recorder._on_audio(indata, 1, None, None)  # não deve lançar exceção
```

- [ ] **Step 2: Rodar e verificar FAIL**

```bash
pytest tests/test_audio_recorder_callback.py -v
```
Esperado: `FAILED` — `TypeError: __init__() got an unexpected keyword argument 'sample_callback'`

- [ ] **Step 3: Modificar `src/audio_recorder.py`**

Substitua o `__init__` e o `_on_audio`:

```python
import queue
import tempfile
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    def __init__(self, sample_rate: int, sample_callback: Callable | None = None):
        self._sample_rate = sample_rate
        self._sample_callback = sample_callback
        self._queue: queue.Queue = queue.Queue()
        self._stream = None

    def start(self) -> None:
        self._queue = queue.Queue()
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self) -> Path:
        self._stream.stop()
        self._stream.close()
        self._stream = None
        return self._write_wav(self._drain())

    def _on_audio(self, indata, frames, time, status):
        self._queue.put(indata.copy())
        if self._sample_callback is not None:
            rms = float(np.sqrt(np.mean(indata ** 2)))
            self._sample_callback(rms)

    def _drain(self) -> list:
        blocks = []
        while not self._queue.empty():
            blocks.append(self._queue.get())
        return blocks

    def _write_wav(self, blocks: list) -> Path:
        path = Path(tempfile.gettempdir()) / "voz_recording.wav"
        audio = np.concatenate(blocks) if blocks else np.zeros((1, 1))
        sf.write(path, audio, self._sample_rate)
        return path
```

- [ ] **Step 4: Rodar e verificar PASS**

```bash
pytest tests/test_audio_recorder_callback.py -v
```
Esperado: 2 passed

- [ ] **Step 5: Rodar suite completa para checar regressões**

```bash
pytest -v
```
Esperado: todos os testes anteriores ainda passando

- [ ] **Step 6: Commit**

```bash
git add src/audio_recorder.py tests/test_audio_recorder_callback.py
git commit -m "feat: add sample_callback to AudioRecorder for real-time RMS"
```

---

## Task 3: WaveformOverlay — janela flutuante AppKit

**Files:**
- Create: `src/waveform_overlay.py`

**Interfaces:**
- Consumes: `bar_color(rms) -> tuple[str, str]` de `src/bar_color.py`
- Produces:
  - `WaveformOverlay()` — construtor sem args
  - `WaveformOverlay.show()` — exibe janela, inicia animação
  - `WaveformOverlay.hide()` — fade out 0.3s e esconde
  - `WaveformOverlay.set_transcribing()` — congela barras, muda label
  - `WaveformOverlay.update_bars(rms: float)` — atualiza barras com novo RMS

> **Nota:** NSView/NSWindow não podem ser testados com pytest puro (requerem display). Os testes de estado lógico ficam em `bar_color`. A Task 3 é implementada e validada manualmente (Step 5).

- [ ] **Step 1: Criar `src/waveform_overlay.py`**

```python
import threading

import numpy as np
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSMakeRect,
    NSView,
    NSWindow,
    NSWindowStyleMaskBorderless,
)
from Foundation import NSTimer

from src.bar_color import bar_color

_BAR_COUNT = 30
_WIN_W = 320
_WIN_H = 80
_BAR_MAX_H = 48
_BAR_MIN_H = 4
_MARGIN_LEFT = 16
_MARGIN_TOP = 28


def _hex_to_nscolor(hex_color: str) -> NSColor:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithRed_green_blue_alpha_(r, g, b, 1.0)


class _WaveformView(NSView):
    def initWithFrame_(self, frame):
        self = super().initWithFrame_(frame)
        if self is None:
            return None
        self._bars = [_BAR_MIN_H] * _BAR_COUNT
        self._color_hex = "#4A90E2"
        self._label = "🎙️ Ouvindo..."
        self._transcribing = False
        self._lock = threading.Lock()
        return self

    def initWithFrame_(self, frame):
        self = super().initWithFrame_(frame)
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
        self._draw(rect)

    def _apply_rms(self, rms: float):
        height = min(max(rms * 120, _BAR_MIN_H), _BAR_MAX_H)
        color_hex, label = bar_color(rms)
        with self._lock:
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

    def _draw(self, rect):
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

        font = NSFont.systemFontOfSize_(11.0)
        attrs = {
            "NSFont": font,
            "NSForegroundColorAttributeName": NSColor.colorWithWhite_alpha_(0.85, 1.0),
        }
        from AppKit import NSAttributedString
        ns_label = NSAttributedString.alloc().initWithString_attributes_(label, attrs)
        ns_label.drawAtPoint_(NSMakeRect(12, _WIN_H - 18, 0, 0).origin)


class WaveformOverlay:
    def __init__(self):
        screen_frame = NSWindow.alloc() \
            .initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, 1, 1),
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
            ).screen().frame()

        x = screen_frame.origin.x + 20
        y = screen_frame.origin.y + screen_frame.size.height - _WIN_H - 48

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
        self._window.orderOut_(None)

    def set_transcribing(self):
        self._view.freeze()

    def update_bars(self, rms: float):
        # Armazena rms e dispara redraw no main thread sem passar float como NSObject
        self._view._pending_rms = rms
        self._view.performSelectorOnMainThread_withObject_waitUntilDone_(
            "setNeedsDisplay:", True, False
        )
```

- [ ] **Step 2: Verificar imports sem erros**

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && source .venv/bin/activate && \
PYTHONPATH="$(pwd):$(pwd)/.venv/lib/python3.11/site-packages" \
/usr/local/Cellar/python@3.11/3.11.15_1/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python \
-c "from src.waveform_overlay import WaveformOverlay; print('ok')"
```
Esperado: `ok`

- [ ] **Step 3: Rodar suite de testes para checar regressões**

```bash
pytest -v
```
Esperado: todos os testes anteriores passando (waveform_overlay não tem teste unitário próprio)

- [ ] **Step 4: Commit**

```bash
git add src/waveform_overlay.py src/bar_color.py
git commit -m "feat: add WaveformOverlay AppKit window with real-time bar visualization"
```

---

## Task 4: Integrar overlay no app.py

**Files:**
- Modify: `src/app.py`

**Interfaces:**
- Consumes:
  - `WaveformOverlay()` de `src/waveform_overlay.py`
  - `AudioRecorder(sample_rate, sample_callback)` de `src/audio_recorder.py`
  - `WaveformOverlay.show()`, `.hide()`, `.set_transcribing()`, `.update_bars(rms)`

- [ ] **Step 1: Substituir `src/app.py` completo**

```python
import threading

import rumps
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
from groq import Groq
from pynput import keyboard

from src.audio_recorder import AudioRecorder
from src.cleaner import Cleaner
from src.config import Config
from src.pipeline import DictationPipeline
from src.text_injector import TextInjector
from src.transcriber import Transcriber
from src.waveform_overlay import WaveformOverlay

ICON_IDLE = "🎙️"
ICON_RECORDING = "🔴"
ICON_PROCESSING = "⏳"


class VozMenuBar(rumps.App):
    def __init__(self, config: Config):
        super().__init__(ICON_IDLE, quit_button="Sair")
        self._config = config
        self._recording = False
        self._overlay = WaveformOverlay()
        client = Groq(api_key=config.groq_api_key)
        self._recorder = AudioRecorder(
            config.sample_rate,
            sample_callback=self._overlay.update_bars,
        )
        self._pipeline = DictationPipeline(
            Transcriber(client, config.transcription_model, config.language),
            Cleaner(client, config.cleanup_model),
            TextInjector(),
            config.enable_cleanup,
        )
        self._hotkey = getattr(keyboard.Key, config.hotkey)
        threading.Thread(target=self._start_listener, daemon=True).start()

    def _start_listener(self):
        with keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        ) as listener:
            listener.join()

    def _on_press(self, key):
        if key == self._hotkey and not self._recording:
            self._recording = True
            self.title = ICON_RECORDING
            self._overlay.show()
            self._recorder.start()

    def _on_release(self, key):
        if key == self._hotkey and self._recording:
            self._recording = False
            self._overlay.set_transcribing()
            threading.Thread(target=self._handle_recording, daemon=True).start()

    def _handle_recording(self):
        self.title = ICON_PROCESSING
        audio_path = self._recorder.stop()
        self._pipeline.run(audio_path)
        self._overlay.hide()
        self.title = ICON_IDLE


def main():
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory
    )
    VozMenuBar(Config.from_env()).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar suite completa**

```bash
pytest -v
```
Esperado: todos passando

- [ ] **Step 3: Teste manual — iniciar o app**

```bash
pkill -f "src.app" 2>/dev/null
source .venv/bin/activate && \
PYTHONPATH="$(pwd):$(pwd)/.venv/lib/python3.11/site-packages" \
/usr/local/Cellar/python@3.11/3.11.15_1/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python \
-m src.app &
```

- [ ] **Step 4: Verificar comportamento**

1. 🎙️ aparece na barra de menu
2. Segurar F8 → overlay aparece no canto superior esquerdo com barras animadas
3. Falar baixo → barras ficam **amarelas** ("⚠️ Áudio fraco")
4. Falar normal → barras ficam **azuis** ("🎙️ Ouvindo...")
5. Falar alto → barras ficam **vermelhas** ("⚠️ Volume alto")
6. Soltar F8 → overlay muda para "⏳ Transcrevendo..." com barras congeladas
7. Texto é colado → overlay desaparece

- [ ] **Step 5: Commit**

```bash
git add src/app.py
git commit -m "feat: integrate WaveformOverlay into VozMenuBar with real-time feedback"
```
