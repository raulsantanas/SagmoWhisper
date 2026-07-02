# Milestone 1 — Fundação: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir a sensibilidade do waveform (escala dB), tornar erros visíveis (log + ícone + menu), impedir instâncias duplicadas e sanear o git — deixando o app pronto para receber os milestones 2 (providers/settings) e 3 (orbe/lançamento).

**Architecture:** Módulos novos nascem em `src/core/` (puros, multiplataforma, TDD, 100% cobertura); mudanças de UI ficam em `src/app.py` e `src/waveform_overlay.py` (AppKit, fumaça manual). Spec: `docs/superpowers/specs/2026-07-02-sagmowhisper-public-design.md`.

**Tech Stack:** Python 3.11 (`.venv`), pytest, ruff, AppKit via pyobjc, pynput, sounddevice.

## Global Constraints

- Diretório de trabalho: `/Users/raul/Documents/dev/SagmoWhisper/voz` (todos os comandos a partir daqui; usar `.venv/bin/python` e `.venv/bin/ruff`)
- Complexidade ciclomática ≤ 4 por método (LEI 8; `ruff check src tests` deve passar após cada task)
- TDD obrigatório para módulos puros: teste falha ANTES da implementação (LEI 2)
- Suíte inteira verde antes de cada commit: `.venv/bin/python -m pytest -q`
- UI em PT-BR; commits em português no formato `tipo: descrição`
- NUNCA commitar `.env` (já está fora do índice; não usar `git add .env`)
- Branch de trabalho: `feature/voz-mvp-ditado` até a Task 7, que cria `main`

---

### Task 1: Higiene git — remover rumps órfão e commitar a migração AppKit pendente

O working tree tem 6 arquivos modificados (migração rumps→AppKit, funcionando e testada) e o `requirements.txt` adiciona `rumps` que o código não usa mais.

**Files:**
- Modify: `requirements.txt` (remover linha `rumps`)
- Commit: `requirements.txt`, `src/app.py`, `src/cleaner.py`, `src/waveform_overlay.py`, `tests/test_audio_recorder_callback.py`, `tests/test_config.py`, `.env.example`, `docs/superpowers/plans/`, `docs/STATUS.md`

**Interfaces:**
- Consumes: nada
- Produces: working tree limpo para as tasks seguintes

- [ ] **Step 1: Remover a linha `rumps` do requirements.txt**

O arquivo termina hoje com:

```
pytest
pytest-cov
ruff
rumps
pyobjc-framework-Cocoa
```

Deve terminar com:

```
pytest
pytest-cov
ruff
pyobjc-framework-Cocoa
```

- [ ] **Step 2: Verificar que a suíte e o lint continuam verdes**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: `22 passed` e `All checks passed!`

- [ ] **Step 3: Commitar tudo que está pendente**

```bash
git add requirements.txt src/app.py src/cleaner.py src/waveform_overlay.py \
  tests/test_audio_recorder_callback.py tests/test_config.py .env.example \
  docs/superpowers/plans/ docs/STATUS.md
git commit -m "feat: migra barra de menu de rumps para AppKit puro

NSStatusBar + MainThreadDispatcher, notificação de erro, SIGINT,
fade-out do overlay sem lambdas com efeito colateral. Remove rumps
(órfão) do requirements."
git status --short
```

Expected: `git status --short` mostra no máximo arquivos não relacionados (ex.: `.superpowers/`), nenhum `M` em src/tests.

---

### Task 2: `src/core/audio_level.py` — escala dB (TDD)

Corrige a causa raiz do "áudio fraco" constante: percepção de áudio é logarítmica; RMS bruto linear esmaga a voz normal (RMS 0.01–0.05) no fundo da escala.

**Files:**
- Create: `src/core/__init__.py` (vazio)
- Create: `src/core/audio_level.py`
- Create: `tests/core/__init__.py` (vazio)
- Test: `tests/core/test_audio_level.py`

**Interfaces:**
- Consumes: nada
- Produces (usados pela Task 3):
  - `rms_to_db(rms: float) -> float`
  - `rms_to_level(rms: float) -> float` — 0.0..1.0, mapeando −60dB..−10dB
  - `classify(rms: float) -> str` — retorna `"weak"` (< −50dB), `"loud"` (> −6dB) ou `"ok"`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/core/__init__.py` vazio e `tests/core/test_audio_level.py`:

```python
import pytest

