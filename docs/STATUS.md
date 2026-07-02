# STATUS — Voz

> Última atualização: 2026-07-02

## Estado atual: Milestone 1 (Fundação) entregue — branch `main` criado

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

## Trabalho não commitado

Nenhum. Working tree limpo (fora de `.superpowers/`, artefato do processo SDD).

## Testes

- `pytest`: **32 passed** (0.41s).
- `ruff check .`: **All checks passed** (CC <= 4, LEI 8).
- Cobertura: 100% em `src/core/audio_level.py`, `src/core/app_logging.py`,
  `src/core/single_instance.py`, `src/cleaner.py`, `src/config.py`, `src/pipeline.py`,
  `src/transcriber.py`. Adapters de I/O (`audio_recorder` parcial, `text_injector`,
  `app`, `waveform_overlay`) sem teste automático por decisão de design — validados
  por fumaça manual (I/O de hardware/SO).

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
| `src/audio_recorder.py` | sounddevice -> .wav + RMS callback | parcial (callback) |
| `src/text_injector.py` | clipboard + Cmd+V | fumaça manual |
| `src/waveform_overlay.py` | Overlay AppKit com barras em tempo real | fumaça manual |
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

Milestone 2 (Providers + Settings + Keyring):
1. Arquitetura: contratos de provider (Groq/OpenAI/fallback) e policy de seleção.
2. Janela de settings (escolha de provider, chaves de API).
3. Armazenamento seguro de credenciais via keyring do macOS (nunca em texto plano).
4. TDD: RED antes de qualquer implementação de provider/settings.
5. Avaliar rodar em background (nohup ou LaunchAgent) — carry-over do milestone 1.

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
