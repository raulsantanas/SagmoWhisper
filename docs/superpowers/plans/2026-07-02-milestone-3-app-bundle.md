# Milestone 3 — SagmoWhisper.app Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empacotar o SagmoWhisper como app nativo do macOS (`SagmoWhisper.app`), instalável por um único comando (`./install.sh`), com "Abrir no login" controlável pela janela de Configurações e CI (testes + lint + build) em todo PR.

**Architecture:** Bundle via py2app com `LSUIElement=True` (sem Dock, só status item). "Abrir no login" = LaunchAgent `RunAtLoad` cuja existência do arquivo É o estado (lógica pura em `src/core/login_item.py`, TDD; a janela AppKit só chama o módulo). `install.sh` orquestra build em venv limpo, assinatura ad-hoc, instalação em /Applications e login ligado por padrão. CI monta o `.app` do zero em `macos-latest`.

**Tech Stack:** Python 3.11, py2app, plistlib, AppKit (pyobjc), bash, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-07-02-m3-app-bundle-design.md` (fonte de verdade; em conflito, o spec vence).

## Global Constraints

- `CFBundleIdentifier` = `com.raulsantana.sagmowhisper` — mesmo valor de `AGENT_LABEL` no login_item.
- `LSUIElement` = `True` no Info.plist (sem ícone no Dock).
- `NSMicrophoneUsageDescription` = "O SagmoWhisper usa o microfone para transcrever sua voz enquanto você segura a tecla de ditado." (texto exato).
- Checkbox nas Configurações: título exato **"Abrir no login"**; hint exato **"Instale o app (./install.sh) para ativar"**; o toggle aplica NA HORA (não espera "Salvar"); desabilitado quando `login_item.app_installed()` é `False`.
- `install.sh`: três modos — `./install.sh` (build + instala + liga login + abre), `--build-only` (para no codesign; usado no CI), `--uninstall` (remove app/LaunchAgent/lock e **PRESERVA** `config.json` e chaves do Keychain, imprimindo instruções de remoção manual). Mensagens em pt-BR. `set -euo pipefail`.
- Empacotador: **py2app**. Plano B (PyInstaller) é decisão do controlador — se o build travar em libs nativas além de ajustes de `packages`/`excludes`, reportar **BLOCKED** com o erro; NUNCA trocar de ferramenta por conta própria.
- Provider Local NÃO embarca no bundle: `excludes: ["faster_whisper"]` no setup.py.
- CI: 2 jobs (`test`, `build`) em `macos-latest`, disparo em `pull_request` e `push` na `main`; **nenhum secret** (testes usam fakes).
- Qualidade (LEIs 2 e 8): TDD para `src/core/login_item.py` com 100% de cobertura; CC ≤ 4 (ruff C90); nomes de teste em pt-BR; `pytest` e `ruff check src tests` verdes em TODO commit.
- Segurança (LEI 9): nenhuma chave em código, JSON, logs ou git; `.env` jamais commitado.
- Suíte atual: **85 testes verdes**. Nenhum teste existente pode quebrar. Após a Task 1: 92.
- Branch de trabalho: `feature/m3-app-bundle`. Commits com prefixo convencional em pt-BR (`feat:`, `docs:`, `ci:`, `build:`).

---

### Task 1: `src/core/login_item.py` (TDD)

**Files:**
- Create: `src/core/login_item.py`
- Test: `tests/core/test_login_item.py`

**Interfaces:**
- Consumes: nada (módulo puro, só stdlib: `plistlib`, `pathlib`, `sys`).
- Produces (usado pelas Tasks 2 e 4):
  - `AGENT_LABEL: str = "com.raulsantana.sagmowhisper"`
  - `AGENT_PATH: Path` (default `~/Library/LaunchAgents/com.raulsantana.sagmowhisper.plist`)
  - `APP_BINARY: Path` (default `/Applications/SagmoWhisper.app/Contents/MacOS/SagmoWhisper`)
  - `plist_xml(binary: Path = APP_BINARY) -> str`
  - `is_enabled(path: Path = AGENT_PATH) -> bool`
  - `app_installed(binary: Path = APP_BINARY) -> bool`
  - `enable(path: Path = AGENT_PATH, binary: Path = APP_BINARY) -> None`
  - `disable(path: Path = AGENT_PATH) -> None`
  - CLI: `python -m src.core.login_item enable|disable|status` (status imprime `enabled`/`disabled`; comando inválido → exit 2 e linha de uso).

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/core/test_login_item.py` com exatamente este conteúdo:

