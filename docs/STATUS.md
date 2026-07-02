# STATUS — Voz

> Última atualização: 2026-07-02

## Estado atual: Milestone 2 (Providers + Settings + Keyring) — entregue — branch `feature/m2-providers-settings`

Ditado por voz global no Mac. Segura F8 -> grava -> Groq Whisper transcreve ->
(opcional) Groq Llama limpa -> cola no cursor de qualquer app via clipboard + Cmd+V.

Milestone 1 (Fundação) concluído em `feature/voz-mvp-ditado`, branch `main` criado
apontando para o mesmo HEAD (`1e5ff11`):

1. `bbf9875` — `audio_level` com escala dB (corrige sensibilidade do waveform).
2. `307c2ba` — overlay usa escala dB, amplitude de voz normal visível.
3. `b3bddb1` — erros de ditado vão para `~/Library/Logs/SagmoWhisper.log`.
4. `72906f6` — fecha só o handler do logger em vez de `logging.shutdown()` global.
5. `d07a5fc` — erro de ditado vira ⚠️ na barra com "Último erro" e "Abrir log".
6. `1e5ff11` — trava de instância única, impede ícones duplicados na barra.
7. `docs: checkpoint do milestone 1 (fundação) em main` — este commit.

Verificado em 2026-07-02:
- `python -m src.app` sobe sem erro e permanece rodando.
- Permissões macOS concedidas ao host do terminal: Accessibility ✓, Input Monitoring ✓, Microfone ✓ (device: C270 HD WEBCAM).
- `.env` com GROQ_API_KEY válida; `VOZ_ENABLE_CLEANUP` desligado.
- `rumps` removido (migração para AppKit puro concluída e commitada).

Overlay "Orbe + Barras" (mockup D) entregue em `feature/orb-overlay` (3 tasks):

1. `69838f4` — `src/core/orb_animation.py`: matemática pura da animação (escala,
   brilho, progresso do anel, ângulo de rotação) — 100% TDD.
2. `2a29835` — `src/macos/orb_overlay.py`: classe `OrbOverlay` (AppKit puro),
   estados listening/transcribing/error, 30fps via `NSTimer` — fumaça manual.
3. Este commit — `src/app.py` troca `WaveformOverlay` por `OrbOverlay`; erro do
   pipeline também aparece na orbe (`show_error`); `src/waveform_overlay.py`
   deletado.

Fumaça real feita nesta task: instância antiga derrubada (`pkill -f src.app`),
nova instância subida com `.venv/bin/python -u -m src.app`, processo único
confirmado via `pgrep`, sem erros em `/tmp/sagmowhisper.log` nem em
`~/Library/Logs/SagmoWhisper.log`. Teste de ditado por voz (F8 real) fica para
o humano — instância deixada rodando ao final desta task.

---

## Milestone 2 (Providers + Settings + Keyring) — CONCLUÍDO

Arquitetura providers + settings nativa do macOS + Keychain (tasks 1-9):

1. `a588ee8` — Contratos de provider (TranscriptionError, protocolos tipados).
2. `b004fbf` — Suporte Keychain (secrets.py: set_api_key, get_api_key).
3. `cce91cb` — Config novo (JSON persistente, override .env, migrate_env_key_if_needed).
4. `ac6b63d` — Provider Groq (Groq client factory, GroqTranscriber/GroqCleaner).
5. `09e5ac7` — Provider OpenAI (OpenAI client factory, OpenAITranscriber/OpenAICleaner).
6. `b74bf29` — Provider Local (lazy-load faster-whisper, LocalTranscriber).
7. `3461f81` — Factory (build_components, test_connection, resolve_api_key).
8. `5e97208` — Settings window (nativa AppKit: provider, modelo, API key, hotkey, teste conexão).
9. `5f1d1f2` — Menu "Configurações…" + aplicar na hora (config novo, ⚠️ sem API key).

