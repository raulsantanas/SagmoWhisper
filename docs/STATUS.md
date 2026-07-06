# STATUS — Voz

> Última atualização: 2026-07-06

## Estado atual: Editor de Ditado concluído — 3 PRs empilhados aguardando revisão do Raul

**Task concluída (2026-07-06):** feature "Editor de Ditado" substitui a etapa
de limpeza da transcrição por um prompt de reescrita em dois registros
(mensagem transcrita literal vs. texto reescrito para o LLM), rodando no
modelo Groq `openai/gpt-oss-120b`, sem o guard determinístico anterior
(`cleanup_reuses_dictated_words` removido — decisão da spec), com log
antes/depois do pipeline e fallback para o texto cru em caso de erro. Entregue
em 3 PRs empilhados (tasks 1-5):

- **PR #18** `feat/modelo-gpt-oss` ← `main` — catálogo/modelo/migração automática
  de config (Llamas descontinuados → `openai/gpt-oss-120b` default).
- **PR #19** `feat/editor-de-ditado` ← `feat/modelo-gpt-oss` — prompt de dois
  registros, pipeline sem guard (log + fallback), remoção do guard antigo.
- **PR #20** `feat/fumaca-live-editor` ← `feat/editor-de-ditado` — fumaça
  live opt-in contra a API real da Groq + este checkpoint.