```python
"""Testes do login_item (LaunchAgent que implementa "Abrir no login")."""
import plistlib
from pathlib import Path

from src.core.login_item import (
    AGENT_LABEL,
    _cli,
    app_installed,
    disable,
    enable,
    is_enabled,
    plist_xml,
)


def test_plist_xml_gera_launchagent_valido():
    xml = plist_xml(Path("/Applications/X.app/Contents/MacOS/X"))
    data = plistlib.loads(xml.encode())
    assert data["Label"] == AGENT_LABEL
    assert data["ProgramArguments"] == [
        "/Applications/X.app/Contents/MacOS/X"
    ]
    assert data["RunAtLoad"] is True


def test_enable_cria_plist_e_liga_o_estado(tmp_path):
    agent = tmp_path / "LaunchAgents" / "com.test.plist"
    assert is_enabled(agent) is False
    enable(agent, Path("/tmp/binario"))
    assert is_enabled(agent) is True
    data = plistlib.loads(agent.read_bytes())
    assert data["ProgramArguments"] == ["/tmp/binario"]


def test_disable_remove_plist_e_e_silencioso_se_ausente(tmp_path):
    agent = tmp_path / "a.plist"
    disable(agent)  # arquivo ausente: não levanta erro
    agent.write_text("qualquer coisa")
    disable(agent)
    assert not agent.exists()


def test_app_installed_reflete_existencia_do_binario(tmp_path):
    assert app_installed(tmp_path / "nao-existe") is False
    binario = tmp_path / "SagmoWhisper"
    binario.write_text("")
    assert app_installed(binario) is True


def test_cli_enable_e_status(tmp_path, capsys):
    agent = tmp_path / "a.plist"
    assert _cli(["enable"], agent, Path("/tmp/binario")) == 0
    assert agent.exists()
    assert _cli(["status"], agent, Path("/tmp/binario")) == 0
    assert capsys.readouterr().out.strip() == "enabled"


def test_cli_disable_e_status(tmp_path, capsys):
    agent = tmp_path / "a.plist"
    enable(agent, Path("/tmp/binario"))
    assert _cli(["disable"], agent, Path("/tmp/binario")) == 0
    assert not agent.exists()
    assert _cli(["status"], agent, Path("/tmp/binario")) == 0
    assert capsys.readouterr().out.strip() == "disabled"


def test_cli_comando_invalido_retorna_2(tmp_path, capsys):
    assert _cli(["xyz"], tmp_path / "a.plist", Path("/tmp/b")) == 2
    assert "uso:" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.venv/bin/pytest tests/core/test_login_item.py -v`
Expected: FAIL/ERROR com `ModuleNotFoundError: No module named 'src.core.login_item'`

- [ ] **Step 3: Implementar o módulo**

Criar `src/core/login_item.py` com exatamente este conteúdo:

```python
"""Estado "Abrir no login" via LaunchAgent: o arquivo existir É o estado.

Sem launchctl: RunAtLoad passa a valer no próximo login ao criar o plist
e deixa de valer ao removê-lo. Nenhum campo novo no config.json.
"""
import plistlib
import sys
from pathlib import Path

AGENT_LABEL = "com.raulsantana.sagmowhisper"
AGENT_PATH = (
    Path.home() / "Library" / "LaunchAgents" / f"{AGENT_LABEL}.plist"
)
APP_BINARY = Path(
    "/Applications/SagmoWhisper.app/Contents/MacOS/SagmoWhisper"
)


def plist_xml(binary: Path = APP_BINARY) -> str:
    data = {
        "Label": AGENT_LABEL,
        "ProgramArguments": [str(binary)],
        "RunAtLoad": True,
    }
    return plistlib.dumps(data, sort_keys=True).decode()


def is_enabled(path: Path = AGENT_PATH) -> bool:
    return path.exists()


def app_installed(binary: Path = APP_BINARY) -> bool:
    return binary.exists()


def enable(path: Path = AGENT_PATH, binary: Path = APP_BINARY) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist_xml(binary))


def disable(path: Path = AGENT_PATH) -> None:
    path.unlink(missing_ok=True)


def _cli(
    args: list, path: Path = AGENT_PATH, binary: Path = APP_BINARY
) -> int:
    if args == ["enable"]:
        enable(path, binary)
        return 0
    if args == ["disable"]:
        disable(path)
        return 0
    if args == ["status"]:
        print("enabled" if is_enabled(path) else "disabled")
        return 0
    print("uso: python -m src.core.login_item enable|disable|status")
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_cli(sys.argv[1:]))
```

- [ ] **Step 4: Rodar e ver passar (suíte inteira + cobertura + lint)**

Run: `.venv/bin/pytest`
Expected: **92 passed** (85 existentes + 7 novos); no relatório de cobertura, `src/core/login_item.py` com **100%**.

Run: `.venv/bin/ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 5: Fumaça do CLI (sem tocar no LaunchAgents real)**

Run: `HOME=$(mktemp -d) .venv/bin/python -m src.core.login_item status`
Expected: `disabled`

- [ ] **Step 6: Commit**

```bash
git add tests/core/test_login_item.py src/core/login_item.py
git commit -m "feat: login_item (LaunchAgent 'Abrir no login', TDD 100%)"
```

---

### Task 2: Checkbox "Abrir no login" nas Configurações

**Files:**
- Modify: `src/macos/settings_window.py`

**Interfaces:**
- Consumes (Task 1): `from src.core import login_item` — `login_item.app_installed()`, `login_item.is_enabled()`, `login_item.enable()`, `login_item.disable()` (todos com defaults; NÃO passar argumentos).
- Produces: controle `self._login_check` (NSButton switch), hint `self._login_hint`, selector `loginToggled:`. Nenhuma outra task consome — validado por fumaça estrutural.

Regras (do spec §5): estado inicial = `is_enabled()`; toggle aplica na hora (estado do sistema, não do config.json — NÃO passa pelo "Salvar"); em modo dev (`app_installed() == False`) o checkbox fica desabilitado e o hint visível.

- [ ] **Step 1: Aumentar a janela e adicionar os controles**

Em `src/macos/settings_window.py`:

(a) Trocar a linha de dimensões:

```python
_W, _H = 440, 340
```

por:

```python
_W, _H = 440, 380
```

(b) Trocar a linha de import:

```python
from src.core import secrets
```

por:

```python
from src.core import login_item, secrets
```

(c) Substituir o método `_build_fields` inteiro por (só muda o bloco novo no
topo — checkbox em y=346 e hint em y=326, na faixa nova de 40px; as linhas
existentes ficam idênticas):

```python
    @objc.python_method
    def _build_fields(self):
        content = self._window.contentView()
        self._login_check = self._checkbox(346, "Abrir no login")
        self._login_check.setTarget_(self)
        self._login_check.setAction_("loginToggled:")
        content.addSubview_(self._login_check)
        self._login_hint = self._label(
            "Instale o app (./install.sh) para ativar", 326, _FIELD_W
        )
        self._login_hint.setFrame_(NSMakeRect(_FIELD_X, 326, _FIELD_W, 18))
        content.addSubview_(self._login_hint)
        self._provider_popup = self._popup(292, "providerChanged:")
        self._add_row(content, "Provider", 292, self._provider_popup)
        self._api_key_field = NSSecureTextField.alloc().initWithFrame_(
            NSMakeRect(_FIELD_X, 252, _FIELD_W, _ROW_H)
        )
        self._api_key_label = self._add_row(
            content, "API key", 252, self._api_key_field
        )
        self._model_popup = self._popup(212, None)
        self._add_row(content, "Modelo", 212, self._model_popup)
        self._cleanup_check = self._checkbox(172, "Limpar hesitações")
        content.addSubview_(self._cleanup_check)
        self._cleanup_popup = self._popup(132, None)
        self._add_row(content, "Modelo de limpeza", 132, self._cleanup_popup)
        self._hotkey_popup = self._popup(92, None)
        self._hotkey_popup.addItemsWithTitles_(list(_HOTKEYS))
        self._add_row(content, "Tecla de ditado", 92, self._hotkey_popup)
        self._status_label = self._label("", 56, _W - 40)
        content.addSubview_(self._status_label)
