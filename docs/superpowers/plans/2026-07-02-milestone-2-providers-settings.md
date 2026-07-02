# Milestone 2 — Providers + Configurações Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Providers plugáveis (Groq / OpenAI / faster-whisper local), API keys no Keychain via keyring, config JSON persistente e janela nativa de Configurações que aplica na hora.

**Architecture:** O contrato `TranscriptionProvider`/`CleanupProvider` + catálogo de modelos vive em `src/core/providers/base.py` (puro). Cada provider é um módulo com as mesmas formas de classe; uma factory pura monta transcriber/cleaner a partir do `Config` + Keychain. A UI (`src/macos/settings_window.py`) só lê o catálogo e chama a factory — zero regra de negócio no AppKit. `src/app.py` ganha o item "Configurações…" e um `_apply_config` que recria pipeline/hotkey sem reiniciar.

**Tech Stack:** Python 3.11, pyobjc (AppKit), keyring (Keychain), groq, openai (novo), faster-whisper (opcional, lazy), pytest, ruff.

## Global Constraints

- Camadas: `src/core/` é 100% puro (sem AppKit, sem I/O de UI), TDD com 100% de cobertura; `src/macos/` é adapter AppKit validado por fumaça manual documentada — sem testes unitários.
- ruff limpo com `Metrics` do pyproject: complexidade ciclomática ≤ 4 por método (`mccabe max-complexity = 4`).
- SEGURANÇA (LEI 9): API key JAMAIS no config JSON, JAMAIS em log, JAMAIS commitada. Keys só no Keychain (service `"SagmoWhisper"`, account = nome do provider) ou em env var de dev (`GROQ_API_KEY`/`OPENAI_API_KEY` como override).
- Config JSON em `~/Library/Application Support/SagmoWhisper/config.json`; `.env` continua como override de dev (env var vence JSON).
- Migração silenciosa: na primeira execução, se existir `GROQ_API_KEY` no ambiente/.env e NÃO existir config JSON, gravar a key no Keychain e criar o JSON com defaults.
- Modelos por provider (copiar verbatim):
  - groq: transcrição `whisper-large-v3-turbo` (default), `whisper-large-v3`; limpeza `llama-3.1-8b-instant`
  - openai: transcrição `whisper-1`, `gpt-4o-transcribe`; limpeza `gpt-4o-mini`
  - local: faster-whisper, modelo `small` (default); NÃO suporta limpeza; NÃO usa API key
- faster-whisper é dependência **opcional**: extra `[local]` no pyproject, import lazy — o app funciona sem ela instalada.
- Erros de provider viram `TranscriptionError(provider, detail)`; `str(err)` = `"<provider>: <detail>"`.
- Strings exatas de UI: item de menu `"Configurações…"` (com reticências U+2026), título da janela `"Configurações"`, botões `"Testar conexão"` e `"Salvar"`, labels de provider `"Groq"`, `"OpenAI"`, `"Local"`, resultado do teste `"✓ Conexão OK"` / `"✗ <mensagem do erro>"`, confirmação `"✓ Salvo e aplicado"`.
- Salvar aplica na hora: grava JSON + Keychain e chama callback `on_save(config)`; o app recria pipeline e hotkey sem reiniciar.
- pyobjc: NUNCA usar inicializadores variádicos (ex.: `initWithColorsAndLocations_` — SIGILL); helpers Python puros com múltiplos args em subclasses de NSObject levam `@objc.python_method`.
- Commits em português, estilo conventional commits, terminando com `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Comandos de teste: `source .venv/bin/activate` antes; suíte = `pytest`, lint = `ruff check src tests`.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `src/core/providers/__init__.py` | pacote | 1 |
| `src/core/providers/base.py` | Protocols, `TranscriptionError`, `PROVIDER_CATALOG`, prompt de limpeza | 1, 4 |
| `src/core/secrets.py` | get/set de API key no Keychain via keyring | 2 |
| `src/core/config.py` | Config novo: JSON + override de env + migração do .env | 3 |
| `src/core/providers/groq_provider.py` | migração de `transcriber.py`/`cleaner.py` + `test_connection` | 4 |
| `src/core/providers/openai_provider.py` | provider OpenAI | 5 |
| `src/core/providers/local_provider.py` | faster-whisper lazy | 6 |
| `src/core/providers/factory.py` | resolve key + monta transcriber/cleaner + testar conexão | 7 |
| `src/macos/settings_window.py` | janela nativa de preferências | 8 |
| `src/app.py` | menu "Configurações…", `_apply_config`, pipeline opcional | 9 |
| Removidos: `src/transcriber.py`, `src/cleaner.py` (Task 4); `src/config.py` (Task 9) | | |

`src/pipeline.py`, `src/audio_recorder.py`, `src/text_injector.py` NÃO são tocados
(migram no Milestone 3). A factory passa `enable_cleanup = cleaner is not None`
para o pipeline atual continuar intacto.

---

### Task 1: Contrato de provider + catálogo (`base.py`)

**Files:**
- Create: `src/core/providers/__init__.py` (vazio)
- Create: `src/core/providers/base.py`
- Test: `tests/core/providers/__init__.py` (vazio), `tests/core/providers/test_base.py`

**Interfaces:**
- Consumes: nada (módulo folha, puro).
- Produces: `TranscriptionProvider` (Protocol com `transcribe(audio_path: Path) -> str`), `CleanupProvider` (Protocol com `clean(text: str) -> str`), `TranscriptionError(provider: str, detail: str)` com atributos `.provider`/`.detail`, `ProviderInfo` (dataclass frozen: `key`, `label`, `needs_api_key`, `transcription_models: tuple`, `cleanup_models: tuple`), `PROVIDER_CATALOG: dict[str, ProviderInfo]`.

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/core/providers/test_base.py
from src.core.providers.base import PROVIDER_CATALOG, TranscriptionError


def test_error_expoe_provider_e_detail():
    err = TranscriptionError("groq", "401 invalid key")
    assert err.provider == "groq"
    assert err.detail == "401 invalid key"
    assert str(err) == "groq: 401 invalid key"


def test_catalogo_tem_os_tres_providers():
    assert set(PROVIDER_CATALOG) == {"groq", "openai", "local"}
    assert [PROVIDER_CATALOG[k].label for k in ("groq", "openai", "local")] == [
        "Groq", "OpenAI", "Local"
    ]


def test_modelos_groq_verbatim_do_spec():
    info = PROVIDER_CATALOG["groq"]
    assert info.transcription_models == (
        "whisper-large-v3-turbo", "whisper-large-v3"
    )
    assert info.cleanup_models == ("llama-3.1-8b-instant",)
    assert info.needs_api_key is True


def test_modelos_openai_verbatim_do_spec():
    info = PROVIDER_CATALOG["openai"]
    assert info.transcription_models == ("whisper-1", "gpt-4o-transcribe")
    assert info.cleanup_models == ("gpt-4o-mini",)
    assert info.needs_api_key is True


def test_local_sem_key_e_sem_limpeza():
    info = PROVIDER_CATALOG["local"]
    assert info.transcription_models == ("small",)
    assert info.cleanup_models == ()
    assert info.needs_api_key is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/core/providers/test_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.providers'`

- [ ] **Step 3: Implementação mínima**

