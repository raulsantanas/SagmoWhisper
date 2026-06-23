# Voz — ditado por voz global no Mac

Segure **F8** em qualquer app (browser, Slack, Cursor, Claude Code…), fale, solte.
O áudio é transcrito pelo Groq Whisper, opcionalmente limpo pelo Groq Llama, e colado
onde o cursor estiver — via clipboard + Cmd+V (preserva acentos PT-BR).

## Requisitos

- macOS
- Python 3.11
- Conta Groq (tier gratuito) — chave em https://console.groq.com
- Libs de sistema: `portaudio`, `libsndfile`

## Setup

```bash
# 1. Dependências de sistema
brew install portaudio libsndfile

# 2. Ambiente Python
cd /Users/raul/Documents/dev/SagmoWhisper/voz
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuração
cp .env.example .env
# edite .env e cole sua GROQ_API_KEY
```

### Variáveis (.env)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `GROQ_API_KEY` | — | **obrigatória** — sua chave Groq |
| `TRANSCRIPTION_MODEL` | `whisper-large-v3-turbo` | modelo de transcrição |
| `CLEANUP_MODEL` | `llama-3.1-8b-instant` | modelo de limpeza |
| `LANGUAGE` | `pt` | idioma da transcrição |
| `ENABLE_CLEANUP` | `true` | limpar hesitações/pontuação |
| `HOTKEY` | `f8` | tecla de gravação (`pynput.keyboard.Key`) |
| `SAMPLE_RATE` | `16000` | taxa de amostragem do áudio |

## Permissões macOS obrigatórias

Em **System Settings > Privacy & Security**, conceda ao terminal/processo Python:

1. **Microphone** — para gravar o áudio.
2. **Accessibility** — para o Cmd+V programático colar o texto.
3. **Input Monitoring** — para o pynput capturar a tecla F8 globalmente.

Sem as três, o app não captura a tecla, não grava, ou não cola. Reinicie o app
após conceder.

## Uso

```bash
source .venv/bin/activate
python -m src.app
```

Segure F8, fale, solte. O texto aparece no cursor atual.

## Rodar em background

```bash
# opção simples: nohup
source .venv/bin/activate
nohup python -m src.app > /tmp/voz.log 2>&1 &

# parar
pkill -f "src.app"
```

Para iniciar no login, criar um LaunchAgent em `~/Library/LaunchAgents/`.

## Desenvolvimento

```bash
source .venv/bin/activate
pytest                  # suíte de testes
ruff check src tests    # lint + complexidade ciclomática <= 4
```

Arquitetura: unidades puras (`config`, `transcriber`, `cleaner`, `pipeline`) cobertas
por TDD; adapters de I/O (`audio_recorder`, `text_injector`, `app`) validados por
fumaça manual. `pipeline.py` é o coração testável que orquestra tudo.