```

- [ ] **Step 2: Refresh do estado + ação do toggle**

(a) No final do método `_refresh_from_config` (depois da linha
`self._reload_provider_fields(self._config.provider)`), adicionar:

```python
        self._refresh_login_controls()
```

(b) Adicionar novo método logo após `_refresh_from_config`:

```python
    @objc.python_method
    def _refresh_login_controls(self):
        installed = login_item.app_installed()
        self._login_check.setEnabled_(installed)
        self._login_check.setState_(1 if login_item.is_enabled() else 0)
        self._login_hint.setHidden_(installed)
```

(c) Na seção `# ---------- ações (selectors AppKit) ----------`, adicionar
antes de `providerChanged_`:

```python
    def loginToggled_(self, sender):
        if self._login_check.state():
            login_item.enable()
        else:
            login_item.disable()
```

- [ ] **Step 3: Suíte + lint (sem regressão)**

Run: `.venv/bin/pytest && .venv/bin/ruff check src tests`
Expected: **92 passed**, `All checks passed!`

- [ ] **Step 4: Fumaça estrutural (headless, sem cliques)**

```bash
.venv/bin/python - <<'EOF'
from AppKit import NSApplication
from src.core.config import DEFAULTS, Config
from src.macos.settings_window import SettingsWindowController

NSApplication.sharedApplication()
c = SettingsWindowController.alloc().initWithConfig_onSave_(
    Config(**DEFAULTS), lambda cfg: None
)
c._refresh_from_config()
assert str(c._login_check.title()) == "Abrir no login"
assert not c._login_check.isEnabled()  # bundle ainda não instalado
assert not c._login_hint.isHidden()
print("ok: checkbox presente, desabilitado em modo dev, hint visível")
EOF
```

Expected: `ok: checkbox presente, desabilitado em modo dev, hint visível`
(Nota: os dois últimos asserts pressupõem `/Applications/SagmoWhisper.app`
ausente — verdadeiro até a instalação no fim do milestone. A fumaça com
cliques reais fica para o gate humano do milestone.)

- [ ] **Step 5: Commit**

```bash
git add src/macos/settings_window.py
git commit -m "feat: checkbox 'Abrir no login' nas Configurações (aplica na hora)"
```

---

### Task 3: `SagmoWhisper.py` + `setup.py` + primeiro build do .app

**Files:**
- Create: `SagmoWhisper.py` (raiz do repo)
- Create: `setup.py` (raiz do repo)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `src.app.main` (já existe em `src/app.py`).
- Produces (usado pelas Tasks 4 e 5): `python setup.py py2app` gera
  `dist/SagmoWhisper.app` com binário `Contents/MacOS/SagmoWhisper` e
  Info.plist com `LSUIElement=true` e `CFBundleIdentifier=com.raulsantana.sagmowhisper`.

O py2app nomeia o `.app` pelo nome do script de entrada — por isso o launcher
se chama `SagmoWhisper.py` (não `launcher.py`).

- [ ] **Step 1: Criar o launcher**

Criar `SagmoWhisper.py` com exatamente este conteúdo:

```python
"""Entrada do bundle. O py2app nomeia o .app pelo nome deste arquivo."""
from src.app import main

main()
```

(`main()` existe em `src/app.py:255`: adquire o lock de instância única,
registra o release, seta ActivationPolicyAccessory e roda o `VozMenuBar`.)

- [ ] **Step 2: Criar o setup.py**