```python
# src/core/providers/base.py
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: Path) -> str: ...


class CleanupProvider(Protocol):
    def clean(self, text: str) -> str: ...


class TranscriptionError(Exception):
    """Erro tipado de provider; a UI mostra str(err) = 'provider: detail'."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider}: {detail}")


@dataclass(frozen=True)
class ProviderInfo:
    key: str
    label: str
    needs_api_key: bool
    transcription_models: tuple[str, ...]
    cleanup_models: tuple[str, ...]  # vazio = provider não suporta limpeza


PROVIDER_CATALOG: dict[str, ProviderInfo] = {
    "groq": ProviderInfo(
        "groq", "Groq", True,
        ("whisper-large-v3-turbo", "whisper-large-v3"),
        ("llama-3.1-8b-instant",),
    ),
    "openai": ProviderInfo(
        "openai", "OpenAI", True,
        ("whisper-1", "gpt-4o-transcribe"),
        ("gpt-4o-mini",),
    ),
    "local": ProviderInfo("local", "Local", False, ("small",), ()),
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/core/providers/test_base.py -v`
Expected: 5 passed. Depois `ruff check src tests` limpo.

- [ ] **Step 5: Commit**

```bash
git add src/core/providers tests/core/providers
git commit -m "feat: contrato de provider, erro tipado e catálogo de modelos"
```

---

### Task 2: Keychain (`secrets.py`)

**Files:**
- Create: `src/core/secrets.py`
- Modify: `requirements.txt` (adicionar `keyring`)
- Test: `tests/core/test_secrets.py`

**Interfaces:**
- Consumes: lib `keyring`.
- Produces: `get_api_key(provider: str) -> str | None`, `set_api_key(provider: str, key: str) -> None`, constante `SERVICE = "SagmoWhisper"`.

- [ ] **Step 1: Instalar dependência**

```bash
source .venv/bin/activate
pip install keyring
```
E adicionar a linha `keyring` em `requirements.txt` (depois de `python-dotenv`).

- [ ] **Step 2: Escrever os testes que falham**

```python
# tests/core/test_secrets.py
from src.core import secrets


def test_get_api_key_le_do_keychain(monkeypatch):
    def fake_get(service, account):
        assert (service, account) == ("SagmoWhisper", "groq")
        return "gsk_teste"

    monkeypatch.setattr(secrets.keyring, "get_password", fake_get)
    assert secrets.get_api_key("groq") == "gsk_teste"


def test_get_api_key_retorna_none_quando_ausente(monkeypatch):
    monkeypatch.setattr(
        secrets.keyring, "get_password", lambda service, account: None
    )
    assert secrets.get_api_key("openai") is None


def test_set_api_key_grava_no_keychain(monkeypatch):
    gravado = {}
    monkeypatch.setattr(
        secrets.keyring,
        "set_password",
        lambda service, account, password: gravado.update(
            {(service, account): password}
        ),
    )
    secrets.set_api_key("openai", "sk-abc")
    assert gravado == {("SagmoWhisper", "openai"): "sk-abc"}
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `pytest tests/core/test_secrets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.secrets'`

- [ ] **Step 4: Implementação mínima**

```python
# src/core/secrets.py
"""API keys ficam SÓ no Keychain do macOS (LEI 9) — nunca em JSON ou log."""
import keyring

SERVICE = "SagmoWhisper"


def get_api_key(provider: str) -> str | None:
    return keyring.get_password(SERVICE, provider)


def set_api_key(provider: str, key: str) -> None:
    keyring.set_password(SERVICE, provider, key)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/core/test_secrets.py -v` → 3 passed; `ruff check src tests` limpo.

- [ ] **Step 6: Commit**

```bash
git add src/core/secrets.py tests/core/test_secrets.py requirements.txt
git commit -m "feat: armazenamento de API keys no Keychain via keyring"
```

---

### Task 3: Config novo (`core/config.py`) — JSON + env override + migração

**Files:**
- Create: `src/core/config.py`
- Test: `tests/core/test_config.py`

**IMPORTANTE:** NÃO tocar em `src/config.py` (o antigo) nem em `tests/test_config.py` — eles continuam servindo o `app.py` atual até a Task 9, quando serão removidos.

**Interfaces:**
- Consumes: `src.core.secrets.set_api_key` (Task 2).
- Produces:
  - `Config` dataclass: `provider: str`, `transcription_model: str`, `cleanup_model: str`, `language: str`, `enable_cleanup: bool`, `hotkey: str`, `sample_rate: int`
  - `Config.load(path: Path = DEFAULT_CONFIG_PATH, env: Mapping | None = None) -> Config` — defaults ← JSON ← env (env vence)
  - `config.save(path: Path = DEFAULT_CONFIG_PATH) -> None` — cria diretórios, grava JSON (SEM nenhuma key)
  - `migrate_env_key_if_needed(path=DEFAULT_CONFIG_PATH, env=None, set_key=secrets.set_api_key) -> bool`
  - `DEFAULT_CONFIG_PATH = Path.home() / "Library" / "Application Support" / "SagmoWhisper" / "config.json"`
  - `DEFAULTS: dict` com `provider="groq"`, `transcription_model="whisper-large-v3-turbo"`, `cleanup_model="llama-3.1-8b-instant"`, `language="pt"`, `enable_cleanup=True`, `hotkey="f8"`, `sample_rate=16000`

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/core/test_config.py
import json

from src.core.config import DEFAULTS, Config, migrate_env_key_if_needed


def test_load_sem_json_e_sem_env_usa_defaults(tmp_path):
    cfg = Config.load(path=tmp_path / "config.json", env={})
    assert cfg.provider == "groq"
    assert cfg.transcription_model == "whisper-large-v3-turbo"
    assert cfg.cleanup_model == "llama-3.1-8b-instant"
    assert cfg.language == "pt"
    assert cfg.enable_cleanup is True
    assert cfg.hotkey == "f8"
    assert cfg.sample_rate == 16000


def test_load_le_json_existente(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"provider": "openai", "hotkey": "f9"}))
    cfg = Config.load(path=p, env={})
    assert cfg.provider == "openai"
    assert cfg.hotkey == "f9"
    assert cfg.language == "pt"  # campo ausente no JSON cai no default


def test_env_vence_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"provider": "openai"}))
    cfg = Config.load(path=p, env={"PROVIDER": "Local", "SAMPLE_RATE": "8000"})
    assert cfg.provider == "local"  # normalizado para minúsculas
    assert cfg.sample_rate == 8000


def test_enable_cleanup_parseia_false_do_env(tmp_path):
    cfg = Config.load(path=tmp_path / "c.json", env={"ENABLE_CLEANUP": "FALSE"})
    assert cfg.enable_cleanup is False


def test_save_cria_diretorio_e_persiste_sem_keys(tmp_path):
    p = tmp_path / "sub" / "config.json"
    cfg = Config(**DEFAULTS)
    cfg.save(path=p)
    data = json.loads(p.read_text())
    assert data == DEFAULTS
    assert "api_key" not in json.dumps(data).lower()
    assert Config.load(path=p, env={}) == cfg


def test_migracao_primeira_execucao_grava_keychain_e_json(tmp_path):
    p = tmp_path / "config.json"
    chamadas = []
    ok = migrate_env_key_if_needed(
        path=p,
        env={"GROQ_API_KEY": "gsk_migra"},
        set_key=lambda prov, key: chamadas.append((prov, key)),
    )
    assert ok is True
    assert chamadas == [("groq", "gsk_migra")]
    assert json.loads(p.read_text()) == DEFAULTS


