# STATUS — Voz

> Última atualização: 2026-07-02

## Estado atual: Milestone 3 (App Bundle) — entregue — branch `feature/m3-app-bundle`

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

---

## Milestone 3 (App Bundle + LaunchAgent) — CONCLUÍDO

Empacotamento nativo macOS com py2app, LaunchAgent para "Abrir no login" e
script install.sh para one-command build + install (tasks 1-6):

1. `ee9b1fd` — Infraestrutura `LoginItem` (TDD 100%, trata plist em ~/Library/LaunchAgents/).
2. `d3a2a23` — Checkbox "Abrir no login" nas Settings (aplica na hora via LoginItem).
3. `ebf5934` — py2app + launcher `SagmoWhisper.py` (`LSUIElement=true`, app sem Dock).
4. `5e08c54` — `install.sh`: build + instala em /Applications + ativa login por padrão.
5. `064ba97` — Fix: PID guard no kill_running (evita kill 0 se lock corrompido).
6. `a47fb34` — CI: testes + lint + build do .app em todo PR e push na main.

Verificado em 2026-07-02:
- `pytest`: **92 passed** (cobertura 100% em `src/core/*`, incluindo `src/core/login_item.py`).
- `ruff check`: sem erros (CC <= 4, LEI 8).
- py2app build: **~34s**, gera `.app` assinado ad-hoc sem erro.
- `install.sh --build-only`: ✓ (não mata nada, só builda).
- `install.sh --uninstall`: ✓ (remove app + plist, preserva settings/Keychain).
- CI workflow criado (`.github/workflows/ci.yml`) mas **NÃO YET EXECUTED** — primeira
  execução será no PR desta milestone.

### Pós-merge (2026-07-02): bug de launch encontrado e corrigido

O gate humano pegou um bug real: o primeiro `./install.sh` completo instalou e
abriu o app, mas o launch quebrava com o diálogo "Launch error" do py2app —
`ImportError: No module named 'pynput.keyboard._darwin'`. Causa: pynput (e
keyring) escolhem backend por import dinâmico em runtime, invisível ao
modulegraph do py2app; o build passava, só o launch real falhava.

Fix em `fix/py2app-pynput-backend` (PR #7): adiciona `pynput` e `keyring` à
lista `packages` do py2app. Verificado com rebuild + reinstalação real:
binário roda sem traceback e o app permanece vivo.

Fumaça — estado real:
- [x] `./install.sh` completo (matou instância dev PID 81214, instalou, abriu)
- [x] `.app` sobe e permanece rodando sem erro (pós-fix; processo confirmado via pgrep)
- [x] LaunchAgent criado em ~/Library/LaunchAgents/ com "Abrir no login" ligado
- [ ] Confirmar visual: ícone 🎙️ na barra, sem Dock, sem "Python" (HUMANO)
- [ ] Conceder Acessibilidade + Monitoramento de Entrada ao SagmoWhisper (HUMANO)
- [ ] Prompt de Microfone na 1ª gravação (HUMANO)
- [ ] Checkbox "Abrir no login" habilitado + marcado; desmarcar/remarcar cria/remove plist (HUMANO)
- [ ] Ditado F8 real pelo bundle (HUMANO)
- [ ] Reiniciar Mac → app abre sozinho (RunAtLoad) (HUMANO)

Novo arquivo-chave: `src/core/login_item.py` (LaunchAgent, TDD 100%).

## Trabalho não commitado

Nenhum. Working tree limpo (fora de `.superpowers/`, artefato do processo SDD).

## Testes (Milestone 3)

- `pytest`: **92 passed** (2.5s).
- `ruff check src tests`: **All checks passed** (CC <= 4, LEI 8).
- Cobertura: 100% em todos os módulos `src/core/*`, incluindo novo `src/core/login_item.py`.
  Adapters de I/O e AppKit (settings, orb, app) validados por build + fumaça manual.

## Arquivos-chave (Milestone 3)

| Arquivo | Responsabilidade | Status |
|---------|------------------|--------|
| `src/core/login_item.py` | LaunchAgent "Abrir no login" | TDD 100% ✓ |
| `SagmoWhisper.py` | Launcher do app (entry point py2app) | validado build ✓ |
| `setup.py` | Configuração py2app + Info.plist | validado build ✓ |
| `install.sh` | Build + instala em /Applications + ativa login | validado build/fumaça ✓ |
| `.github/workflows/ci.yml` | Testes + lint + build em PR/main | criado, não executado |
| `src/macos/settings_window.py` | Checkbox "Abrir no login" + LoginItem | TDD + fumaça |

## Próxima task

Milestone 3 aguardando: (a) revisão final do branch + PR; (b) fumaça humana
pós-instalação — PENDENTE DE HUMANO:
- [ ] `./install.sh` completo (mata instância dev, instala em /Applications, abre)
- [ ] Ícone 🎙️ na barra, NENHUM ícone no Dock, nenhum "Python" visível
- [ ] Conceder Acessibilidade + Monitoramento de Entrada ao SagmoWhisper; prompt de Microfone na 1ª gravação
- [ ] Checkbox "Abrir no login" habilitado e marcado nas Configurações; desmarcar/remarcar cria/remove o plist em ~/Library/LaunchAgents/
- [ ] Ditado F8 real pelo bundle
- [ ] Reiniciar o Mac → app abre sozinho (RunAtLoad)

Após aprovação humana: push + PR para `main`, merge, tag release.

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
