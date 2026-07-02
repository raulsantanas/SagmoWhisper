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
- **Pluggable providers** — Groq, OpenAI or local faster-whisper, switchable in the native Settings window (API keys in the macOS Keychain)
- **Optional cleanup** — hesitations and punctuation fixed by the provider's model
- **Live orb overlay** — a pulsing AI-assistant-style orb with dB-scaled bars and weak/loud signal warnings
- **Visible errors** — failures show a ⚠️ in the menu bar with a "Last error" entry and a one-click log
- **Single instance** — a PID lock prevents duplicate menu-bar icons

## Requirements

- macOS
- Python 3.11
- A [Groq](https://console.groq.com) account (free tier works) for the API key
- System libraries: `portaudio`, `libsndfile`

## Install (native app — recommended)

One command builds SagmoWhisper.app on your own Mac and installs it into
/Applications — no Apple Developer account, no cost (the build is signed
locally with a free ad-hoc signature):

```bash
brew install portaudio libsndfile
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper
./install.sh
```

The installer also turns on **Open at login** — toggle it any time with the
"Abrir no login" checkbox in **🎙️ > Configurações…**. To remove the app later
run `./install.sh --uninstall` (your settings and Keychain keys are kept).

## Install (dev mode — run from source)

```bash
# 1. System dependencies
brew install portaudio libsndfile

# 2. Clone and set up the Python environment
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# edit .env and paste your GROQ_API_KEY
```

## Configuration

Configuration is done via the menu **🎙️ > Configurações…** (provider Groq/OpenAI/Local, model, hotkey), with API keys securely stored in the **macOS Keychain**. The `.env` file is now a development override only.

**Settings window** (native macOS preferences):
- Provider selection: Groq, OpenAI, or Local (faster-whisper)
- API key (stored securely in Keychain, not in files)
- Transcription and cleanup models (per provider)
- Hotkey assignment
- Cleanup enable/disable

**Development overrides** (`.env` only):

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER` | `groq` | override provider (`groq`, `openai`, `local`) |
| `OPENAI_API_KEY` | — | OpenAI dev override (dev only; production uses Keychain) |
| `TRANSCRIPTION_MODEL` | per provider | override transcription model |
| `CLEANUP_MODEL` | per provider | override cleanup model |
| `LANGUAGE` | `pt` | transcription language (`en`, `pt`, …) |
| `ENABLE_CLEANUP` | `true` | fix hesitations/punctuation |
| `HOTKEY` | `f8` | push-to-talk key (`pynput.keyboard.Key`) |
| `SAMPLE_RATE` | `16000` | audio sample rate |

## Required macOS permissions — step by step

SagmoWhisper needs three permissions, granted once. All of them live in
**System Settings > Privacy & Security** — scroll the sidebar down to find it.

> ⚠️ **Careful:** the "Accessibility" item near the top of the sidebar is the
> assistive-features area (VoiceOver, Zoom…) and has no permission list. The
> one you want is *inside* **Privacy & Security**.

1. **Accessibility** — lets the app paste the transcribed text at your cursor
   (programmatic Cmd+V).
   Open **System Settings > Privacy & Security > Accessibility** and turn on
   **SagmoWhisper.app**. If it is not listed, click **+**, pick
   `/Applications/SagmoWhisper.app` and then turn it on.

2. **Input Monitoring** — lets the global F8 hotkey be captured in any app.
   Still in **Privacy & Security**, open **Input Monitoring** and turn on
   **SagmoWhisper.app** the same way.

3. **Microphone** — records your voice. This one *cannot* be added manually:
   macOS shows a prompt by itself on your first recording — just accept it
   (SagmoWhisper then appears in **Privacy & Security > Microphone**).

4. **Restart the app** — permissions only take effect after a restart:
   click **🎙️ > Sair** in the menu bar, then open SagmoWhisper again from
   /Applications.

Then do a first test: click into any text field, hold **F8**, say a sentence,
release — accept the Microphone prompt — and hold **F8** again: the text
appears at your cursor.

Without all three the app can't capture the key, record, or paste. When
running in dev mode (from source), grant the same permissions to your
terminal instead.

## Usage

1. Open **SagmoWhisper** from /Applications (it also starts at login when
   enabled) — a 🎙️ icon appears in the menu bar, with no Dock icon.
2. Set your API key in **🎙️ > Configurações…** (stored in the macOS Keychain).
3. Hold **F8**, speak, release. The text appears at your cursor.

If anything fails, the menu-bar icon turns ⚠️ — click it for the error message
and the log (`~/Library/Logs/SagmoWhisper.log`). To start at login, use the
**Abrir no login** checkbox in **🎙️ > Configurações…** (requires the
installed app).

### Run from source (dev mode)

```bash
source .venv/bin/activate
python -m src.app

# or in the background
nohup python -m src.app > /tmp/sagmowhisper.log 2>&1 &
pkill -f "src.app"   # stop
```

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

- **Windows port** — the core (`src/core/`) is platform-agnostic by design

## License

[MIT](LICENSE) — © 2026 Raul Santana