def test_migracao_nao_roda_se_json_ja_existe(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{}")
    ok = migrate_env_key_if_needed(
        path=p, env={"GROQ_API_KEY": "x"}, set_key=lambda *_: 1 / 0
    )
    assert ok is False


def test_migracao_nao_roda_sem_key_no_env(tmp_path):
    ok = migrate_env_key_if_needed(
        path=tmp_path / "config.json", env={}, set_key=lambda *_: 1 / 0
    )
    assert ok is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/core/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.config'`

- [ ] **Step 3: Implementação mínima**

```python
# src/core/config.py
"""Config persistente em JSON; .env/env vars são override de dev (env vence).

API keys NUNCA entram neste JSON — vivem no Keychain (src/core/secrets.py).
"""
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.core import secrets

DEFAULT_CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "SagmoWhisper"
    / "config.json"
)

DEFAULTS = {
    "provider": "groq",
    "transcription_model": "whisper-large-v3-turbo",
    "cleanup_model": "llama-3.1-8b-instant",
    "language": "pt",
    "enable_cleanup": True,
    "hotkey": "f8",
    "sample_rate": 16000,
}

_ENV_PARSERS = {
    "PROVIDER": ("provider", str.lower),
    "TRANSCRIPTION_MODEL": ("transcription_model", str),
    "CLEANUP_MODEL": ("cleanup_model", str),
    "LANGUAGE": ("language", str),
    "ENABLE_CLEANUP": ("enable_cleanup", lambda v: v.lower() == "true"),
    "HOTKEY": ("hotkey", str.lower),
    "SAMPLE_RATE": ("sample_rate", int),
}


def _real_env() -> Mapping:
    load_dotenv()
    return os.environ


def _apply_env(data: dict, env: Mapping) -> None:
    for var, (field, parse) in _ENV_PARSERS.items():
        if env.get(var):
            data[field] = parse(env[var])


@dataclass
class Config:
    provider: str
    transcription_model: str
    cleanup_model: str
    language: str
    enable_cleanup: bool
    hotkey: str
    sample_rate: int

    @classmethod
    def load(
        cls, path: Path = DEFAULT_CONFIG_PATH, env: Mapping | None = None
    ) -> "Config":
        if env is None:
            env = _real_env()
        data = dict(DEFAULTS)
        if path.exists():
            data.update(json.loads(path.read_text()))
        _apply_env(data, env)
        return cls(**data)

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False)
        )


def migrate_env_key_if_needed(
    path: Path = DEFAULT_CONFIG_PATH,
    env: Mapping | None = None,
    set_key=secrets.set_api_key,
) -> bool:
    """Primeira execução: importa GROQ_API_KEY do .env para o Keychain."""
    if path.exists():
        return False
    if env is None:
        env = _real_env()
    key = env.get("GROQ_API_KEY")
    if not key:
        return False
    set_key("groq", key)
    Config(**DEFAULTS).save(path)
    return True
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/core/test_config.py -v` → 8 passed; suíte inteira `pytest` verde (o config antigo segue intacto); `ruff check src tests` limpo.

- [ ] **Step 5: Commit**

```bash
git add src/core/config.py tests/core/test_config.py
git commit -m "feat: config JSON persistente com override de env e migração do .env"
```

---

### Task 4: Migrar Groq para provider (`groq_provider.py`)

**Files:**
- Modify: `src/core/providers/base.py` (adicionar `CLEANUP_SYSTEM_PROMPT` — mover verbatim de `src/cleaner.py`)
- Create: `src/core/providers/groq_provider.py`
- Modify: `src/app.py` (imports e nomes de classe apenas)
- Delete: `src/transcriber.py`, `src/cleaner.py`, `tests/test_transcriber.py`, `tests/test_cleaner.py`
- Test: `tests/core/providers/test_groq_provider.py`

**Interfaces:**
- Consumes: `TranscriptionError`, `CLEANUP_SYSTEM_PROMPT` (base.py).
- Produces: `GroqTranscriber(client, model: str, language: str)` com `.transcribe(audio_path) -> str`; `GroqCleaner(client, model: str)` com `.clean(text) -> str`; `make_client(api_key: str) -> Groq`; `test_connection(api_key: str, client_factory=make_client) -> None` (levanta `TranscriptionError` em falha). Assinaturas dos construtores IDÊNTICAS às classes antigas (`Transcriber`/`Cleaner`) — o `app.py` só troca import e nome.

- [ ] **Step 1: Mover o prompt para `base.py`**

Adicionar ao FINAL de `src/core/providers/base.py` (copiar o texto EXATO de `src/cleaner.py:1-13`, renomeando para `CLEANUP_SYSTEM_PROMPT`):

```python
CLEANUP_SYSTEM_PROMPT = (
    "Você é um corretor ortográfico de transcrições de voz em português do Brasil. "
    "REGRAS ABSOLUTAS: "
    "1) Retorne SOMENTE o texto transcrito corrigido — nunca responda, "
    "complemente, explique ou adicione conteúdo novo. "
    "2) Remova apenas hesitações (é, tipo, né, hm, ah) e fragmentos repetidos "
    "no final (artefatos do Whisper). "
    "3) Corrija pontuação e ortografia sem alterar o sentido. "
    "4) Se o texto for curto (ex: 'sim', 'ok', 'boa'), retorne exatamente "
    "esse texto curto. "
    "PROIBIDO: responder ao conteúdo, gerar texto novo, completar frases, "
    "comentar."
)
```

- [ ] **Step 2: Escrever os testes que falham**

```python
# tests/core/providers/test_groq_provider.py
from types import SimpleNamespace

import pytest

from src.core.providers.base import CLEANUP_SYSTEM_PROMPT, TranscriptionError
from src.core.providers.groq_provider import (
    GroqCleaner,
    GroqTranscriber,
    test_connection,
)


class _FakeClient:
    def __init__(self, text="  olá mundo  ", fail=False):
        self.calls = []
        fake = self

        def create(**kwargs):
            fake.calls.append(kwargs)
            if fail:
                raise RuntimeError("401 invalid api key")
            return SimpleNamespace(
                text=text,
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=text))
                ],
            )

        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(create=create)
        )
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=create)
        )


def test_transcribe_retorna_texto_limpo(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = GroqTranscriber(_FakeClient(), "whisper-large-v3-turbo", "pt")

    assert t.transcribe(audio) == "olá mundo"


def test_transcribe_passa_modelo_lingua_e_nome_do_arquivo(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    client = _FakeClient()
    GroqTranscriber(client, "whisper-large-v3", "pt").transcribe(audio)

    call = client.calls[0]
    assert call["model"] == "whisper-large-v3"
    assert call["language"] == "pt"
    assert call["file"][0] == "fala.wav"


def test_transcribe_embrulha_falha_em_transcription_error(tmp_path):
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")
    t = GroqTranscriber(_FakeClient(fail=True), "m", "pt")

    with pytest.raises(TranscriptionError) as exc:
        t.transcribe(audio)
    assert exc.value.provider == "groq"
    assert "401" in exc.value.detail


def test_clean_usa_prompt_e_temperatura_baixa():
    client = _FakeClient(text="texto corrigido")
    result = GroqCleaner(client, "llama-3.1-8b-instant").clean("texto bruto")

    assert result == "texto corrigido"
    call = client.calls[0]
    assert call["temperature"] == 0.2
    assert call["messages"][0] == {
        "role": "system",
        "content": CLEANUP_SYSTEM_PROMPT,
    }
    assert call["messages"][1] == {"role": "user", "content": "texto bruto"}


def test_clean_embrulha_falha_em_transcription_error():
    c = GroqCleaner(_FakeClient(fail=True), "m")
    with pytest.raises(TranscriptionError) as exc:
        c.clean("x")
    assert exc.value.provider == "groq"


def test_test_connection_ok_nao_levanta():
    fake = SimpleNamespace(models=SimpleNamespace(list=lambda: []))
    test_connection("gsk_x", client_factory=lambda key: fake)


def test_test_connection_falha_vira_transcription_error():
    def boom(key):
        raise RuntimeError("rede fora")

    with pytest.raises(TranscriptionError) as exc:
        test_connection("gsk_x", client_factory=boom)
    assert exc.value.provider == "groq"
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `pytest tests/core/providers/test_groq_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.providers.groq_provider'`

- [ ] **Step 4: Implementação**

```python
# src/core/providers/groq_provider.py
from pathlib import Path

from groq import Groq

from src.core.providers.base import CLEANUP_SYSTEM_PROMPT, TranscriptionError


class GroqTranscriber:
    def __init__(self, client, model: str, language: str):
        self._client = client
        self._model = model
        self._language = language

    def transcribe(self, audio_path: Path) -> str:
        try:
            with open(audio_path, "rb") as audio_file:
                result = self._client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self._model,
                    language=self._language,
                )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        return result.text.strip()


class GroqCleaner:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def clean(self, text: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": CLEANUP_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        return completion.choices[0].message.content.strip()


def make_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


def test_connection(api_key: str, client_factory=make_client) -> None:
    """Chamada mínima (lista modelos) para validar a key sem gastar tokens."""
    try:
        client_factory(api_key).models.list()
    except Exception as e:
        raise TranscriptionError("groq", str(e)) from e
```

- [ ] **Step 5: Rewire do `app.py` e remoção dos módulos antigos**

Em `src/app.py`, trocar:

```python
from src.cleaner import Cleaner
...
from src.transcriber import Transcriber
```
por:
```python
from src.core.providers.groq_provider import GroqCleaner, GroqTranscriber
```
E no `__init__` de `VozMenuBar`, trocar `Transcriber(` por `GroqTranscriber(` e `Cleaner(` por `GroqCleaner(` (mesmos argumentos).

Depois:
```bash
git rm src/transcriber.py src/cleaner.py tests/test_transcriber.py tests/test_cleaner.py
```

- [ ] **Step 6: Rodar suíte inteira + lint + fumaça**

Run: `pytest` → tudo verde (os testes antigos de transcriber/cleaner saíram; os novos cobrem o mesmo comportamento + erros). `ruff check src tests` limpo.
Fumaça: `.venv/bin/python -c "from src.app import VozMenuBar; print('imports ok')"` → `imports ok`.

- [ ] **Step 7: Commit**

```bash
git add -A src tests requirements.txt
git commit -m "refactor: código Groq migra para core/providers com erro tipado"
```

---

### Task 5: Provider OpenAI (`openai_provider.py`)

**Files:**
- Create: `src/core/providers/openai_provider.py`
- Modify: `requirements.txt` (adicionar `openai`)
- Test: `tests/core/providers/test_openai_provider.py`

**Interfaces:**
- Consumes: `TranscriptionError`, `CLEANUP_SYSTEM_PROMPT` (base.py).
- Produces: `OpenAITranscriber(client, model: str, language: str)`, `OpenAICleaner(client, model: str)`, `make_client(api_key: str) -> OpenAI`, `test_connection(api_key: str, client_factory=make_client) -> None`. Mesmas formas do groq_provider — a factory (Task 7) trata os dois simetricamente.

- [ ] **Step 1: Instalar dependência**

```bash
source .venv/bin/activate && pip install openai
```
Adicionar `openai` em `requirements.txt` (depois de `groq`).

- [ ] **Step 2: Escrever os testes que falham**

O arquivo é o espelho do de Groq — reutilizar o mesmo fake. Copiar
`tests/core/providers/test_groq_provider.py` para
`tests/core/providers/test_openai_provider.py` e ajustar: imports
(`from src.core.providers.openai_provider import OpenAICleaner, OpenAITranscriber, test_connection`),
classes (`OpenAITranscriber`/`OpenAICleaner`), provider esperado nos erros
(`exc.value.provider == "openai"`), modelos usados nos testes
(`"whisper-1"` e `"gpt-4o-mini"`). O corpo dos testes é idêntico — mesmos
nomes de teste, mesmos asserts de temperatura/prompt/arquivo.

- [ ] **Step 3: Rodar e ver falhar**

Run: `pytest tests/core/providers/test_openai_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.providers.openai_provider'`

- [ ] **Step 4: Implementação**

```python
# src/core/providers/openai_provider.py
from pathlib import Path

from openai import OpenAI

from src.core.providers.base import CLEANUP_SYSTEM_PROMPT, TranscriptionError


class OpenAITranscriber:
    def __init__(self, client, model: str, language: str):
        self._client = client
        self._model = model
        self._language = language

    def transcribe(self, audio_path: Path) -> str:
        try:
            with open(audio_path, "rb") as audio_file:
                result = self._client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self._model,
                    language=self._language,
                )
        except Exception as e:
            raise TranscriptionError("openai", str(e)) from e
        return result.text.strip()


class OpenAICleaner:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def clean(self, text: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": CLEANUP_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
        except Exception as e:
            raise TranscriptionError("openai", str(e)) from e
        return completion.choices[0].message.content.strip()


def make_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def test_connection(api_key: str, client_factory=make_client) -> None:
    """Chamada mínima (lista modelos) para validar a key sem gastar tokens."""
    try:
        client_factory(api_key).models.list()
    except Exception as e:
        raise TranscriptionError("openai", str(e)) from e
```

Nota de revisão: a duplicação estrutural entre groq/openai é decisão do
plano — os SDKs têm a mesma interface HOJE, mas são libs independentes que
podem divergir; abstrair agora seria acoplamento prematuro (YAGNI). O que é
regra de domínio única (o prompt) já mora em um lugar só (`base.py`).

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/core/providers/test_openai_provider.py -v` → 7 passed; `pytest` inteiro verde; `ruff check src tests` limpo.

- [ ] **Step 6: Commit**

```bash
git add src/core/providers/openai_provider.py tests/core/providers/test_openai_provider.py requirements.txt
git commit -m "feat: provider OpenAI (whisper-1/gpt-4o-transcribe + gpt-4o-mini)"
```

---

### Task 6: Provider local (`local_provider.py`, faster-whisper lazy)

**Files:**
- Create: `src/core/providers/local_provider.py`
- Modify: `pyproject.toml` (renomear projeto para `sagmowhisper` + extra `[local]`)
- Test: `tests/core/providers/test_local_provider.py`

**Interfaces:**
- Consumes: `TranscriptionError` (base.py).
- Produces: `LocalTranscriber(model_size: str = "small", language: str = "pt")` com `.transcribe(audio_path) -> str`; `test_connection(api_key: str = "", find_spec=importlib.util.find_spec) -> None`. NÃO existe cleaner local (catálogo tem `cleanup_models=()`).
- faster-whisper NÃO vai para `requirements.txt` — é opcional.

- [ ] **Step 1: pyproject — nome do projeto e extra opcional**

Em `pyproject.toml`, seção `[project]`: trocar `name = "voz"` por `name = "sagmowhisper"` e adicionar após a seção `[project]`:

```toml
[project.optional-dependencies]
local = ["faster-whisper"]
```

- [ ] **Step 2: Escrever os testes que falham**

```python
# tests/core/providers/test_local_provider.py
import sys
from types import SimpleNamespace

import pytest

from src.core.providers.base import TranscriptionError
from src.core.providers.local_provider import LocalTranscriber, test_connection


def _fake_module(constructed: list):
    class FakeWhisperModel:
        def __init__(self, model_size):
            constructed.append(model_size)

        def transcribe(self, path, language):
            segments = [
                SimpleNamespace(text=" olá "),
                SimpleNamespace(text="mundo "),
            ]
            return segments, SimpleNamespace(language=language)

    return SimpleNamespace(WhisperModel=FakeWhisperModel)


def test_transcribe_junta_segmentos(monkeypatch, tmp_path):
    constructed = []
    monkeypatch.setitem(
        sys.modules, "faster_whisper", _fake_module(constructed)
    )
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    t = LocalTranscriber()
    assert t.transcribe(audio) == "olá mundo"
    assert constructed == ["small"]


def test_modelo_carrega_uma_vez_so(monkeypatch, tmp_path):
    constructed = []
    monkeypatch.setitem(
        sys.modules, "faster_whisper", _fake_module(constructed)
    )
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    t = LocalTranscriber()
    t.transcribe(audio)
    t.transcribe(audio)
    assert constructed == ["small"]


def test_sem_faster_whisper_vira_erro_tipado_com_instrucao(
    monkeypatch, tmp_path
):
    # sys.modules[nome] = None faz o import levantar ImportError
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber().transcribe(audio)
    assert exc.value.provider == "local"
    assert "sagmowhisper[local]" in exc.value.detail


def test_falha_do_modelo_vira_erro_tipado(monkeypatch, tmp_path):
    class Boom:
        def __init__(self, model_size):
            pass

        def transcribe(self, path, language):
            raise RuntimeError("cuda indisponível")

    monkeypatch.setitem(
        sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Boom)
    )
    audio = tmp_path / "fala.wav"
    audio.write_bytes(b"RIFFfake")

    with pytest.raises(TranscriptionError) as exc:
        LocalTranscriber().transcribe(audio)
    assert exc.value.provider == "local"


