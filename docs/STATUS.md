# STATUS — Voz

> Última atualização: 2026-07-02

## Estado atual: MVP funcional, verificado rodando — trabalho não commitado pendente

Ditado por voz global no Mac. Segura F8 -> grava -> Groq Whisper transcreve ->
(opcional) Groq Llama limpa -> cola no cursor de qualquer app via clipboard + Cmd+V.

Verificado em 2026-07-02:
- `python -m src.app` sobe sem erro e permanece rodando.
- Permissões macOS concedidas ao host do terminal: Accessibility ✓, Input Monitoring ✓, Microfone ✓ (device: C270 HD WEBCAM).
- `.env` com GROQ_API_KEY válida; `VOZ_ENABLE_CLEANUP` desligado.

## Trabalho não commitado (6 arquivos, +157/-27)

Migração de `rumps` para AppKit puro (NSStatusBar + MainThreadDispatcher),
notificação de erro via NSUserNotification, tratamento de SIGINT, fade-out do
overlay refeito sem lambdas com efeito colateral.

Pendências antes do commit:
1. `requirements.txt` ainda lista `rumps`, mas `src/app.py` não usa mais — remover a linha.
2. Fumaça manual do fluxo completo (F8 -> falar -> soltar -> texto colado).
3. Commit no branch `feature/voz-mvp-ditado` (único branch — não existe `main` nem remote).

## Testes

- `pytest`: **22 passed** (0.38s).
- `ruff check src tests`: **All checks passed** (CC <= 4, LEI 8).
- Cobertura: 100% nas unidades puras (config, transcriber, cleaner, pipeline, bar_color).
  Adapters de I/O (audio_recorder parcial, text_injector, app, waveform_overlay) sem teste
  automático por decisão de design — validados por fumaça manual (I/O de hardware/SO).

## Arquivos-chave

| Arquivo | Responsabilidade | Testado |
|---------|------------------|---------|
| `src/config.py` | Config dataclass + from_env() | sim (TDD) |
| `src/transcriber.py` | Groq Whisper -> texto | sim (TDD) |
| `src/cleaner.py` | Groq Llama limpa transcrição PT-BR | sim (TDD) |
| `src/pipeline.py` | Orquestra transcrição -> limpeza -> injeção | sim (TDD) |
| `src/bar_color.py` | Cor das barras por qualidade de áudio | sim (TDD) |
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

1. Fumaça manual do fluxo F8 de ponta a ponta.
2. Remover `rumps` de `requirements.txt` e commitar a migração AppKit.
3. Criar branch `main` e fazer merge do feature branch.
4. Avaliar rodar em background (nohup ou LaunchAgent).

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