- Ordem de merge obrigatória: **modelo → editor → fumaça** (#18 → #19 → #20).
  Quem mergeia é o Raul — nenhum agente faz merge.

**Fumaça live (opt-in, `pytest -m groq_live --no-cov`):** passou **5/5 duas
vezes** contra `openai/gpt-oss-120b` real, 0 calibrações de prompt necessárias.
1 fix pós-review (commit `e3f1642`): os ditados usados nos testes live foram
trocados por entradas inéditas (para não duplicarem os few-shots já presentes
no prompt) + guarda contra vazamento de `<think>` (reasoning do modelo) na
saída.

⚠️ **Débito conhecido (catálogo):** `PROVIDER_CATALOG["groq"].cleanup_models`
lista `openai/gpt-oss-20b` como opção secundária, mas esse modelo segue
**BLOQUEADO no projeto Groq** (`403 model_permission_blocked_project`) —
selecioná-lo nas Configurações quebraria a limpeza até ser habilitado em
console.groq.com/settings/project/limits. Modelos habilitados hoje no
projeto: `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`,
`openai/gpt-oss-120b`, `whisper-large-v3`, `whisper-large-v3-turbo`.

- Arquivos-chave: `src/core/providers/base.py` (dois registros do prompt,
  `cleanup_messages`), `src/pipeline.py` (log antes/depois + fallback sem
  guard), `src/core/config.py` (migração automática de modelo),
  `tests/core/providers/test_cleanup_live.py` (fumaça live opt-in).
- Testes: **142 passed, 3 skipped, 5 deselected** (live é opt-in, marker
  `groq_live`, requer `GROQ_API_KEY` do Keychain) · `ruff check .` limpo
  (CC ≤ 4, LEI 8).
- Próxima task (HUMANO — Raul): revisar e mergear os 3 PRs **em ordem**
  (modelo → editor → fumaça); depois reinstalar o `.app` (`! ./install.sh`,
  só o Raul roda) + dança TCC (`tccutil reset Accessibility|ListenEvent
  com.raulsantana.sagmowhisper` + readicionar permissões) para os fixes
  chegarem ao app instalado — acumula os fixes dos PRs #12, #15, #17 e #20.
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: PR #15 mergeado (`80a31f7`) — falta reinstalar o .app

**Task concluída (2026-07-06):** app instalado não abria ao clicar. Causa raiz:
`app.lock` órfão em `~/Library/Application Support/SagmoWhisper/` com PID 623
reciclado pelo macOS para `diagnosticspushd`; `acquire_lock` só checava PID vivo
e levantava `AlreadyRunningError` para sempre. Mitigação imediata: lock removido
manualmente, app voltou a abrir. Fix definitivo: lock só vale se o PID vivo for
processo SagmoWhisper (`ps -p <pid> -o command=`).

- Arquivos: `src/core/single_instance.py`, `tests/core/test_single_instance.py`
- Testes: 135 passed, 3 skipped (suíte completa) · ruff limpo
- PR #15 mergeado em 2026-07-06 (CI 4/4 verde, merge `80a31f7`).
- Próxima task (HUMANO): reinstalar o .app para o fix valer no app instalado —
  `! ./install.sh` + dança TCC (`tccutil reset` + readicionar permissões).
- Próxima task (código): corrigir `UnicodeEncodeError` no handler de log do
  bundle py2app (mensagens com acento quebram o logging — visto ao logar
  "já está rodando" com encoding ascii)
- Retomar: `cd ~/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Milestone 4 (CLI Linux) — implementado, beta — branch `feature/m4-linux-cli`

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
- [x] Ícone 🎙️ na barra (menus usados na fumaça real; sem Dock por LSUIElement)
- [x] Acessibilidade + Monitoramento de Entrada concedidas ao SagmoWhisper
- [x] Prompt de Microfone na 1ª gravação — aceito
- [x] Checkbox "Abrir no login" habilitado + marcado (toggle desmarcar/remarcar não exercitado)
- [x] **Ditado F8 real pelo bundle — FUNCIONANDO** (frase falada → texto colado no cursor)
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

## Fechamento (2026-07-02): PRs #5, #6 e #7 mergeados — M3 CONCLUÍDO

- PR #5 (feature/m3-app-bundle): milestone completo, CI verde na 1ª execução.
- PR #7 (fix/py2app-pynput-backend): fix do launch (pynput/keyring em `packages`),
  revisado e mergeado — o app instalado e a main agora têm o mesmo código.
- PR #6 (chore/docs-guia-usuario): READMEs user-first + `docs/superpowers/`
  removido do repo público (gitignorado; specs/planos seguem locais e no histórico).
- Zero PRs abertos; branches remotos deletados; CI verde nos dois últimos PRs
  (test + build do .app no runner).

## Fumaça humana (2026-07-02, tarde): ditado F8 FUNCIONANDO 🎙️

Permissões concedidas (Acessibilidade + Monitoramento de Entrada; Microfone
aceito no prompt da 1ª gravação), app reiniciado após cada permissão, e o
teste real passou: segurar F8 → falar → soltar → texto colado no cursor, tudo
pelo bundle instalado, sem terminal. Botões "Salvar" e "Testar conexão" das
Configurações também verificados (✓ Conexão OK / ✓ Salvo e aplicado, chamada
HTTPS real ao Groq com a key do Keychain). PR #9 documenta o passo a passo
das permissões nos READMEs, com as pegadinhas reais (duas telas
"Acessibilidade"; Microfone só via prompt; reinício obrigatório).

## Pós-ícone (2026-07-02, ~20h): TCC invalidado pela reinstalação — diagnosticado e resolvido

A reinstalação do PR #10 (ícone) reassinou o app e o macOS parou de honrar as
permissões antigas em silêncio: F8 sem nenhum rastro no log. Diagnóstico via
TCC.db: o `csreq` guardado apontava para o cdhash da assinatura anterior, e
**desligar/ligar a chavinha NÃO atualiza o csreq** — só remover e readicionar
o app (ou `tccutil reset <serviço> com.raulsantana.sagmowhisper`). Feito isso
e reaberto o app, **ditado F8 voltou a funcionar** (confirmado pelo Raul).
Gotcha documentado nos READMEs e no output final do install.sh.

## Bugfix (2026-07-02, ~20h): limpeza respondia perguntas ditadas

Uso real revelou: ditar uma pergunta fazia o app colar uma RESPOSTA, não a
transcrição — o modelo de limpeza (llama-3.1-8b-instant) tratava o texto como
pergunta dirigida a ele, apesar da proibição no system prompt. Fix (TDD, RED
primeiro), em duas camadas: (1) regra explícita nova no prompt + few-shot em
`CLEANUP_EXAMPLES` via `cleanup_messages()` compartilhada em `base.py`, usada
pelos cleaners Groq e OpenAI (DRY); (2) guard determinístico
`cleanup_reuses_dictated_words()` — resposta gerada sempre introduz palavra
nova; se introduzir, o pipeline descarta a limpeza e cola a transcrição crua
(fallback inofensivo). Validado contra a API real da Groq: 8/8 casos sem
resposta vazada (2 caíram no fallback). Suíte: 97 passed.
⚠️ O fix só chega ao app instalado após reinstalar (`./install.sh`) — e
reinstalar exige remover/readicionar as permissões TCC (ver READMEs).

---

## Milestone 4 (CLI Linux) — CONCLUÍDO (beta)

Port do core para Ubuntu como app de linha de comando, mantendo o macOS
nativo intacto (tasks 1-13):

1. `6ec78c8` — refactor: extrai `resolve_hotkey` para módulo compartilhado Mac/Linux.
2. `bbf9547` — feat: `TextInjector` escolhe Cmd+V (macOS) / Ctrl+V (Linux) pela plataforma.
3. `3906325` — feat: config segue XDG no Linux (`~/.config/sagmowhisper/config.json`); docstring do cofre multiplataforma.
4. `0cf2fb6` — build: pacote pip instalável com script `sagmowhisper` e marker `pyobjc` (só instala no macOS).
5. `a22d205` — feat: checagem de sessão Linux (Wayland, `DISPLAY`, `xclip`) com mensagens claras de erro.
6. `a4fee64` — feat: "abrir no login" via unit systemd de usuário no Linux (`sagmowhisper login on/off/status`).
7. `74194cb` — feat: assistente `sagmowhisper setup` no terminal (provider, API key, opções).
8. `9665738` — feat: loop push-to-talk F8 do Linux com feedback impresso no terminal.
9. `eda3662` — feat: comando `sagmowhisper` (subcomandos `setup`, `run`, `login`) para Linux.
10. `03918d1` — test: integração X11 real (clipboard + Ctrl+V) para o CI Linux.
11. `1162e49` — feat: `install-linux.sh` (instala deps do sistema + o app) para Ubuntu.
12. `323a6ea` — ci: suíte completa em Ubuntu sob Xvfb + fumaça do instalador Linux.
13. Este commit — READMEs (EN/pt-BR) anunciam o Linux (Ubuntu) beta + checkpoint.

Verificado em 2026-07-02 (pós-merge do PR #13):
- **PR #13 mergeado na main** (`8f116cb..6013959`), branch deletado, revisão final registrada como comentário no PR.
- `pytest`: **134 passed, 3 skipped** (skips = integração X11, exercitados no job `test-linux`; +1 teste de branch em `on_release` adicionado nos fixes pré-merge).
- `ruff check src tests`: sem erros (CC <= 4, LEI 8).
- CI verde nos 4 jobs do PR #13: test (macOS), build (.app py2app), test-linux (Ubuntu + Xvfb), install-linux (fumaça do install-linux.sh). O job build falhou na 1ª rodada — setuptools >= 82 removeu `install_requires` e o `[project].dependencies` quebrava o py2app; causa raiz confirmada por reprodução local, fix em `f03e483` (deps de runtime só no requirements.txt), re-rodada 4/4 verde.
- Pendente: fumaça humana do Raul num Ubuntu real (F8 → grava → transcreve → cola) para remover o selo Beta dos READMEs.

Débitos aceitos na revisão final (não bloqueantes):
- Type hint de retorno ausente em `resolve_hotkey`.
- `UNIT_PATH` do `login_service` (Linux) resolvido em import-time, não lazy.
- Teste de Ctrl+V (`test_emitir_ctrl_v_no_display_virtual_nao_falha`) só verifica ausência de exceção — limitação do Xvfb, não valida o conteúdo colado.
- Echos do `install-linux.sh` usam unicode (emojis/acentos) sem normalização para terminais que não suportam.
- Assimetria de nome: `login_item.py` (macOS) vs `login_service.py` (Linux) — mesmo papel, nomes diferentes.
- `src/macos` é empacotado mesmo quando o instalador Linux não o utiliza.

## Trabalho não commitado

Nenhum. Working tree limpo (fora de `.superpowers/`, artefato do processo SDD).

## Testes (Milestone 4)

- `pytest`: **134 passed, 3 skipped**.
- `ruff check src tests`: **All checks passed** (CC <= 4, LEI 8).
- Cobertura: core Linux (`src/linux/*`) coberto por TDD; integração X11 real (clipboard/Ctrl+V)
  passou no job `test-linux` do PR #13 (Ubuntu + Xvfb); ditado F8 fim a fim com microfone real
  ainda não passou por fumaça humana em hardware físico.

## Arquivos-chave (Milestone 4)

| Arquivo | Responsabilidade | Testado |
|---------|------------------|---------|
| `src/linux/cli.py` | Entry point `sagmowhisper` (setup/run/login) | sim (TDD) |
| `src/linux/session_check.py` | Detecta Wayland/DISPLAY/xclip ausente | sim (TDD) |
| `src/linux/login_service.py` | Unit systemd de usuário ("abrir no login") | sim (TDD) |
| `src/linux/setup_wizard.py` | Assistente interativo de configuração | sim (TDD) |
| `src/text_injector.py` | Cmd+V (macOS) / Ctrl+V (Linux) por plataforma | sim (TDD) + integração X11 real |
| `install-linux.sh` | Instala deps do sistema + o app no Ubuntu | fumaça CI (`install-linux` job) |
| `.github/workflows/ci.yml` | Jobs `test-linux` (Xvfb) e `install-linux` | CI verde (PR #13) |

## Próxima task

- [x] Merge do PR do M4 (`feature/m4-linux-cli` -> `main`), CI verde nos 4 jobs (test, build, test-linux, install-linux) — feito em 2026-07-02
- [ ] Fumaça humana do Raul num Ubuntu real: `./install-linux.sh` -> `sagmowhisper setup` -> `sagmowhisper run` -> F8 com microfone real -> remover selo Beta dos READMEs (HUMANO)
- [ ] Itens pendentes do M3 (baixa prioridade): reiniciar o Mac para confirmar RunAtLoad; exercitar toggle "Abrir no login"

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