def test_test_connection_ok_quando_instalado():
    test_connection(find_spec=lambda name: object())


def test_test_connection_falha_quando_ausente():
    with pytest.raises(TranscriptionError) as exc:
        test_connection(find_spec=lambda name: None)
    assert "sagmowhisper[local]" in exc.value.detail
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `pytest tests/core/providers/test_local_provider.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.providers.local_provider'`

- [ ] **Step 4: Implementação**

```python
# src/core/providers/local_provider.py
"""faster-whisper é dependência OPCIONAL: import lazy para o app abrir sem ela."""
import importlib.util
from pathlib import Path

from src.core.providers.base import TranscriptionError

_INSTALL_HINT = (
    "faster-whisper não instalado. "
    "Instale com: pip install 'sagmowhisper[local]'"
)


class LocalTranscriber:
    def __init__(self, model_size: str = "small", language: str = "pt"):
        self._model_size = model_size
        self._language = language
        self._model = None

    def _load_model(self):
        # download automático do modelo no primeiro uso (aviso fica na UI)
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise TranscriptionError("local", _INSTALL_HINT) from e
        self._model = WhisperModel(self._model_size)
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        model = self._load_model()
        try:
            segments, _info = model.transcribe(
                str(audio_path), language=self._language
            )
            return " ".join(s.text.strip() for s in segments).strip()
        except Exception as e:
            raise TranscriptionError("local", str(e)) from e


def test_connection(
    api_key: str = "", find_spec=importlib.util.find_spec
) -> None:
    if find_spec("faster_whisper") is None:
        raise TranscriptionError("local", _INSTALL_HINT)
```