from src.core.audio_level import classify, rms_to_db, rms_to_level


def test_rms_to_db_conversao_basica():
    assert rms_to_db(0.1) == pytest.approx(-20.0)
    assert rms_to_db(1.0) == pytest.approx(0.0)


def test_rms_to_db_nao_explode_com_zero():
    assert rms_to_db(0.0) <= -60.0


def test_voz_normal_gera_amplitude_visivel():
    # RMS 0.02 (~-34dB) era invisível na escala linear; em dB deve dar ~52%
    assert rms_to_level(0.02) == pytest.approx(0.52, abs=0.01)


def test_level_clampa_nos_extremos():
    assert rms_to_level(1.0) == 1.0       # 0dB > teto de -10dB
    assert rms_to_level(0.0000001) == 0.0  # abaixo do piso de -60dB


def test_level_e_monotonico():
    assert rms_to_level(0.01) < rms_to_level(0.05) < rms_to_level(0.2)


def test_classify_voz_normal_e_ok():
    assert classify(0.02) == "ok"


def test_classify_silencio_e_weak():
    assert classify(0.001) == "weak"   # ~-60dB


def test_classify_grito_e_loud():
    assert classify(0.6) == "loud"     # ~-4.4dB
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/core/test_audio_level.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.core'`

- [ ] **Step 3: Implementação mínima**

Criar `src/core/__init__.py` vazio e `src/core/audio_level.py`:

```python
import math

DB_FLOOR = -60.0
DB_CEIL = -10.0
WEAK_DB = -50.0
LOUD_DB = -6.0
_EPS = 1e-6


def rms_to_db(rms: float) -> float:
    return 20.0 * math.log10(max(rms, _EPS))


def rms_to_level(rms: float) -> float:
    level = (rms_to_db(rms) - DB_FLOOR) / (DB_CEIL - DB_FLOOR)
    return min(max(level, 0.0), 1.0)


def classify(rms: float) -> str:
    db = rms_to_db(rms)
    if db > LOUD_DB:
        return "loud"
    if db < WEAK_DB:
        return "weak"
    return "ok"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/core/test_audio_level.py -q && .venv/bin/ruff check src tests`
Expected: `9 passed` e `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add src/core/ tests/core/
git commit -m "feat: adiciona audio_level com escala dB (corrige sensibilidade do waveform)"
```

---

### Task 3: Integrar `audio_level` no overlay e remover `bar_color`

**Files:**
- Modify: `src/waveform_overlay.py` (método `_apply_rms`, linhas ~55-64, e import da linha 21)
- Delete: `src/bar_color.py`
- Delete: `tests/test_bar_color.py`

**Interfaces:**
- Consumes: `rms_to_level`, `classify` da Task 2
- Produces: overlay com amplitude perceptível; `bar_color` deixa de existir no projeto

- [ ] **Step 1: Trocar a escala linear pela escala dB no overlay**

Em `src/waveform_overlay.py`, substituir o import (linha 21):

```python
from src.bar_color import bar_color
```

por:

```python
from src.core.audio_level import classify, rms_to_level
```

Adicionar logo após as constantes existentes (`_MARGIN_LEFT = 16`):

```python
_STATE_STYLES = {
    "weak": ("#F39C12", "⚠️ Áudio fraco"),
    "loud": ("#E74C3C", "⚠️ Volume alto"),
    "ok": ("#4A90E2", "🎙️ Ouvindo..."),
}
```

E substituir o método `_apply_rms` inteiro:

```python
    def _apply_rms(self, rms: float):
        with self._lock:
            if self._transcribing:
                return
            level = rms_to_level(rms)
            height = _BAR_MIN_H + level * (_BAR_MAX_H - _BAR_MIN_H)
            color_hex, label = _STATE_STYLES[classify(rms)]
            self._bars.pop(0)
            self._bars.append(height)
            self._color_hex = color_hex
            self._label = label
```

- [ ] **Step 2: Remover o módulo antigo e seu teste**

```bash
git rm src/bar_color.py tests/test_bar_color.py
```

- [ ] **Step 3: Suíte e lint verdes**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: todos os testes passam (os de `bar_color` saem da contagem; os 9 de `audio_level` entram) e `All checks passed!`

