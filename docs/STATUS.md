# STATUS — Voz

> Última atualização: 2026-07-10

## Estado atual: Meta-Declaração com Estrutura — Few-Shot Corrigido — RED→GREEN testado

**Task concluída (2026-07-10):** ditados com meta-declaração ("esse é um prompt então faça o rebuild completo dos ajustes de privacidade porque já fiz aqui para subir a última pr", log 03:35:18) saíam em linha corrida, sem estrutura de prompt (sem tags XML). O gate `prompt_register_triggered()` FUNCIONA (verificado: True para os casos reais) — o problema era o modelo seguindo o exemplo do few-shot em vez da instrução.

### Análise: Causa raiz do few-shot contradizia a regra

O único few-shot de meta-declaração em `CLEANUP_EXAMPLES_PROMPT` (exemplo do CSV) tinha:
- **Entrada:** 3 tarefas enumeradas (imperativo complexo)
- **Saída:** linha corrida, sem tags XML

Isso contradiz a regra "2+ informações → SEMPRE tags XML" explicitada na #29. O modelo (llama-3.3-70b, temp 0) segue o exemplo, não a instrução verbal.

**Fix:** saída do exemplo do CSV reescrita em `src/core/providers/base.py` para demonstrar a regra:
- Objetivo imperativo na 1ª linha
- `<tarefas>` em bullets (não linha corrida)
- Demonstração estruturada da paráfrase semântica (conteúdo levemente reformulado, mas intenção preservada)