- [ ] **Step 5: Rodar e ver passar**

Run: `pytest tests/core/providers/test_local_provider.py -v` → 6 passed; `pytest` inteiro verde; `ruff check src tests` limpo.

- [ ] **Step 6: Commit**

```bash
git add src/core/providers/local_provider.py tests/core/providers/test_local_provider.py pyproject.toml
git commit -m "feat: provider local faster-whisper como dependência opcional (lazy)"
```

---

### Task 7: Factory de providers (`factory.py`)

**Files:**
- Create: `src/core/providers/factory.py`
- Test: `tests/core/providers/test_factory.py`

**Interfaces:**
- Consumes: `Config` (Task 3), `secrets.get_api_key` (Task 2), os 3 módulos de provider (Tasks 4-6), `PROVIDER_CATALOG`/`TranscriptionError` (Task 1).
- Produces:
  - `resolve_api_key(provider: str, env: Mapping | None = None) -> str | None` — env var de dev (`GROQ_API_KEY`/`OPENAI_API_KEY`) vence o Keychain
  - `build_components(config: Config) -> tuple[transcriber, cleaner | None]` — cleaner `None` quando limpeza desativada ou sem suporte; levanta `TranscriptionError(provider, "API key ausente. Configure em Configurações…")` se precisar de key e não houver
  - `test_connection(provider: str, api_key: str | None) -> None` — despacha para o módulo do provider

- [ ] **Step 1: Escrever os testes que falham**

```python
# tests/core/providers/test_factory.py
import pytest

from src.core.config import DEFAULTS, Config
from src.core.providers import factory
from src.core.providers.base import TranscriptionError
from src.core.providers.groq_provider import GroqCleaner, GroqTranscriber
from src.core.providers.local_provider import LocalTranscriber
from src.core.providers.openai_provider import (
    OpenAICleaner,
    OpenAITranscriber,
)


def _cfg(**overrides) -> Config:
    return Config(**{**DEFAULTS, **overrides})


def test_resolve_api_key_env_vence_keychain(monkeypatch):
    monkeypatch.setattr(
        factory.secrets, "get_api_key", lambda p: "do_keychain"
    )
    assert (
        factory.resolve_api_key("groq", env={"GROQ_API_KEY": "do_env"})
        == "do_env"
    )


def test_resolve_api_key_cai_no_keychain(monkeypatch):
    monkeypatch.setattr(
        factory.secrets, "get_api_key", lambda p: "do_keychain"
    )
    assert factory.resolve_api_key("openai", env={}) == "do_keychain"


def test_resolve_api_key_local_nao_tem_env_var(monkeypatch):
    monkeypatch.setattr(factory.secrets, "get_api_key", lambda p: None)
    assert factory.resolve_api_key("local", env={}) is None


def test_build_groq(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    transcriber, cleaner = factory.build_components(_cfg())
    assert isinstance(transcriber, GroqTranscriber)
    assert isinstance(cleaner, GroqCleaner)


def test_build_openai(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "sk_x")
    transcriber, cleaner = factory.build_components(
        _cfg(
            provider="openai",
            transcription_model="whisper-1",
            cleanup_model="gpt-4o-mini",
        )
    )
    assert isinstance(transcriber, OpenAITranscriber)
    assert isinstance(cleaner, OpenAICleaner)


def test_build_local_sem_key_e_sem_cleaner(monkeypatch):
    monkeypatch.setattr(
        factory, "resolve_api_key", lambda p: 1 / 0
    )  # não pode ser chamada
    transcriber, cleaner = factory.build_components(
        _cfg(provider="local", transcription_model="small")
    )
    assert isinstance(transcriber, LocalTranscriber)
    assert cleaner is None


def test_build_cleanup_desligado_vira_none(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    _, cleaner = factory.build_components(_cfg(enable_cleanup=False))
    assert cleaner is None


def test_build_sem_key_levanta_erro_com_dica(monkeypatch):
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: None)
    with pytest.raises(TranscriptionError) as exc:
        factory.build_components(_cfg())
    assert "Configurações" in exc.value.detail


def test_test_connection_despacha_para_o_provider(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        factory.groq_provider,
        "test_connection",
        lambda key: chamadas.append(("groq", key)),
    )
    factory.test_connection("groq", "gsk_x")
    assert chamadas == [("groq", "gsk_x")]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `pytest tests/core/providers/test_factory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.core.providers.factory'`