Criar `setup.py` com exatamente este conteúdo:

```python
"""Build do SagmoWhisper.app: .venv/bin/python setup.py py2app."""
import tomllib
from pathlib import Path

from setuptools import setup

_VERSION = tomllib.loads(Path("pyproject.toml").read_text())["project"][
    "version"
]

_PLIST = {
    "CFBundleIdentifier": "com.raulsantana.sagmowhisper",
    "CFBundleName": "SagmoWhisper",
    "CFBundleShortVersionString": _VERSION,
    "LSUIElement": True,
    "NSMicrophoneUsageDescription": (
        "O SagmoWhisper usa o microfone para transcrever sua voz "
        "enquanto você segura a tecla de ditado."
    ),
}

setup(
    app=["SagmoWhisper.py"],
    options={
        "py2app": {
            "plist": _PLIST,
            "packages": ["numpy", "sounddevice", "soundfile", "src"],
            "excludes": ["faster_whisper", "pytest", "ruff"],
        }
    },
)
```

- [ ] **Step 3: Git-ignorar artefatos de build**

Adicionar ao final de `.gitignore`:

```
# build do .app (Milestone 3)
.build-venv/
build/
dist/
*.egg-info/
.eggs/
htmlcov/
coverage.json
```

- [ ] **Step 4: Build empírico**

```bash
.venv/bin/pip install py2app
rm -rf build dist
.venv/bin/python setup.py py2app
```

Expected: termina sem erro e cria `dist/SagmoWhisper.app`.

**Se o build falhar em libs nativas** (numpy/sounddevice/soundfile): tentar
ajustes razoáveis de `packages`/`excludes` (ex.: adicionar `"cffi"`,
`"_soundfile_data"`). Se persistir, reportar **BLOCKED** com o erro completo —
a troca para o Plano B (PyInstaller) é decisão do controlador, não sua.

- [ ] **Step 5: Verificar o bundle**

```bash
test -x dist/SagmoWhisper.app/Contents/MacOS/SagmoWhisper && echo "binario ok"
plutil -extract LSUIElement raw dist/SagmoWhisper.app/Contents/Info.plist
plutil -extract CFBundleIdentifier raw dist/SagmoWhisper.app/Contents/Info.plist
codesign --force --deep -s - dist/SagmoWhisper.app
codesign --verify --deep dist/SagmoWhisper.app && echo "assinatura ok"
find dist/SagmoWhisper.app -name "faster_whisper*" | grep -q . \
  && echo "ERRO: faster_whisper embarcado" || echo "sem faster_whisper ok"
```

Expected: `binario ok`, `true`, `com.raulsantana.sagmowhisper`,
`assinatura ok`, `sem faster_whisper ok`.

- [ ] **Step 6: Suíte + lint continuam verdes**

Run: `.venv/bin/pytest && .venv/bin/ruff check src tests`
Expected: **92 passed**, `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add SagmoWhisper.py setup.py .gitignore
git commit -m "build: setup.py py2app + launcher SagmoWhisper.py (LSUIElement, sem Dock)"
```

(NÃO commitar `build/`, `dist/` nem `.build-venv/` — já git-ignorados.)

---

### Task 4: `install.sh` (instala, --build-only, --uninstall)

**Files:**
- Create: `install.sh` (raiz do repo, executável)

**Interfaces:**
- Consumes: `setup.py` (Task 3), `python -m src.core.login_item enable` (Task 1).
- Produces (usado pela Task 5): `./install.sh --build-only` monta e assina
  `dist/SagmoWhisper.app` num venv limpo `.build-venv/` sem tocar em
  /Applications, login nem app rodando.

- [ ] **Step 1: Criar o script**

Criar `install.sh` com exatamente este conteúdo:

