# SagmoWhisper — global voice dictation for macOS

> 🇧🇷 [Leia em Português](README.pt-BR.md)

Hold **F8** in any app (browser, Slack, your editor, a terminal…), speak, release.
Your audio is transcribed by Groq Whisper, optionally cleaned up by Groq Llama,
and pasted right where your cursor is — via clipboard + Cmd+V (accents and
non-ASCII text are preserved).

A floating orb overlay shows your voice level in real time, with a proper
dB scale and warnings when your mic signal is genuinely too weak or too loud.

## Features

- **Push-to-talk dictation anywhere** — one hotkey (F8 by default), works in every app
- **Fast, free transcription** — Groq Whisper (`whisper-large-v3-turbo`), free tier friendly
- **Optional cleanup** — hesitations and punctuation fixed by `llama-3.1-8b-instant`
- **Live orb overlay** — a pulsing AI-assistant-style orb with dB-scaled bars and weak/loud signal warnings
- **Visible errors** — failures show a ⚠️ in the menu bar with a "Last error" entry and a one-click log
- **Single instance** — a PID lock prevents duplicate menu-bar icons

## Requirements

- macOS
- Python 3.11
- A [Groq](https://console.groq.com) account (free tier works) for the API key
- System libraries: `portaudio`, `libsndfile`

## Install

```bash
# 1. System dependencies
brew install portaudio libsndfile

# 2. Clone and set up the Python environment
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper/voz
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# edit .env and paste your GROQ_API_KEY
```

### Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **required** — your Groq API key |
| `TRANSCRIPTION_MODEL` | `whisper-large-v3-turbo` | transcription model |
| `CLEANUP_MODEL` | `llama-3.1-8b-instant` | cleanup model |
| `LANGUAGE` | `pt` | transcription language (`en`, `pt`, …) |
| `ENABLE_CLEANUP` | `true` | fix hesitations/punctuation |
| `HOTKEY` | `f8` | push-to-talk key (`pynput.keyboard.Key`) |
| `SAMPLE_RATE` | `16000` | audio sample rate |

## Required macOS permissions

In **System Settings > Privacy & Security**, grant your terminal (or the Python
process) these three permissions:

1. **Microphone** — to record audio.
2. **Accessibility** — so the programmatic Cmd+V can paste the text.
3. **Input Monitoring** — so the global F8 hotkey can be captured.

Without all three the app can't capture the key, record, or paste. Restart the
app after granting them.

## Usage

```bash
source .venv/bin/activate
python -m src.app
```

Hold F8, speak, release. The text appears at your cursor. If anything fails,
the menu-bar icon turns ⚠️ — click it for the error message and the log
(`~/Library/Logs/SagmoWhisper.log`).

### Run in the background

```bash
source .venv/bin/activate
nohup python -m src.app > /tmp/sagmowhisper.log 2>&1 &

# stop
pkill -f "src.app"
```

To start at login, create a LaunchAgent in `~/Library/LaunchAgents/`.

## Development

```bash
source .venv/bin/activate
pytest                  # test suite (TDD)
ruff check src tests    # lint + cyclomatic complexity <= 4
```

Architecture: pure units (`src/core/`, `config`, `transcriber`, `cleaner`,
`pipeline`) are TDD-covered with 100% coverage on core modules; AppKit/I-O
adapters (`audio_recorder`, `text_injector`, `macos/orb_overlay`, `app`) are
validated by documented manual smoke tests. The core is platform-agnostic by
design to allow a future Windows port.

## Roadmap

- **Providers + Settings** — native preferences window, pluggable providers
  (Groq / OpenAI / local faster-whisper), API keys stored in the macOS Keychain
- **New visual + packaging** — `pipx install sagmowhisper`, CI

## License

[MIT](LICENSE) — © 2026 Raul Santana