- [ ] **Step 3: Implementação**

```python
# src/core/providers/factory.py
import os
from collections.abc import Mapping

from src.core import secrets
from src.core.config import Config
from src.core.providers import (
    groq_provider,
    local_provider,
    openai_provider,
)
from src.core.providers.base import PROVIDER_CATALOG, TranscriptionError

_ENV_KEY_VARS = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY"}
_MODULES = {
    "groq": groq_provider,
    "openai": openai_provider,
    "local": local_provider,
}


def resolve_api_key(
    provider: str, env: Mapping | None = None
) -> str | None:
    env = os.environ if env is None else env
    env_var = _ENV_KEY_VARS.get(provider)
    if env_var and env.get(env_var):
        return env[env_var]
    return secrets.get_api_key(provider)


def build_components(config: Config):
    """-> (transcriber, cleaner | None); cleaner None = sem limpeza."""
    info = PROVIDER_CATALOG[config.provider]
    api_key = None
    if info.needs_api_key:
        api_key = resolve_api_key(config.provider)
        if not api_key:
            raise TranscriptionError(
                config.provider,
                "API key ausente. Configure em Configurações…",
            )
    return (
        _build_transcriber(config, api_key),
        _build_cleaner(config, api_key, info),
    )


def _build_transcriber(config: Config, api_key: str | None):
    if config.provider == "local":
        return local_provider.LocalTranscriber(
            config.transcription_model, config.language
        )
    module = _MODULES[config.provider]
    transcriber_cls = (
        groq_provider.GroqTranscriber
        if config.provider == "groq"
        else openai_provider.OpenAITranscriber
    )
    return transcriber_cls(
        module.make_client(api_key),
        config.transcription_model,
        config.language,
    )


def _build_cleaner(config: Config, api_key: str | None, info):
    if not config.enable_cleanup or not info.cleanup_models:
        return None
    if config.provider == "groq":
        return groq_provider.GroqCleaner(
            groq_provider.make_client(api_key), config.cleanup_model
        )
    return openai_provider.OpenAICleaner(
        openai_provider.make_client(api_key), config.cleanup_model
    )


def test_connection(provider: str, api_key: str | None) -> None:
    _MODULES[provider].test_connection(api_key or "")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `pytest tests/core/providers/test_factory.py -v` → 9 passed; `pytest` inteiro verde; cobertura 100% em `src/core/` (checar bloco `term-missing`); `ruff check src tests` limpo.

- [ ] **Step 5: Commit**

```bash
git add src/core/providers/factory.py tests/core/providers/test_factory.py
git commit -m "feat: factory de providers com resolução de key (env > Keychain)"
```

---

### Task 8: Janela de Configurações (`settings_window.py`)

**Files:**
- Create: `src/macos/settings_window.py`

Adapter AppKit — SEM testes unitários (política do projeto); validação por fumaça manual no Step 2. Toda a lógica de negócio já está no core (catálogo, factory, config, secrets) — esta janela só liga controles a essas funções.

**Interfaces:**
- Consumes: `PROVIDER_CATALOG` (labels, modelos, needs_api_key), `Config`/`DEFAULT_CONFIG_PATH` (Task 3), `secrets.set_api_key`/`get_api_key` (Task 2), `factory.test_connection` e `factory.resolve_api_key` (Task 7).
- Produces: `SettingsWindowController.alloc().initWithConfig_onSave_(config, on_save)` com método `show()`. `on_save` é chamado com o novo `Config` já persistido (JSON + Keychain), na main thread.

- [ ] **Step 1: Implementação completa**

```python
# src/macos/settings_window.py
"""Janela nativa de preferências. Regra de negócio zero: só liga AppKit ao core."""
import threading

