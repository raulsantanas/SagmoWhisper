# STATUS — Voz

> Última atualização: 2026-06-23

## Estado atual: MVP completo, testes verdes

Ditado por voz global no Mac. Segura F8 -> grava -> Groq Whisper transcreve ->
(opcional) Groq Llama limpa -> cola no cursor de qualquer app via clipboard + Cmd+V.

## Testes

- `pytest`: **15 passed**.
- `ruff check src tests`: **All checks passed** (complexidade ciclomática <= 4, LEI 8).
- Cobertura: 100% nas unidades puras (config, transcriber, cleaner, pipeline).
  Adapters de I/O (audio_recorder, text_injector, app) sem teste automático por
  decisão de design — validados por fumaça manual (I/O de hardware/SO).

## Arquivos-chave

| Arquivo | Responsabilidade | Testado |
|---------|------------------|---------|
| `src/config.py` | Config dataclass + from_env() | sim (TDD) |
| `src/transcriber.py` | Groq Whisper -> texto | sim (TDD) |
| `src/cleaner.py` | Groq Llama limpa transcrição PT-BR | sim (TDD) |
| `src/pipeline.py` | Orquestra transcrição -> limpeza -> injeção | sim (TDD) |
| `src/audio_recorder.py` | sounddevice -> .wav | fumaça manual |
| `src/text_injector.py` | clipboard + Cmd+V | fumaça manual |
| `src/app.py` | Listener F8 (glue) | fumaça manual |

## Como rodar (dev)

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz
source .venv/bin/activate
pytest                  # suíte
ruff check src tests    # qualidade/complexidade
```

## Como usar

```bash
cp .env.example .env    # cole sua GROQ_API_KEY
source .venv/bin/activate
python -m src.app       # segura F8 para ditar
```

## Próximos passos (fumaça manual obrigatória)

1. Conceder as 3 permissões macOS (ver README): Microfone, Acessibilidade,
   Monitoramento de Entrada — em **System Settings > Privacy & Security**.
2. Rodar `python -m src.app`, segurar F8, falar, soltar; conferir colagem
   correta de acentos PT-BR em browser/Slack/Cursor.
3. Avaliar rodar em background (ver README — nohup ou LaunchAgent).

## Retomar

```bash
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```