- [ ] **Step 4: Fumaça manual da sensibilidade**

Run: `.venv/bin/python -u -m src.app` (encerrar instância anterior antes: `pkill -f "src.app"`)
Falar em volume NORMAL segurando F8.
Expected: barras oscilando visivelmente (~metade da altura) com cor azul "🎙️ Ouvindo...", SEM "⚠️ Áudio fraco". Sussurrar deve mostrar "Áudio fraco"; falar muito alto perto do mic deve mostrar "Volume alto". Encerrar o app após validar.

- [ ] **Step 5: Commit**

```bash
git add src/waveform_overlay.py
git commit -m "feat: overlay usa escala dB — amplitude de voz normal visível"
```

---

### Task 4: `src/core/app_logging.py` — log em arquivo (TDD) e app.py logando exceções

**Files:**
- Create: `src/core/app_logging.py`
- Test: `tests/core/test_app_logging.py`
- Modify: `src/app.py` (imports; método `_handle_recording`; remover `_show_notification` e imports de NSUserNotification)

**Interfaces:**
- Consumes: nada
- Produces (usados pela Task 5):
  - `setup_logging(log_path: Path) -> logging.Logger` — logger "sagmowhisper" com RotatingFileHandler (1 MB × 3) + stderr
  - `src/app.py` define `LOG_PATH = Path.home() / "Library/Logs/SagmoWhisper.log"` e `logger` de módulo

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/core/test_app_logging.py`:

```python
import logging

from src.core.app_logging import setup_logging


def _fresh_logger():
    logger = logging.getLogger("sagmowhisper")
    logger.handlers.clear()
    return logger


def test_setup_cria_arquivo_de_log(tmp_path):
    _fresh_logger()
    log_path = tmp_path / "logs" / "app.log"
    logger = setup_logging(log_path)
    logger.error("falha de teste")
    logging.shutdown()
    assert log_path.exists()
    assert "falha de teste" in log_path.read_text()