import objc
from AppKit import (
    NSApp,
    NSBackingStoreBuffered,
    NSButton,
    NSButtonTypeSwitch,
    NSMakeRect,
    NSPopUpButton,
    NSSecureTextField,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

from src.core import secrets
from src.core.config import Config
from src.core.providers import factory
from src.core.providers.base import PROVIDER_CATALOG

_W, _H = 440, 340
_LABEL_X, _LABEL_W = 20, 130
_FIELD_X, _FIELD_W = 160, 260
_ROW_H = 24
_HOTKEYS = tuple(f"F{n}" for n in range(1, 13))
_PROVIDER_KEYS = tuple(PROVIDER_CATALOG)  # ("groq", "openai", "local")


class SettingsWindowController(NSObject):
    def initWithConfig_onSave_(self, config, on_save):
        self = objc.super(SettingsWindowController, self).init()
        if self is None:
            return None
        self._config = config
        self._on_save = on_save
        self._build_window()
        return self

    # ---------- construção ----------

    @objc.python_method
    def _build_window(self):
        self._window = (
            NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, _W, _H),
                NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
                NSBackingStoreBuffered,
                False,
            )
        )
        self._window.setTitle_("Configurações")
        self._window.setReleasedWhenClosed_(False)
        self._window.center()
        self._build_fields()
        self._build_buttons()

    @objc.python_method
    def _build_fields(self):
        content = self._window.contentView()
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

    @objc.python_method
    def _build_buttons(self):
        content = self._window.contentView()
        self._test_button = self._button(
            "Testar conexão", 20, 20, 140, "testConnection:"
        )
        self._save_button = self._button(
            "Salvar", _W - 120, 20, 100, "saveSettings:"
        )
        content.addSubview_(self._test_button)
        content.addSubview_(self._save_button)

    @objc.python_method
    def _add_row(self, content, title, y, control):
        label = self._label(title + ":", y + 3, _LABEL_W)
        content.addSubview_(label)
        content.addSubview_(control)
        return label

    @objc.python_method
    def _label(self, text, y, width):
        field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(_LABEL_X, y, width, 18)
        )
        field.setStringValue_(text)
        field.setBezeled_(False)
        field.setDrawsBackground_(False)
        field.setEditable_(False)
        field.setSelectable_(False)
        return field

    @objc.python_method
    def _popup(self, y, action):
        popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(_FIELD_X, y, _FIELD_W, _ROW_H + 2), False
        )
        if action:
            popup.setTarget_(self)
            popup.setAction_(action)
        return popup

    @objc.python_method
    def _checkbox(self, y, title):
        check = NSButton.alloc().initWithFrame_(
            NSMakeRect(_FIELD_X, y, _FIELD_W, _ROW_H)
        )
        check.setButtonType_(NSButtonTypeSwitch)
        check.setTitle_(title)
        return check

    @objc.python_method
    def _button(self, title, x, y, width, action):
        button = NSButton.alloc().initWithFrame_(
            NSMakeRect(x, y, width, 28)
        )
        button.setTitle_(title)
        button.setBezelStyle_(1)  # NSBezelStyleRounded
        button.setTarget_(self)
        button.setAction_(action)
        return button

    # ---------- estado <-> controles ----------

    @objc.python_method
    def _refresh_from_config(self):
        labels = [PROVIDER_CATALOG[k].label for k in _PROVIDER_KEYS]
        self._provider_popup.removeAllItems()
        self._provider_popup.addItemsWithTitles_(labels)
        self._provider_popup.selectItemAtIndex_(
            _PROVIDER_KEYS.index(self._config.provider)
        )
        self._cleanup_check.setState_(1 if self._config.enable_cleanup else 0)
        self._hotkey_popup.selectItemWithTitle_(self._config.hotkey.upper())
        self._status_label.setStringValue_("")
        self._reload_provider_fields(self._config.provider)

    @objc.python_method
    def _reload_provider_fields(self, provider_key):
        info = PROVIDER_CATALOG[provider_key]
        self._fill_popup(
            self._model_popup,
            info.transcription_models,
            self._config.transcription_model,
        )
        self._fill_popup(
            self._cleanup_popup,
            info.cleanup_models,
            self._config.cleanup_model,
        )
        self._api_key_field.setHidden_(not info.needs_api_key)
        self._api_key_label.setHidden_(not info.needs_api_key)
        self._cleanup_check.setEnabled_(bool(info.cleanup_models))
        self._cleanup_popup.setEnabled_(bool(info.cleanup_models))
        stored = factory.resolve_api_key(provider_key) or ""
        self._api_key_field.setStringValue_(stored)

    @objc.python_method
    def _fill_popup(self, popup, options, current):
        popup.removeAllItems()
        popup.addItemsWithTitles_(list(options))
        if current in options:
            popup.selectItemWithTitle_(current)

    @objc.python_method
    def _selected_provider(self):
        return _PROVIDER_KEYS[self._provider_popup.indexOfSelectedItem()]

    @objc.python_method
    def _collect_config(self) -> Config:
        provider = self._selected_provider()
        info = PROVIDER_CATALOG[provider]
        cleanup_model = (
            self._cleanup_popup.titleOfSelectedItem()
            or self._config.cleanup_model
        )
        return Config(
            provider=provider,
            transcription_model=self._model_popup.titleOfSelectedItem(),
            cleanup_model=cleanup_model,
            language=self._config.language,
            enable_cleanup=bool(self._cleanup_check.state())
            and bool(info.cleanup_models),
            hotkey=self._hotkey_popup.titleOfSelectedItem().lower(),
            sample_rate=self._config.sample_rate,
        )

    # ---------- ações (selectors AppKit) ----------

    def providerChanged_(self, sender):
        self._reload_provider_fields(self._selected_provider())

    def testConnection_(self, sender):
        provider = self._selected_provider()
        api_key = str(self._api_key_field.stringValue())
        self._status_label.setStringValue_("Testando…")
        threading.Thread(
            target=self._run_connection_test,
            args=(provider, api_key),
            daemon=True,
        ).start()

    @objc.python_method
    def _run_connection_test(self, provider, api_key):
        try:
            factory.test_connection(provider, api_key)
            result = "✓ Conexão OK"
        except Exception as e:
            result = f"✗ {e}"
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showTestResult:", result, False
        )

    def showTestResult_(self, message):
        self._status_label.setStringValue_(str(message))

    def saveSettings_(self, sender):
        new_config = self._collect_config()
        api_key = str(self._api_key_field.stringValue()).strip()
        if PROVIDER_CATALOG[new_config.provider].needs_api_key and api_key:
            secrets.set_api_key(new_config.provider, api_key)
        new_config.save()
        self._config = new_config
        self._on_save(new_config)
        self._status_label.setStringValue_("✓ Salvo e aplicado")

    # ---------- API pública ----------

    def show(self):
        self._refresh_from_config()
        self._window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)


if __name__ == "__main__":
    # Fumaça manual: python -m src.macos.settings_window
    # Abre a janela com config default; Salvar imprime o config no stdout.
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyAccessory,
    )

    from src.core.config import DEFAULTS

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = SettingsWindowController.alloc().initWithConfig_onSave_(
        Config(**DEFAULTS), lambda cfg: print("on_save:", cfg)
    )
    controller.show()
    app.run()
```

- [ ] **Step 2: Fumaça manual**

Run: `.venv/bin/python -m src.macos.settings_window`
Checklist (documentar o resultado no report):
1. Janela "Configurações" abre centralizada com os 6 controles e 2 botões.
2. Trocar provider para "Local" esconde a linha de API key e desabilita limpeza; voltar para "Groq" restaura.
3. Popup de modelo mostra os modelos do provider selecionado.
4. "Testar conexão" com key inválida mostra `✗ groq: ...` sem travar a UI; com a key real do Keychain/.env mostra `✓ Conexão OK`.
5. "Salvar" imprime `on_save: Config(...)` no terminal, mostra "✓ Salvo e aplicado" e grava `~/Library/Application Support/SagmoWhisper/config.json` SEM nenhuma api key dentro (verificar com `cat`).
6. Fechar a janela e o app com Ctrl+C — sem traceback.

ATENÇÃO pós-fumaça: se o config.json real foi criado no passo 5, está ok — é o comportamento esperado do produto (e a migração da Task 3 já teria criado).
Rodar também: `pytest` (verde) e `ruff check src tests` (limpo) — a janela não pode quebrar nada.

- [ ] **Step 3: Commit**

```bash
git add src/macos/settings_window.py
git commit -m "feat: janela nativa de Configurações com testar conexão e salvar-aplica"
```

---

### Task 9: Wiring no app — menu "Configurações…", aplicar na hora, config novo

**Files:**
- Modify: `src/app.py`
- Delete: `src/config.py`, `tests/test_config.py`
- Modify: `.env.example`, `README.md`, `README.pt-BR.md`, `docs/STATUS.md`

**Interfaces:**
- Consumes: `Config.load`/`migrate_env_key_if_needed` (Task 3), `factory.build_components` (Task 7), `SettingsWindowController` (Task 8), `TranscriptionError` (Task 1).
- Produces: app final do M2. Comportamento novo: sem API key o app ABRE (não crasha), mostra ⚠️ com "Último erro: ... Configure em Configurações…"; F8 sem pipeline vira erro visível; salvar nas Configurações reconstrói pipeline + hotkey na hora.

- [ ] **Step 1: Reescrever imports e construção em `src/app.py`**

Trocar os imports antigos:

```python
from groq import Groq
...
from src.cleaner import Cleaner          # (já virou GroqCleaner na Task 4)
from src.config import Config
from src.core.providers.groq_provider import GroqCleaner, GroqTranscriber
from src.transcriber import Transcriber  # (idem)
```

pelo conjunto novo (remover `from groq import Groq` e o import de groq_provider):

```python
from src.core.config import Config, migrate_env_key_if_needed
from src.core.providers import factory
from src.core.providers.base import TranscriptionError
from src.macos.settings_window import SettingsWindowController
```

No `__init__` de `VozMenuBar`, substituir o bloco que cria `client`/`self._pipeline` (de `client = Groq(...)` até o fechamento do `DictationPipeline(...)`) por:

```python
        self._recorder = AudioRecorder(
            config.sample_rate,
            sample_callback=self._overlay.update_bars,
        )
        self._pipeline = None
        self._settings = (
            SettingsWindowController.alloc().initWithConfig_onSave_(
                config, self._apply_config
            )
        )
