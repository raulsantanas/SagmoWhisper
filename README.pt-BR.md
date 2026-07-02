# SagmoWhisper — ditado por voz global no macOS

> 🇺🇸 [Read in English](README.md)

Segure **F8** em qualquer app (browser, Slack, seu editor, um terminal…), fale,
solte. O áudio é transcrito pelo Groq Whisper, opcionalmente limpo pelo Groq
Llama, e colado onde o cursor estiver — via clipboard + Cmd+V (acentos do
PT-BR preservados).

Um overlay flutuante mostra o nível da sua voz em tempo real, com escala em dB
de verdade e avisos quando o sinal do microfone está realmente fraco ou alto
demais.

## Funcionalidades

- **Ditado push-to-talk em qualquer lugar** — uma tecla (F8 por padrão), funciona em todo app
- **Transcrição rápida e gratuita** — Groq Whisper (`whisper-large-v3-turbo`), roda no tier grátis
- **Limpeza opcional** — hesitações e pontuação corrigidas pelo `llama-3.1-8b-instant`
- **Waveform ao vivo** — barras em escala dB com avisos de sinal fraco/alto
- **Erros visíveis** — falhas viram ⚠️ na barra de menu, com "Último erro" e log em um clique
- **Instância única** — lock por PID impede ícones duplicados na barra

## Requisitos

- macOS
- Python 3.11
- Conta [Groq](https://console.groq.com) (tier gratuito funciona) para a API key
- Libs de sistema: `portaudio`, `libsndfile`

## Instalação

```bash
# 1. Dependências de sistema
brew install portaudio libsndfile

# 2. Clonar e preparar o ambiente Python
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper/voz
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuração
cp .env.example .env
# edite .env e cole sua GROQ_API_KEY
```

### Configuração (.env)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `GROQ_API_KEY` | — | **obrigatória** — sua chave Groq |
| `TRANSCRIPTION_MODEL` | `whisper-large-v3-turbo` | modelo de transcrição |
| `CLEANUP_MODEL` | `llama-3.1-8b-instant` | modelo de limpeza |
| `LANGUAGE` | `pt` | idioma da transcrição (`en`, `pt`, …) |
| `ENABLE_CLEANUP` | `true` | limpar hesitações/pontuação |
| `HOTKEY` | `f8` | tecla de gravação (`pynput.keyboard.Key`) |
| `SAMPLE_RATE` | `16000` | taxa de amostragem do áudio |

## Permissões macOS obrigatórias

Em **Ajustes do Sistema > Privacidade e Segurança**, conceda ao terminal (ou ao
processo Python) estas três permissões:

1. **Microfone** — para gravar o áudio.
2. **Acessibilidade** — para o Cmd+V programático colar o texto.
3. **Monitoramento de Entrada** — para capturar a tecla F8 globalmente.

Sem as três, o app não captura a tecla, não grava, ou não cola. Reinicie o app
após conceder.

## Uso

```bash
source .venv/bin/activate
python -m src.app
```

Segure F8, fale, solte. O texto aparece no cursor. Se algo falhar, o ícone da
barra vira ⚠️ — clique nele para ver a mensagem e o log
(`~/Library/Logs/SagmoWhisper.log`).

### Rodar em background

```bash
source .venv/bin/activate
nohup python -m src.app > /tmp/sagmowhisper.log 2>&1 &

# parar
pkill -f "src.app"
```

Para iniciar no login, crie um LaunchAgent em `~/Library/LaunchAgents/`.

## Desenvolvimento

```bash
source .venv/bin/activate
pytest                  # suíte de testes (TDD)
ruff check src tests    # lint + complexidade ciclomática <= 4
```

Arquitetura: unidades puras (`src/core/`, `config`, `transcriber`, `cleaner`,
`pipeline`) cobertas por TDD, com 100% de cobertura nos módulos core; adapters
AppKit/I-O (`audio_recorder`, `text_injector`, `waveform_overlay`, `app`) são
validados por fumaça manual documentada. O core é agnóstico de plataforma por
design, para permitir um port Windows futuro.

## Roadmap

- **Providers + Configurações** — janela nativa de preferências, providers
  plugáveis (Groq / OpenAI / faster-whisper local), API keys no Keychain do macOS
- **Novo visual + empacotamento** — overlay com orbe pulsante,
  `pipx install sagmowhisper`, CI

## Licença

[MIT](LICENSE) — © 2026 Raul Santana