Nada mais mudou no código. Temperatura já estava 0 (PR #29); gate já estava robusto (PR #29); só faltava o exemplo contradizer menos a regra.

### Testes (TDD, RED verificado)

**Novo teste direto:**
- `test_exemplo_de_meta_declaracao_demonstra_tags_xml` em `tests/core/providers/test_base.py` (falhou antes do fix com exemplo antigo, passou pós-correção)

**Novo teste live contra Groq real:**
- `test_meta_declaracao_com_tarefa_e_porque_ganha_estrutura` em `tests/test_cleanup_live.py` com o ditado real do log (falhou antes; passou depois)

**Suíte completa:**
- `pytest`: **230 passed, 3 skipped, 11 deselected**
- `pytest -m groq_live --no-cov`: **11/11** na primeira tentativa
- `ruff check src tests`: limpo (CC ≤ 4)

**Reprodução manual:** o ditado real agora sai com `<contexto>` e `<tarefas>`, estruturado.

### Ressalva honesta: paráfrase semântica não-literal

A saída estruturada parafraseia levemente o porquê original ("para subir a última pr" → "Considere as últimas alterações") — fidelidade literal do conteúdo segue como observação de acompanhamento, não bloqueia nem invalida a correção (o imperativo e as tarefas saem claros).

- Arquivo: `src/core/providers/base.py` (exemplo `CLEANUP_EXAMPLES_PROMPT` reescrito)
- Testes: **230 passed, 3 skipped, 11 deselected** (RED verificado com 1 novo teste que falhava antes); live Groq **11/11**
- Ruff: limpo (CC ≤ 4)
- **PR desta branch** (número ainda não definido): será aberta a partir de `fix/few-shot-meta-declaracao-estrutura` (rebased na main `f265fe5`)
- ⚠️ **O .app instalado hoje (2026-07-10) NÃO tem este fix** — rebuild obrigatório via `./install.sh` após merge (será preciso re-conceder TCC Acessibilidade + Monitoramento de Entrada novamente)
- **Próximo passo (coordenador):** PR → CI → merge → `./install.sh` + TCC re-concedido
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Gatilho de Registro PROMPT Explícito + Temperatura 0 — RED→GREEN testado

**Task concluída (2026-07-10):** dois bugs corrigidos em sessão de revisão/refinamento do fix anterior (branch `fix/gatilho-explicito-estrutura-sempre`, rebased na main `b73ef31`):

### Bug 1: Saída sem estrutura (parágrafos/bullets) dependendo do conteúdo
**Causa raiz:** `temperature=0.2` no `GroqCleaner` causava variância de estrutura; registro PROMPT com system prompt longo permitia saída "curta sem tags" como alternativa válida.
**Fix:** `temperature=0` em `src/core/providers/groq_provider.py` (temperatura determinística). Registro PROMPT com estrutura Anthropic **SEMPRE** que houver 2+ informações: tags XML `<contexto>/<tarefas>/<restricoes>` em vez de parágrafo corrido; few-shots reancorados com exemplos de múltiplos blocos.

### Bug 2: Menção casual à palavra "prompt" gerava prompt aleatório
**Causa raiz:** gate do registro PROMPT era substring (`"prompt" in text.casefold()`) em `src/core/providers/base.py` — qualquer menção casual ligava o registro PROMPT, cujo system prompt transformava o ditado em prompt de LLM (meta-prompt não intencional).
**Fix:** gate substituído por `prompt_register_triggered()` — regex de comando dirigido ao editor (verbo gatilho + "prompt(s)" na mesma oração, com exclusão de sujeito 3ª pessoa ele/ela/eles/elas e negação) OU meta-declaração (ex: "isso é um prompt"). A função está em `src/core/providers/base.py`; suporta plural "prompts" e valida contexto da menção.

- Arquivos: `src/core/providers/base.py` (gate regex, estrutura XML, few-shots), `src/core/providers/groq_provider.py` (temperatura 0)
- Testes: **229 passed, 3 skipped, 10 deselected** (RED verificado com 6 casos falhando antes do fix; todos passam pós-correção)
- Ruff: limpo (CC ≤ 4)
- Fumaça live Groq (`pytest -m groq_live`): **10/10 na primeira tentativa** — enumeração→bullets, menção casual "prompt" não alucina, "melhore o prompt" não vira meta-prompt, prompt composto→tags XML, "prompts" no plural, exclusão eles/elas validada
- **PR desta branch** (número ainda não definido): será aberta a partir de `fix/gatilho-explicito-estrutura-sempre` (rebased em main `b73ef31`)
- ⚠️ **O .app instalado hoje (2026-07-09) NÃO tem estes fixes** — rebuild obrigatório via `./install.sh` após merge (será preciso re-conceder TCC Acessibilidade + Monitoramento de Entrada novamente)
- **Pendências que continuam:** fumaça Ubuntu real; backlog (avisar usuário quando limpeza falha; Wayland; notarização/Releases)
- **Removido do backlog:** "temperatura 0 no cleaner" — entregue nesta branch (commit `cc337b2` + fixes pós-rebase)
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Deadlock PortAudio×CoreAudio CORRIGIDO — RED→GREEN testado

**Task concluída (2026-07-10):** app congelou por ~4h40 (0% CPU) por deadlock nativo
PortAudio×CoreAudio ao parar gravação. **Causa raiz:** toque rápido de F8 → `stop()`
rodando em thread worker (`_handle_recording`) corria em paralelo com start assíncrono
do CoreAudio ainda em andamento, travando a thread Python em `FinishStoppingStream` →
`AudioOutputUnitStop` esperando `HALB_Mutex` enquanto IOThread do CoreAudio esperava
mutex do AudioUnit dentro de `startStopCallback`. Evidência preservada em
`~/Library/Logs/SagmoWhisper-deadlock-sample-2026-07-10.txt`.

**Fix (TDD, RED→GREEN):** `src/audio_recorder.py` — `stop()` agora espera o primeiro
bloco de áudio (novo `threading.Event` `_first_block`, setado em `_on_audio`) antes de
chamar `stream.stop()/close()`, provando que stream está ativo e fechando a janela da
corrida. Novo parâmetro `start_grace_timeout` (default 1.0s) evita espera infinita com
mic mudo ou sem TCC (falla com erro claro, não travada). **Efeito colateral positivo:**
gravações de toque rápido agora contêm ≥1 bloco real (mitiga erro 400 do Groq "Audio
file is too short").

- Arquivos: `src/audio_recorder.py` (correção), `tests/test_audio_recorder_stop_race.py` (novo, 2 testes)
- Testes: **169 passed, 3 skipped, 8 deselected** (antes: 167 passed) — RED verificado (testes falharam antes da correção)
- Ruff: limpo (CC ≤ 4)
- Fumaça live: 5 ciclos start/stop imediatos com PortAudio real, sem travar (~0,2s/ciclo)
- **PR desta branch** (ainda sem número): será aberta a partir de `fix/audio-stop-deadlock` (baseada na main `5d5dbca`, pós-#27)
- ⚠️ **O .app instalado hoje (2026-07-09) NÃO tem este fix** — rebuild obrigatório via `./install.sh` após merge (e será preciso re-conceder TCC novamente)
- Pendências que continuam valendo: re-conceder TCC Acessibilidade + Monitoramento de Entrada (invalidado por reinstalação 09/07); fumaça Ubuntu real
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Registro Determinístico MERGEADO (#26) + modelo Groq bloqueado em nível de organização

**Task concluída (2026-07-09):** interpretação do ditado como PROMPT ou MENSAGEM
tornou-se **determinística** — a decisão de registro é feita em código (`"prompt"
in text.casefold()`) e sistema prompts específicos foram separados por tipo de
registro. Três correções empilhadas no PR #26:

1. **Correção anti-meta-prompt** (2026-07-07, órfã): ditado "melhora esse
   prompt e analisa o código…" gerava saída meta ("Melhore o prompt fornecido…"
   como objetivo) — o modelo tratava a moldura "melhore o prompt" como tarefa.
   Fix: "melhore" listado como comando de moldura no system prompt, regra
   explícita "a saída é NUNCA um prompt para criar ou melhorar outro prompt",
   e few-shot dedicado.

2. **Separação de system prompts** (novo): `cleanup_messages(text)` em
   `src/core/providers/base.py` mantém assinatura igual. O gate interno
   (`"prompt" in text.casefold()`) seleciona o system prompt e few-shots
   específicos (constantes novas: `CLEANUP_SYSTEM_PROMPT_PROMPT` /
   `CLEANUP_SYSTEM_PROMPT_MENSAGEM`). A constante original `CLEANUP_SYSTEM_PROMPT`
   foi removida. Gatilho em código é o único responsável pela categorização (SRP).

3. **Bloqueio Groq no nível da organização**: Groq retorna `403
   model_permission_blocked_org` para todos os chat models exceto
   `llama-3.3-70b-versatile` (bloqueados: `openai/gpt-oss-120b`,
   `llama-3.1-8b-instant`, e alternativas gpt-oss). Default + allowlist foram
   atualizados em `src/core/config.py` para usar apenas o modelo que funciona
   na org. A config migra modelo bloqueado → default no load. Se o Raul
   reabilitar modelos em console.groq.com/settings/limits, é necessário um
   novo PR para ampliar a allowlist no código.

- Arquivos: `src/core/providers/base.py` (system prompts + few-shots por
  registro), `src/core/config.py` (default + allowlist), testes (160 linhas
  novas em `tests/core/providers/test_base.py` + `tests/test_cleanup_live.py`).
- Testes: **167 passed, 3 skipped** · ruff limpo (CC ≤ 4).
- Fumaça live (`pytest -m groq_live --no-cov`): **8/8** (pergunta ditada não
  respondida; mensagem reescrita; enumeração vira bullets; texto curto volta
  idêntico; gatilho "escreva o prompt" removido da saída; menção casual vira
  prompt; "melhore o prompt" não vira meta-prompt; composto ganha tags XML).
- **PR #26 MERGEADO** em 2026-07-09; CI verde antes do merge; main = `9448b78`.
- **Instalação concluída pelo maestro** (2026-07-09): `./install.sh` completou
  com exit 0; rebuild + reinstalação do .app; app novo aberto em
  `/Applications`. Falta só o TCC humano.
- **Próxima task (HUMANO — Raul):** re-conceder permissões macOS (Ajustes do
  Sistema → Privacidade e Segurança → **Acessibilidade** e **Monitoramento de
  Entrada** → adicionar SagmoWhisper com "+"), reabrir o app, e testar:
  (1) "escreva o prompt para…", (2) menção casual a prompt, (3) "melhora esse
  prompt…" (todos devem resultar em prompt com tags XML ou imperativo), mais
  1 mensagem normal (sem tags, sem formatação).
- Pendências técnicas conhecidas: fumaça em Ubuntu real (tirar selo Beta);
  temperatura 0 no cleaner (1 variância residual rara em ~12 runs).
- Débito vivo: allowlist do código inclui só `llama-3.3-70b-versatile`.
  Reabilitar `openai/gpt-oss-20b` ou `llama-3.1-8b-instant` no console Groq
  é opcional e exigiria novo PR.
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Editor v2 MERGEADO (#24) + app reinstalado — faltam só os cliques TCC

**Task concluída (2026-07-07):** o registro PROMPT agora dispara com
**QUALQUER menção à palavra "prompt"** no ditado (comando, meta-declaração ou
menção casual — decisão do Raul), e o prompt gerado segue as **boas práticas
de prompt da Anthropic** (docs oficiais consultadas): objetivo imperativo na
primeira linha, contexto preservado, prompts compostos estruturados com tags
XML `<contexto>/<tarefas>/<restricoes>`, restrições/critérios só se ditados.
O caso negativo antigo (menção casual NÃO disparava) foi removido por decisão
de produto; o few-shot do Bruno deu lugar a um exemplo de menção casual.

- Arquivos: `src/core/providers/base.py` (system prompt + few-shots),
  `tests/core/providers/test_base.py` (5 testes novos, 1 atualizado),
  `tests/test_cleanup_live.py` (2 casos live novos).
- Testes: **153 passed, 3 skipped, 5 deselected** · ruff limpo (CC ≤ 4).
- Fumaça live (`pytest -m groq_live --no-cov`): **7/7 duas vezes** contra
  `openai/gpt-oss-120b` real, 0 calibrações de prompt.
- **PR #24 MERGEADO** em 2026-07-07 com autorização do Raul ("faça toda
  instalação para mim"); CI verde antes do merge; main = `c7f9846`.
- **Instalação executada pelo agente (2026-07-07):** `./install.sh` a partir
  da main (instância antiga encerrada, "Abrir no login" ligado, app aberto —
  rodando de `/Applications`) + `tccutil reset Accessibility|ListenEvent
  com.raulsantana.sagmowhisper` (ambos "Successfully reset").
- **Falta só GUI (HUMANO):** Ajustes do Sistema → Privacidade e Segurança →
  **Acessibilidade** e **Monitoramento de Entrada** → adicionar o
  SagmoWhisper com "+" (as entradas foram resetadas, não precisa remover);
  reabrir o app; microfone pede sozinho na 1ª gravação. Depois testar:
  mensagem longa (pontuada), "escreva o prompt..." e uma menção casual a
  "prompt" (deve virar prompt formatado).
- Contexto de portfólio: **Sagmo Voice é OUTRO projeto** (privado, para
  venda, em `/dev/Sagmo-Voice`, só PRD) — nunca misturar com este repo.
- Pendências humanas herdadas: fumaça em Ubuntu real (tirar selo Beta);
  reboot do Mac para validar RunAtLoad; toggle "Abrir no login".
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Editor de Ditado MERGEADO na main — falta reinstalar o .app

**Task concluída (2026-07-06):** os 4 PRs do Editor de Ditado foram mergeados
na main (autorizado pelo Raul), em ordem: **#17** (log utf-8 +
`errors="backslashreplace"`) → **#18** (modelo `openai/gpt-oss-120b` +
migração de config) → **#21** (prompt de dois registros + pipeline sem guard;
substituiu o #19) → **#20** (fumaça live opt-in + checkpoints). CI da main
**verde** após o último merge; suíte na main: **143 passed, 3 skipped,
5 deselected**, ruff limpo.

- Nota de processo: o **PR #19 foi fechado automaticamente pelo GitHub**
  quando a branch base dele (`feat/modelo-gpt-oss`) foi deletada no merge do
  #18 — PR fechado com base deletada não reabre; o **#21** o substituiu com o
  mesmo conteúdo. Gotcha para próximas pilhas: **retargetear o PR de cima
  para `main` ANTES de deletar a branch base** (foi o que salvou o #20).
- Conflito único no caminho: `docs/STATUS.md` entre o checkpoint do #17 e o
  do editor — resolvido mantendo o do editor como atual (merge `6287ca5`).
- Próxima task (HUMANO — Raul): **reinstalar o `.app`** (`! ./install.sh`,
  só o Raul roda) + dança TCC (`tccutil reset Accessibility|ListenEvent
  com.raulsantana.sagmowhisper` + readicionar permissões) — traz o editor de
  ditado + o log utf-8 para o app instalado. Depois, testar ditando uma
  mensagem longa no WhatsApp (deve sair pontuada) e um "escreva o prompt...".
- Débito vivo: `openai/gpt-oss-20b` consta no catálogo do app mas segue
  bloqueado no projeto Groq (403) — habilitar em
  console.groq.com/settings/project/limits antes de selecioná-lo.
- Pendências humanas herdadas: fumaça em Ubuntu real (tirar selo Beta);
  reboot do Mac para validar RunAtLoad; toggle "Abrir no login".
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: Editor de Ditado concluído — 3 PRs empilhados aguardando revisão do Raul

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
- **Dependência com PR #17** (`fix/log-utf8-encoding`, aberto, base `main`): o
  log de auditoria com acentos (`Limpeza: original -> final`) só funciona no
  bundle py2app depois que o #17 mergear — o `RotatingFileHandler` destas
  branches não tem `encoding="utf-8"`; sem o #17, o bundle descarta em
  silêncio os registros de log acentuados. Recomendado mergear o #17 antes ou
  junto do #19.

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

⚠️ **Débitos da revisão final (triados, documentados e não corrigidos):**
- `tests/test_pipeline.py::test_resposta_do_editor_e_aceita_sem_guard` não foi
  RED verdadeiro (a fixture reusa palavras ditadas); mantido como teste de
  regressão.
- A guarda contra vazamento de reasoning (`<think>`) existe em só 1 dos 5
  testes live — suficiente para vazamento sistêmico, ampliar se flakear.

- Arquivos-chave: `src/core/providers/base.py` (dois registros do prompt,
  `cleanup_messages`), `src/pipeline.py` (log antes/depois + fallback sem
  guard), `src/core/config.py` (migração automática de modelo),
  `tests/test_cleanup_live.py` (fumaça live opt-in).
- Testes: **142 passed, 3 skipped, 5 deselected** (live é opt-in, marker
  `groq_live`, requer `GROQ_API_KEY` do Keychain) · `ruff check .` limpo
  (CC ≤ 4, LEI 8).
- Próxima task (HUMANO — Raul): revisar e mergear os 3 PRs **em ordem**
  (modelo → editor → fumaça); depois reinstalar o `.app` (`! ./install.sh`,
  só o Raul roda) + dança TCC (`tccutil reset Accessibility|ListenEvent
  com.raulsantana.sagmowhisper` + readicionar permissões) para os fixes
  chegarem ao app instalado — acumula os fixes dos PRs #12, #15, #17 e #20.
- Retomar: `cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude`

## Estado anterior: app reinstalado e validado E2E; fix do log UTF-8 em PR

**Task concluída (2026-07-06):** app instalado não abria ao clicar. Causa raiz:
`app.lock` órfão em `~/Library/Application Support/SagmoWhisper/` com PID 623
reciclado pelo macOS para `diagnosticspushd`; `acquire_lock` só checava PID vivo
e levantava `AlreadyRunningError` para sempre. Mitigação imediata: lock removido
manualmente, app voltou a abrir. Fix definitivo: lock só vale se o PID vivo for
processo SagmoWhisper (`ps -p <pid> -o command=`).

- Arquivos: `src/core/single_instance.py`, `tests/core/test_single_instance.py`
- Testes: 135 passed, 3 skipped (suíte completa) · ruff limpo
- PR #15 mergeado em 2026-07-06 (CI 4/4 verde, merge `80a31f7`).
- .app reinstalado em 2026-07-06 com os fixes #12 e #15; TCC refeito pelo Raul
  e ditado validado E2E (F8 sintético via Quartz + `say` → "Teste, teste."
  colado no TextEdit; as 3 permissões exercitadas, log sem erros novos).
- `UnicodeEncodeError` do log corrigido: `RotatingFileHandler` agora com
  `encoding="utf-8"` (teste reproduz o bundle com `LC_ALL=C` + `-X utf8=0`,
  pois o Python de dev liga UTF-8 mode sozinho em locale C — PEP 540).
  O .app instalado só recebe este fix na PRÓXIMA reinstalação (não urgente:
  o bug apenas mutila linhas de log acentuadas).
- Próxima task (HUMANO): reiniciar o Mac → app deve abrir sozinho (RunAtLoad),
  último item da fumaça M3.
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