```bash
#!/bin/bash
# Instala o SagmoWhisper como app nativo do macOS.
# Uso: ./install.sh            build + instala + liga "Abrir no login" + abre
#      ./install.sh --build-only   só monta e assina dist/SagmoWhisper.app (CI)
#      ./install.sh --uninstall    remove app/LaunchAgent/lock (preserva config e Keychain)
set -euo pipefail

APP_NAME="SagmoWhisper"
APP_PATH="/Applications/${APP_NAME}.app"
LOCK_FILE="$HOME/Library/Application Support/SagmoWhisper/app.lock"
AGENT_PLIST="$HOME/Library/LaunchAgents/com.raulsantana.sagmowhisper.plist"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_VENV="$REPO_DIR/.build-venv"

erro() { echo "✗ $1" >&2; exit 1; }

kill_running() {
  if [ -f "$LOCK_FILE" ]; then
    local pid
    pid=$(cat "$LOCK_FILE" 2>/dev/null || true)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      echo "Encerrando instância em execução (PID $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
  fi
}

uninstall() {
  echo "Removendo ${APP_NAME}..."
  kill_running
  rm -rf "$APP_PATH"
  # rm do plist == login_item.disable (sem depender de venv)
  rm -f "$AGENT_PLIST"
  rm -f "$LOCK_FILE"
  echo "✓ App, início no login e lock removidos."
  echo "Suas configurações e chaves foram PRESERVADAS. Para removê-las também:"
  echo "  rm -rf \"\$HOME/Library/Application Support/SagmoWhisper\""
  echo "  security delete-generic-password -s SagmoWhisper"
  exit 0
}

build() {
  [ "$(uname)" = "Darwin" ] || erro "este instalador é só para macOS."
  command -v python3 >/dev/null \
    || erro "python3 não encontrado. Instale o Python 3.11+ (brew install python@3.11)."
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || erro "Python 3.11+ é necessário (encontrado: $(python3 --version))."
  echo "Criando ambiente de build limpo (.build-venv)..."
  rm -rf "$BUILD_VENV"
  python3 -m venv "$BUILD_VENV"
  "$BUILD_VENV/bin/pip" install --quiet --upgrade pip
  "$BUILD_VENV/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt" py2app
  echo "Empacotando ${APP_NAME}.app (pode levar alguns minutos)..."
  cd "$REPO_DIR"
  rm -rf build dist
  "$BUILD_VENV/bin/python" setup.py py2app
  codesign --force --deep -s - "dist/${APP_NAME}.app"
  echo "✓ dist/${APP_NAME}.app montado e assinado (ad-hoc)."
}

case "${1:-}" in
  --uninstall) uninstall ;;
  --build-only) build; exit 0 ;;
  "") ;;
  *) erro "opção desconhecida: $1 (use --build-only ou --uninstall)" ;;
esac

build
kill_running
echo "Instalando em /Applications..."
rm -rf "$APP_PATH"
cp -R "dist/${APP_NAME}.app" "$APP_PATH"
"$BUILD_VENV/bin/python" -m src.core.login_item enable
echo "✓ 'Abrir no login' ligado (desligue quando quiser em 🎙️ → Configurações…)."
open "$APP_PATH"
echo ""
echo "✓ ${APP_NAME} instalado e aberto!"
echo "Passos finais (uma única vez, em Ajustes do Sistema → Privacidade e Segurança):"
echo "  1. Acessibilidade → + → ${APP_NAME}"
echo "  2. Monitoramento de Entrada → + → ${APP_NAME}"
echo "  3. O pedido de Microfone aparece sozinho na primeira gravação."
echo "  4. Configure sua chave em 🎙️ → Configurações…"
```

- [ ] **Step 2: Tornar executável e validar sintaxe**

```bash
chmod +x install.sh
bash -n install.sh && echo "sintaxe ok"
```

Expected: `sintaxe ok`

- [ ] **Step 3: Testar rejeição de opção inválida**

Run: `./install.sh --naoexiste; echo "exit=$?"`
Expected: `✗ opção desconhecida: --naoexiste (use --build-only ou --uninstall)` e `exit=1`

- [ ] **Step 4: Testar --uninstall isolado (HOME falso — NÃO matar o app real)**