```

E, DEPOIS de `self._setup_menu()` (o menu precisa existir para mostrar erro), adicionar:

```python
        self._rebuild_pipeline()
```

Adicionar os dois métodos novos em `VozMenuBar` (depois de `_notify_error`):

```python
    def _rebuild_pipeline(self):
        try:
            transcriber, cleaner = factory.build_components(self._config)
        except TranscriptionError as e:
            self._pipeline = None
            logger.error("Pipeline indisponível: %s", e)
            self._show_error(str(e))
            return
        self._pipeline = DictationPipeline(
            transcriber,
            cleaner,
            TextInjector(),
            enable_cleanup=cleaner is not None,
        )

    def _apply_config(self, new_config):
        # chamado pela janela de Configurações (main thread) — aplica na hora
        self._config = new_config
        self._hotkey = self._resolve_hotkey(new_config.hotkey)
        self._had_error = False
        self._set_title(ICON_IDLE)
        self._error_item.setHidden_(True)
        self._rebuild_pipeline()
```

Extrair a resolução de hotkey que hoje está inline no `__init__` (o bloco `hotkey_str = ...` até o `except AttributeError`) para um método reutilizado pelos dois caminhos:

```python
    def _resolve_hotkey(self, name: str):
        try:
            return getattr(keyboard.Key, name.lower())
        except AttributeError:
            return keyboard.KeyCode.from_char(name)
```

e no `__init__` usar `self._hotkey = self._resolve_hotkey(config.hotkey)`.

- [ ] **Step 2: F8 sem pipeline vira erro visível**

Em `_handle_recording`, logo depois de `audio_path = self._recorder.stop()`, o `self._pipeline.run(audio_path)` falharia com `AttributeError` se pipeline for `None`. Trocar as duas linhas:

```python
            audio_path = self._recorder.stop()
            self._had_error = False
            self._pipeline.run(audio_path)
```

por:

```python
            audio_path = self._recorder.stop()
            self._had_error = False
            if self._pipeline is None:
                raise TranscriptionError(
                    self._config.provider,
                    "API key ausente. Configure em Configurações…",
                )
            self._pipeline.run(audio_path)
```

- [ ] **Step 3: Item de menu "Configurações…"**

Em `MainThreadDispatcher`, adicionar (depois de `openLog_`):

```python
    def openSettings_(self, sender):
        self._app._settings.show()
```

Em `_setup_menu`, ANTES do item "Abrir log", adicionar:

```python
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Configurações…", "openSettings:", ","
        )
        settings_item.setTarget_(self._dispatcher)
        menu.addItem_(settings_item)
```

- [ ] **Step 4: `main()` usa config novo + migração**

Substituir a última linha de `main()`:

```python
    VozMenuBar(Config.from_env()).run()
```
por:
```python
    migrate_env_key_if_needed()
    VozMenuBar(Config.load()).run()
```

- [ ] **Step 5: Remover o config antigo**

```bash
git rm src/config.py tests/test_config.py
```
Verificar que nada mais importa `src.config`: `grep -rn "src.config\b" src tests` → sem resultados (fora `src.core.config`).

- [ ] **Step 6: Docs**

`.env.example`: adicionar as linhas comentadas abaixo das existentes:

```
# Dev overrides (opcional — a config oficial fica em Configurações…/Keychain)
# PROVIDER=groq|openai|local
# OPENAI_API_KEY=
```

`README.md` e `README.pt-BR.md`: na seção de configuração, adicionar um parágrafo antes da tabela dizendo que a partir de agora a configuração oficial é pelo menu **🎙️ > Configurações…** (provider Groq/OpenAI/Local, modelo, hotkey), com a API key guardada no **Keychain do macOS**; o `.env` vira override de desenvolvimento. Na tabela, adicionar as linhas `PROVIDER` (default `groq`) e `OPENAI_API_KEY` (override de dev). Nos Features, adicionar bullet: EN "**Pluggable providers** — Groq, OpenAI or local faster-whisper, switchable in the native Settings window (API keys in the macOS Keychain)" / PT-BR "**Providers plugáveis** — Groq, OpenAI ou faster-whisper local, trocáveis na janela nativa de Configurações (API keys no Keychain do macOS)". Remover o bullet do Roadmap sobre "Providers + Settings" (entregue).

`docs/STATUS.md`: registrar o M2 (tasks, commits, contagem de testes, próxima task = Milestone 3 empacotamento .app).

- [ ] **Step 7: Suíte + fumaça completa**

1. `pytest` → tudo verde; cobertura 100% nos módulos core novos.
2. `ruff check src tests` → limpo.
3. Fumaça app: matar instância anterior (`pkill -f "src.app"`), `nohup .venv/bin/python -u -m src.app > /tmp/sagmowhisper.log 2>&1 &`; conferir: ícone 🎙️ na barra; menu tem "Configurações…" (⌘,), "Abrir log", "Sair"; "Configurações…" abre a janela; salvar mostra "✓ Salvo e aplicado" e `cat ~/Library/Application\ Support/SagmoWhisper/config.json` reflete a escolha SEM api key dentro.
4. Registrar evidências no report (PID, saída dos comandos).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: menu Configurações… aplica providers/hotkey na hora; config novo"
```

---

## Self-review (feito na escrita)

- **Cobertura do spec:** contrato+erro tipado (T1), keyring (T2), config JSON+migração silenciosa (T3), migração Groq (T4), OpenAI (T5), local opcional lazy (T6), popup filtrado/testar conexão via catálogo+factory (T7/T8), janela com 5 campos + salvar-aplica-na-hora + testar conexão (T8), menu + aplicar sem reiniciar + F8 sem key vira erro visível (T9). Campo "language" fica só em JSON/env (o spec lista 5 campos na janela; idioma não está entre eles).
- **Sem placeholders:** todo step de código tem o código completo; o único "copiar e ajustar" (T5 Step 2) enumera exatamente o que muda.
- **Consistência de tipos:** assinaturas de `GroqTranscriber`/`OpenAITranscriber(client, model, language)`, `test_connection(api_key, client_factory=...)`, `build_components(config) -> (transcriber, cleaner|None)` e `initWithConfig_onSave_` conferidas entre T4-T9.
- **Pipeline intocado:** `enable_cleanup = cleaner is not None` preserva `src/pipeline.py` (migra no M3).
