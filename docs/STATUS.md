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

## Trabalho não commitado

Nenhum. Working tree limpo (fora de `.superpowers/`, artefato do processo SDD).

## Testes

- `pytest`: **45 passed** (0.42s).
- `ruff check src tests`: **All checks passed** (CC <= 4, LEI 8).
- Cobertura: 100% em `src/core/audio_level.py`, `src/core/app_logging.py`,
  `src/core/single_instance.py`, `src/core/orb_animation.py`, `src/cleaner.py`,
  `src/config.py`, `src/pipeline.py`, `src/transcriber.py`. Adapters de I/O
  (`audio_recorder` parcial, `text_injector`, `app`, `macos/orb_overlay`) sem
  teste automático por decisão de design — validados por fumaça manual (I/O de
  hardware/SO/AppKit).

## Arquivos-chave

| Arquivo | Responsabilidade | Testado |
|---------|------------------|---------|
| `src/config.py` | Config dataclass + from_env() | sim (TDD) |
| `src/transcriber.py` | Groq Whisper -> texto | sim (TDD) |
| `src/cleaner.py` | Groq Llama limpa transcrição PT-BR | sim (TDD) |
| `src/pipeline.py` | Orquestra transcrição -> limpeza -> injeção | sim (TDD) |
| `src/core/audio_level.py` | Escala dB de nível de áudio | sim (TDD, 100% cobertura) |
| `src/core/app_logging.py` | Log estruturado em `~/Library/Logs/SagmoWhisper.log` | sim (TDD, 100% cobertura) |
| `src/core/single_instance.py` | Trava de instância única | sim (TDD, 100% cobertura) |
| `src/core/orb_animation.py` | Matemática pura da animação da orbe | sim (TDD, 100% cobertura) |
| `src/audio_recorder.py` | sounddevice -> .wav + RMS callback | parcial (callback) |
| `src/text_injector.py` | clipboard + Cmd+V | fumaça manual |
| `src/macos/orb_overlay.py` | Overlay AppKit "Orbe + Barras" (listening/transcribing/error) | fumaça manual |
| `src/app.py` | NSStatusBar + listener F8 (glue) | fumaça manual |

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

Orb overlay merged em `main` via PR #1; fix do monitor principal via PR #2
(orbe agora abre em `NSScreen.screens()[0]`, não na tela com foco). Próximo:

Milestone 2 (Providers + Settings + Keyring):
1. Arquitetura: contratos de provider (Groq/OpenAI/fallback) e policy de seleção.
2. Janela de settings nativa do macOS (escolha de provider, chaves de API) —
   pedido explícito do Raul: menu nativo do Mac.
3. Armazenamento seguro de credenciais via keyring do macOS (nunca em texto plano).
4. TDD: RED antes de qualquer implementação de provider/settings.
5. Avaliar rodar em background (nohup ou LaunchAgent) — carry-over do milestone 1.

Milestone 3 (empacotamento) — requisito novo do Raul (2026-07-02):
virar app nativo do macOS (bundle `.app`, ex.: py2app/briefcase) para não
depender de rodar Python no terminal nem aparecer "Python" no Dock; iniciar
no login via LaunchAgent. O app já usa ActivationPolicyAccessory; o bundle
com `LSUIElement` fecha o restante.

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