Verificado em 2026-07-02:
- Testes: **83/83 green** (task 9: removidos 5 testes obsoletos de src/config.py antigo).
- `ruff check`: sem erros (CC <= 4, LEI 8).
- Fumaça interativa NÃO executada (exige cliques reais) — PENDENTE DE HUMANO antes do ship:
  abrir "Configurações…", trocar provider (key some no Local), "Testar conexão" (✓/✗),
  "Salvar" → "✓ Salvo e aplicado" + `cat ~/Library/Application\ Support/SagmoWhisper/config.json`
  sem nenhuma key (confirmação runtime da LEI 9), hotkey aplicada sem reiniciar, Ctrl+C sem traceback.
- Import clean: `python -c "from src.app import VozMenuBar; print('ok')"` ✓

## Trabalho não commitado

Nenhum. Working tree limpo (fora de `.superpowers/`, artefato do processo SDD).

## Testes (Milestone 2)

- `pytest`: **83 passed** (2.3s).
- `ruff check src tests`: **All checks passed** (CC <= 4, LEI 8).
- Cobertura: 100% em todos os módulos `src/core/*` (providers, config, secrets).
  Exemplos: `src/core/providers/base.py`, `src/core/providers/groq_provider.py`,
  `src/core/providers/openai_provider.py`, `src/core/providers/local_provider.py`,
  `src/core/providers/factory.py`, `src/core/config.py`, `src/core/secrets.py`.
  Adapters de I/O (`audio_recorder`, `text_injector`, `app`, `macos/orb_overlay`,
  `macos/settings_window`) validados por fumaça manual (AppKit/hardware/SO).

## Arquivos-chave (Milestone 2)

| Arquivo | Responsabilidade | Testado |
|---------|------------------|---------|
| `src/core/config.py` | Config JSON persistente + override .env | sim (TDD, 100%) |
| `src/core/secrets.py` | Keychain macOS (set/get API keys) | sim (TDD, 100%) |
| `src/core/providers/base.py` | TranscriptionError, protocolos, PROVIDER_CATALOG | sim (TDD, 100%) |
| `src/core/providers/groq_provider.py` | Groq client + GroqTranscriber/GroqCleaner | sim (TDD, 100%) |
| `src/core/providers/openai_provider.py` | OpenAI client + OpenAITranscriber/OpenAICleaner | sim (TDD, 100%) |
| `src/core/providers/local_provider.py` | LocalTranscriber (faster-whisper lazy) | sim (TDD, 100%) |
| `src/core/providers/factory.py` | build_components, test_connection, resolve_api_key | sim (TDD, 100%) |
| `src/macos/settings_window.py` | Janela AppKit nativa: provider, modelo, API key, hotkey | fumaça manual |
| `src/app.py` | Menu + _rebuild_pipeline + _apply_config (hot reload) | fumaça manual |
| `src/pipeline.py` | Orquestra transcrição -> limpeza -> injeção | sim (TDD) |
| `src/audio_recorder.py` | sounddevice -> .wav + RMS callback | parcial |
| `src/text_injector.py` | clipboard + Cmd+V | fumaça manual |
| `src/macos/orb_overlay.py` | Overlay AppKit "Orbe + Barras" | fumaça manual |

## Como rodar (dev)

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz
source .venv/bin/activate
pytest                  # suíte
ruff check src tests    # qualidade/complexidade
```

## Como usar

```bash
source .venv/bin/activate
python -m src.app       # segura F8 para ditar
```

## Próxima task

Milestone 2 merged em `main` via PR. Próximo:

**Milestone 3 (Empacotamento .app)** — requisito Raul (2026-07-02):
Transformar em app nativo do macOS (bundle `.app`, py2app ou briefcase) para:
- Não depender de rodar Python no terminal
- Não aparecer "Python" no Dock
- Iniciar no login via LaunchAgent + `LSUIElement`
- (O app já usa `ActivationPolicyAccessory`; o bundle com `LSUIElement` fecha o restante)

Tarefas do M3:
1. Configurar py2app ou briefcase para gerar `.app` standalone.
2. Criar LaunchAgent em `~/Library/LaunchAgents/com.raulsantanas.sagmowhisper.plist`.
3. Packaging: versão, ícone, Info.plist com `LSUIElement=true`.
4. Testar: `.app` sobe, menu aparece sem Python no Dock, reinicia no login.
5. CI/CD opcional: release binários no GitHub.

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