Run: `HOME="$(mktemp -d)" ./install.sh --uninstall; echo "exit=$?"`
Expected: mensagens de remoção + instruções de preservação, `exit=0`.
(Com HOME falso não há lock nem LaunchAgent; `/Applications/SagmoWhisper.app`
ainda não existe — o `rm -rf` é inofensivo.)

- [ ] **Step 5: Testar --build-only (o caminho real do usuário e do CI)**

Run: `./install.sh --build-only`
Expected: cria `.build-venv/`, monta e assina `dist/SagmoWhisper.app`, termina
com `✓ dist/SagmoWhisper.app montado e assinado (ad-hoc).` sem tocar em
/Applications. Depois conferir:

```bash
test -x dist/SagmoWhisper.app/Contents/MacOS/SagmoWhisper && echo "binario ok"
```

NÃO rodar `./install.sh` sem flag nesta task: a instalação completa (que mata
a instância dev em execução e escreve em /Applications) é o gate humano do
fim do milestone.

- [ ] **Step 6: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh (build+instala+login por padrão, --build-only, --uninstall)"
```

---

### Task 5: CI — `.github/workflows/ci.yml`

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `./install.sh --build-only` (Task 4), suíte pytest/ruff.
- Produces: workflow `CI` com jobs `test` e `build` — o PR deste milestone é a
  primeira execução real.

- [ ] **Step 1: Criar o workflow**

Criar `.github/workflows/ci.yml` com exatamente este conteúdo:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Instala dependências
        run: pip install -r requirements.txt
      - name: Testes (pytest + cobertura)
        run: pytest
      - name: Lint (ruff, CC <= 4)
        run: ruff check src tests

  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Monta o .app do zero
        run: ./install.sh --build-only
      - name: Verifica o bundle
        run: |
          test -x "dist/SagmoWhisper.app/Contents/MacOS/SagmoWhisper"
          [ "$(plutil -extract LSUIElement raw dist/SagmoWhisper.app/Contents/Info.plist)" = "true" ]
          [ "$(plutil -extract CFBundleIdentifier raw dist/SagmoWhisper.app/Contents/Info.plist)" = "com.raulsantana.sagmowhisper" ]
```

- [ ] **Step 2: Validar a sintaxe YAML localmente**

