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
- **Providers plugáveis** — Groq, OpenAI ou faster-whisper local, trocáveis na janela nativa de Configurações (API keys no Keychain do macOS)
- **Limpeza opcional** — hesitações e pontuação corrigidas pelo modelo do provider
- **Orbe ao vivo** — orbe pulsante estilo assistente de IA com barras em escala dB e avisos de sinal fraco/alto
- **Erros visíveis** — falhas viram ⚠️ na barra de menu, com "Último erro" e log em um clique
- **Instância única** — lock por PID impede ícones duplicados na barra

## Requisitos

- macOS
- Python 3.11
- Conta [Groq](https://console.groq.com) (tier gratuito funciona) para a API key
- Libs de sistema: `portaudio`, `libsndfile`

## Instalação (app nativo — recomendado)

Um único comando monta o SagmoWhisper.app no seu próprio Mac e instala em
/Applications — sem conta Apple Developer, sem custo (o build é assinado
localmente com assinatura ad-hoc gratuita):

```bash
brew install portaudio libsndfile
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper
./install.sh
```

O instalador também liga **Abrir no login** — mude quando quiser pelo checkbox
"Abrir no login" em **🎙️ > Configurações…**. Para remover o app depois, rode
`./install.sh --uninstall` (suas configurações e chaves no Keychain são
preservadas).

## Instalação (modo dev — rodar do código)

```bash
# 1. Dependências de sistema
brew install portaudio libsndfile

# 2. Clonar e preparar o ambiente Python
git clone https://github.com/raulsantanas/SagmoWhisper.git
cd SagmoWhisper
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configuração
cp .env.example .env
# edite .env e cole sua GROQ_API_KEY
```

## Configuração

A configuração é feita pelo menu **🎙️ > Configurações…** (escolha de provider Groq/OpenAI/Local, modelo, tecla de atalho), com as API keys guardadas com segurança no **Keychain do macOS**. O arquivo `.env` agora é apenas um override de desenvolvimento.

**Janela de Configurações** (preferências nativas do macOS):
- Seleção de provider: Groq, OpenAI ou Local (faster-whisper)
- API key (guardada com segurança no Keychain, não em arquivos)
- Modelos de transcrição e limpeza (por provider)
- Atribuição de tecla de atalho
- Ativar/desativar limpeza

**Overrides de desenvolvimento** (`.env` apenas):

| Variável | Default | Descrição |
|----------|---------|-----------|
| `PROVIDER` | `groq` | override de provider (`groq`, `openai`, `local`) |
| `OPENAI_API_KEY` | — | override OpenAI dev (apenas dev; produção usa Keychain) |
| `TRANSCRIPTION_MODEL` | por provider | override de modelo de transcrição |
| `CLEANUP_MODEL` | por provider | override de modelo de limpeza |
| `LANGUAGE` | `pt` | idioma da transcrição (`en`, `pt`, …) |
| `ENABLE_CLEANUP` | `true` | limpar hesitações/pontuação |
| `HOTKEY` | `f8` | tecla de gravação (`pynput.keyboard.Key`) |
| `SAMPLE_RATE` | `16000` | taxa de amostragem do áudio |

## Permissões macOS obrigatórias — passo a passo

O SagmoWhisper precisa de três permissões, concedidas uma única vez. Todas
ficam em **Ajustes do Sistema > Privacidade e Segurança** — role a barra
lateral para baixo até encontrar.

> ⚠️ **Atenção:** o item "Acessibilidade" no topo da barra lateral é a área de
> recursos assistivos (VoiceOver, Zoom…) e não tem lista de permissões. O
> caminho certo fica *dentro* de **Privacidade e Segurança**.

1. **Acessibilidade** — permite colar o texto transcrito no cursor
   (Cmd+V programático).
   Abra **Ajustes do Sistema > Privacidade e Segurança > Acessibilidade** e
   ative o **SagmoWhisper.app**. Se não estiver na lista, clique em **+**,
   escolha `/Applications/SagmoWhisper.app` e depois ative a chavinha.

2. **Monitoramento de Entrada** — permite capturar a tecla F8 global em
   qualquer app.
   Ainda em **Privacidade e Segurança**, abra **Monitoramento de Entrada** e
   ative o **SagmoWhisper.app** do mesmo jeito.

3. **Microfone** — grava sua voz. Este *não* dá para adicionar manualmente:
   o macOS mostra o pedido sozinho na primeira gravação — é só aceitar
   (o SagmoWhisper então aparece em **Privacidade e Segurança > Microfone**).

4. **Reinicie o app** — as permissões só valem depois de reiniciar:
   clique em **🎙️ > Sair** na barra de menu e abra o SagmoWhisper de novo
   em /Applications.

Depois faça o primeiro teste: clique em qualquer campo de texto, segure
**F8**, fale uma frase, solte — aceite o pedido de Microfone — e segure **F8**
de novo: o texto aparece no cursor.

Sem as três, o app não captura a tecla, não grava, ou não cola. Em modo dev
(rodando do código), conceda as mesmas permissões ao seu terminal.

## Uso

1. Abra o **SagmoWhisper** em /Applications (ele também abre no login, quando
   ativado) — o ícone 🎙️ aparece na barra de menu, sem ícone no Dock.
2. Configure sua API key em **🎙️ > Configurações…** (guardada no Keychain
   do macOS).
3. Segure **F8**, fale, solte. O texto aparece no cursor.

Se algo falhar, o ícone da barra vira ⚠️ — clique nele para ver a mensagem e o
log (`~/Library/Logs/SagmoWhisper.log`). Para iniciar no login, use o checkbox
**Abrir no login** em **🎙️ > Configurações…** (exige o app instalado).

### Rodar do código (modo dev)

```bash
source .venv/bin/activate
python -m src.app

# ou em background
nohup python -m src.app > /tmp/sagmowhisper.log 2>&1 &
pkill -f "src.app"   # parar
```

## Desenvolvimento

```bash
source .venv/bin/activate
pytest                  # suíte de testes (TDD)
ruff check src tests    # lint + complexidade ciclomática <= 4
```

Arquitetura: unidades puras (`src/core/`, `config`, `transcriber`, `cleaner`,
`pipeline`) cobertas por TDD, com 100% de cobertura nos módulos core; adapters
AppKit/I-O (`audio_recorder`, `text_injector`, `macos/orb_overlay`, `app`) são
validados por fumaça manual documentada. O core é agnóstico de plataforma por
design, para permitir um port Windows futuro.

## Roadmap

- **Port para Windows** — o core (`src/core/`) é agnóstico de plataforma por design

## Licença

[MIT](LICENSE) — © 2026 Raul Santana