def test_setup_e_idempotente_nao_duplica_handlers(tmp_path):
    _fresh_logger()
    log_path = tmp_path / "app.log"
    setup_logging(log_path)
    logger = setup_logging(log_path)
    file_handlers = [
        h for h in logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/core/test_app_logging.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.core.app_logging'`

- [ ] **Step 3: Implementação mínima**

Criar `src/core/app_logging.py`:

```python
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("sagmowhisper")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(file_handler)
        logger.addHandler(logging.StreamHandler(sys.stderr))
    return logger
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/core/test_app_logging.py -q`
Expected: `2 passed`

- [ ] **Step 5: Usar o logger no app.py (substitui print + notificação morta)**

Em `src/app.py`:

(a) Remover `NSUserNotification` e `NSUserNotificationCenter` do import de `Foundation` (eles não são entregues para Python fora de bundle — era por isso que o erro sumia). O import fica:

```python
from Foundation import NSDate, NSObject, NSRunLoop
```

(b) Adicionar aos imports do topo:

```python
from pathlib import Path

from src.core.app_logging import setup_logging
```

(c) Logo após as constantes de ícone (`ICON_PROCESSING = "⏳"`), adicionar:

```python
LOG_PATH = Path.home() / "Library" / "Logs" / "SagmoWhisper.log"
logger = setup_logging(LOG_PATH)
```

(d) Substituir o bloco `except` de `_handle_recording` (hoje: `print` + `_show_notification`):

```python
        except Exception as e:
            logger.exception("Falha no ditado")
            self._notify_error(str(e))
```

(e) Apagar o método `_show_notification` inteiro e criar no lugar (placeholder que a Task 5 liga à UI):

```python
    def _notify_error(self, message: str):
        pass
```

- [ ] **Step 6: Suíte e lint verdes**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: tudo verde, `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/core/app_logging.py tests/core/test_app_logging.py src/app.py
git commit -m "feat: erros de ditado vão para ~/Library/Logs/SagmoWhisper.log

Remove NSUserNotification (nunca era entregue fora de bundle) e o
print bufferizado que engolia o erro."
```

---

### Task 5: Erro visível na barra de menu — ícone ⚠️ + "Último erro" + "Abrir log"

**Files:**
- Modify: `src/app.py` (constante de ícone; `MainThreadDispatcher`; `_setup_menu`; `_handle_recording`/`finishRecordingOnMainThread`; `_notify_error`)

**Interfaces:**
- Consumes: `LOG_PATH` e `logger` da Task 4
- Produces: contrato de UX de erro — após falha o ícone fica ⚠️ até o próximo ditado bem-sucedido; menu mostra "Último erro: …" e "Abrir log"

- [ ] **Step 1: Adicionar estado de erro ao app**

Em `src/app.py`:

(a) Junto às constantes de ícone:

```python
ICON_ERROR = "⚠️"
```

(b) Adicionar import no topo:

```python
import subprocess
```

(c) No `__init__` de `VozMenuBar`, junto de `self._recording = False`:

```python
        self._had_error = False
```

(d) Novos métodos no `MainThreadDispatcher`:

```python
    def showErrorOnMainThread_(self, message):
        self._app._show_error(str(message))

    def openLog_(self, sender):
        subprocess.run(["open", str(LOG_PATH)])
```

(e) Em `_setup_menu` de `VozMenuBar`, ANTES do item "Sair", adicionar:

```python
        self._error_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "", None, ""
        )
        self._error_item.setHidden_(True)
        menu.addItem_(self._error_item)

        open_log_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Abrir log", "openLog:", ""
        )
        open_log_item.setTarget_(self._dispatcher)
        menu.addItem_(open_log_item)
```

(f) Novo método em `VozMenuBar`:

```python
    def _show_error(self, message: str):
        self._had_error = True
        self._set_title(ICON_ERROR)
        self._error_item.setTitle_(f"Último erro: {message[:80]}")
        self._error_item.setHidden_(False)
```

(g) Substituir o `_notify_error` placeholder da Task 4:

```python
    def _notify_error(self, message: str):
        self._dispatcher.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showErrorOnMainThread:", message, False
        )
```

(h) Em `_handle_recording`, primeira linha do `try` (antes de `self._pipeline.run`):

```python
            self._had_error = False
```

(i) Em `finishRecordingOnMainThread` do dispatcher, não sobrescrever o ⚠️:

```python
    def finishRecordingOnMainThread(self):
        self._app._overlay.hide()
        if not self._app._had_error:
            self._app._set_title(ICON_IDLE)
            self._app._error_item.setHidden_(True)
```

- [ ] **Step 2: Suíte e lint verdes**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: tudo verde, `All checks passed!`

- [ ] **Step 3: Fumaça manual do fluxo de erro**

```bash
pkill -f "src.app"; GROQ_API_KEY=gsk_chave_invalida .venv/bin/python -u -m src.app
```

Ditar algo com F8.
Expected: ícone vira ⚠️; menu mostra "Último erro: Error code: 401…" e "Abrir log" abre o arquivo com o stack trace. Encerrar, rodar sem o override (`.venv/bin/python -u -m src.app`), ditar com sucesso e confirmar que o ícone volta a 🎙️ e o item de erro some. Encerrar o app.

- [ ] **Step 4: Commit**

```bash
git add src/app.py
git commit -m "feat: erro de ditado vira ⚠️ na barra com 'Último erro' e 'Abrir log'"
```

---

### Task 6: `src/core/single_instance.py` — trava de instância única (TDD)

Impede o bug real observado hoje: 3 instâncias simultâneas → ícones duplicados na barra.

**Files:**
- Create: `src/core/single_instance.py`
- Test: `tests/core/test_single_instance.py`
- Modify: `src/app.py` (função `main`)

**Interfaces:**
- Consumes: nada
- Produces:
  - `AlreadyRunningError(RuntimeError)`
  - `acquire_lock(lock_path: Path) -> None` — grava PID; levanta `AlreadyRunningError` se outro PID vivo detém o lock; assume locks órfãos
  - `release_lock(lock_path: Path) -> None` — idempotente

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/core/test_single_instance.py`:

```python
import os
import subprocess

import pytest

from src.core.single_instance import (
    AlreadyRunningError,
    acquire_lock,
    release_lock,
)


def test_acquire_grava_pid_proprio(tmp_path):
    lock = tmp_path / "app.lock"
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_acquire_falha_se_pid_do_lock_esta_vivo(tmp_path):
    lock = tmp_path / "app.lock"
    lock.write_text(str(os.getpid()))
    with pytest.raises(AlreadyRunningError):
        acquire_lock(lock)


def test_acquire_assume_lock_orfao_de_processo_morto(tmp_path):
    proc = subprocess.Popen(["true"])
    proc.wait()
    lock = tmp_path / "app.lock"
    lock.write_text(str(proc.pid))
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_acquire_assume_lock_com_conteudo_invalido(tmp_path):
    lock = tmp_path / "app.lock"
    lock.write_text("lixo")
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_release_remove_e_e_idempotente(tmp_path):
    lock = tmp_path / "app.lock"
    acquire_lock(lock)
    release_lock(lock)
    assert not lock.exists()
    release_lock(lock)  # não levanta
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/python -m pytest tests/core/test_single_instance.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'src.core.single_instance'`

- [ ] **Step 3: Implementação mínima**

Criar `src/core/single_instance.py`:

```python
import os
from pathlib import Path


class AlreadyRunningError(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def acquire_lock(lock_path: Path) -> None:
    if lock_path.exists():
        content = lock_path.read_text().strip()
        if content.isdigit() and _pid_alive(int(content)):
            raise AlreadyRunningError(
                f"SagmoWhisper já está rodando (PID {content})."
            )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(str(os.getpid()))


def release_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.venv/bin/python -m pytest tests/core/test_single_instance.py -q && .venv/bin/ruff check src tests`
Expected: `5 passed` e `All checks passed!`

- [ ] **Step 5: Ligar no `main()` do app.py**

(a) Imports no topo de `src/app.py`:

```python
import atexit

from src.core.single_instance import (
    AlreadyRunningError,
    acquire_lock,
    release_lock,
)
```

(b) Junto de `LOG_PATH`:

```python
LOCK_PATH = (
    Path.home() / "Library" / "Application Support" / "SagmoWhisper" / "app.lock"
)
```

(c) Substituir a função `main()` por:

```python
def main():
    try:
        acquire_lock(LOCK_PATH)
    except AlreadyRunningError as e:
        logger.error(str(e))
        sys.exit(1)
    atexit.register(release_lock, LOCK_PATH)
    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory
    )
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    VozMenuBar(Config.from_env()).run()
```

- [ ] **Step 6: Suíte, lint e fumaça manual**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests`
Expected: tudo verde.

Fumaça: `pkill -f "src.app"; .venv/bin/python -u -m src.app` em um terminal; em outro, `.venv/bin/python -u -m src.app` de novo.
Expected: a segunda tentativa loga "SagmoWhisper já está rodando (PID …)" e sai com código 1; só UM ícone na barra. Encerrar o app.

- [ ] **Step 7: Commit**

```bash
git add src/core/single_instance.py tests/core/test_single_instance.py src/app.py
git commit -m "feat: trava de instância única — impede ícones duplicados na barra"
```

---

### Task 7: Criar branch `main` e atualizar checkpoint

**Files:**
- Modify: `docs/STATUS.md`
- Git: criar branch `main` a partir do estado atual

**Interfaces:**
- Consumes: todas as tasks anteriores commitadas
- Produces: `main` como branch principal; STATUS.md refletindo o milestone 1 entregue

- [ ] **Step 1: Confirmar working tree limpo e suíte verde**

Run: `git status --short && .venv/bin/python -m pytest -q`
Expected: nenhum arquivo modificado fora de `.superpowers/`; todos os testes passam.

- [ ] **Step 2: Criar `main` a partir do feature branch**

```bash
git checkout -b main
git branch
```

Expected: `* main` listado junto de `feature/voz-mvp-ditado`.

- [ ] **Step 3: Atualizar docs/STATUS.md**

Substituir as seções "Estado atual", "Trabalho não commitado" e "Próxima task" para refletir: milestone 1 (Fundação) entregue — escala dB, erros visíveis (log/ícone/menu), instância única, `rumps` removido, branch `main` criado; testes com a contagem atual; próxima task = plano do milestone 2 (providers + settings). Manter o restante do arquivo.

- [ ] **Step 4: Commit final**

```bash
git add docs/STATUS.md
git commit -m "docs: checkpoint do milestone 1 (fundação) em main"
```