Run: `ruby -ryaml -e 'YAML.load_file(".github/workflows/ci.yml"); puts "yaml ok"'`
Expected: `yaml ok`
(A validação real acontece quando o PR do milestone abrir — o CI roda nele.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: testes + lint + build do .app em todo PR e push na main"
```

---

### Task 6: README (EN + pt-BR) + checkpoint em docs/STATUS.md

**Files:**
- Modify: `README.md`
- Modify: `README.pt-BR.md`
- Modify: `docs/STATUS.md`

**Interfaces:**
- Consumes: comportamento real de `install.sh` (Task 4) e do checkbox (Task 2).
- Produces: documentação final do milestone. Nada de código.

- [ ] **Step 1: README.md — nova seção de instalação**

Inserir ANTES da seção `## Install` existente:

```markdown
## Install (native app — recommended)

One command builds SagmoWhisper.app on your own Mac and installs it into
/Applications — no Apple Developer account, no cost (the build is signed
locally with a free ad-hoc signature):

```bash
brew install portaudio libsndfile
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper
./install.sh
```

The installer also turns on **Open at login** — toggle it any time with the
"Abrir no login" checkbox in **🎙️ > Configurações…**. To remove the app later
run `./install.sh --uninstall` (your settings and Keychain keys are kept).
```

Depois: renomear o heading `## Install` existente para
`## Install (dev mode — run from source)` e, dentro dele, corrigir a linha
`cd SagmoWhisper/voz` para `cd SagmoWhisper` (o repo não tem subpasta `voz`).

- [ ] **Step 2: README.md — permissões e login**

Substituir o parágrafo de abertura da seção `## Required macOS permissions`
(as duas linhas "In **System Settings > Privacy & Security**, grant your
terminal (or the Python process) these three permissions:") por:

```markdown
In **System Settings > Privacy & Security**, grant **SagmoWhisper** (or your
terminal, when running in dev mode) these three permissions:
```

E ajustar os itens 1-3 para:

```markdown
1. **Microphone** — asked automatically on the first recording.
2. **Accessibility** — add SagmoWhisper with the **+** button, so the
   programmatic Cmd+V can paste the text.
3. **Input Monitoring** — add SagmoWhisper with the **+** button, so the
   global F8 hotkey can be captured.
```

Na seção `### Run in the background`, substituir a linha final
"To start at login, create a LaunchAgent in `~/Library/LaunchAgents/`." por:

```markdown
To start at login, use the **Abrir no login** checkbox in
**🎙️ > Configurações…** (requires the installed app).
```

- [ ] **Step 3: README.pt-BR.md — mesmas mudanças, em português**

Inserir ANTES da seção `## Instalação` existente:

```markdown
## Instalação (app nativo — recomendado)

Um único comando monta o SagmoWhisper.app no seu próprio Mac e instala em
/Applications — sem conta Apple Developer, sem custo (o build é assinado
localmente com assinatura ad-hoc gratuita):

```bash
brew install portaudio libsndfile
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper
./install.sh
```

O instalador também liga **Abrir no login** — mude quando quiser pelo checkbox
"Abrir no login" em **🎙️ > Configurações…**. Para remover o app depois, rode
`./install.sh --uninstall` (suas configurações e chaves no Keychain são
preservadas).
```

Depois: renomear `## Instalação` para
`## Instalação (modo dev — rodar do código)` e corrigir `cd SagmoWhisper/voz`
para `cd SagmoWhisper`. Na seção `## Permissões macOS obrigatórias`, aplicar o
equivalente em português do Step 2 (conceder ao **SagmoWhisper** — ou ao
terminal em modo dev; Microfone pedido automaticamente na primeira gravação;
Acessibilidade e Monitoramento de Entrada adicionados com o botão **+**). Na
seção de background, trocar a menção a criar LaunchAgent manualmente pelo
checkbox "Abrir no login" em **🎙️ > Configurações…**.

- [ ] **Step 4: docs/STATUS.md — checkpoint do Milestone 3**

Atualizar `docs/STATUS.md`: marcar o Milestone 3 como entregue no branch
`feature/m3-app-bundle`, listando as tasks 1-6 com os **hashes reais** dos
commits (obter com `git log --oneline main..HEAD` — PROIBIDO deixar
placeholder), estado dos testes (**92 passed**, ruff limpo, 100% em
`src/core/*`), e a seção "Próxima task" apontando para o gate humano:

```markdown
## Próxima task

Milestone 3 aguardando: (a) revisão final do branch + PR; (b) fumaça humana
pós-instalação — PENDENTE DE HUMANO:
- [ ] `./install.sh` completo (mata instância dev, instala em /Applications, abre)
- [ ] Ícone 🎙️ na barra, NENHUM ícone no Dock, nenhum "Python" visível
- [ ] Conceder Acessibilidade + Monitoramento de Entrada ao SagmoWhisper; prompt de Microfone na 1ª gravação
- [ ] Checkbox "Abrir no login" habilitado e marcado nas Configurações; desmarcar/remarcar cria/remove o plist em ~/Library/LaunchAgents/
- [ ] Ditado F8 real pelo bundle
- [ ] Reiniciar o Mac → app abre sozinho (RunAtLoad)
```

Manter o restante do arquivo consistente (não inventar fatos; tudo que for
afirmado tem que ter sido executado de verdade nesta sessão).

- [ ] **Step 5: Suíte + lint (nada quebrou)**

Run: `.venv/bin/pytest && .venv/bin/ruff check src tests`
Expected: **92 passed**, `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add README.md README.pt-BR.md docs/STATUS.md
git commit -m "docs: instalação do app nativo (EN/pt-BR) + checkpoint do Milestone 3"
```

---

## Fim do plano — fluxo de fechamento (controlador)

Após a Task 6: revisão final do branch inteiro (modelo mais capaz), fix wave
única se houver achados, instalação real via `./install.sh` (gate humano
descrito no STATUS), push e PR para `main` — NUNCA merge direto.
