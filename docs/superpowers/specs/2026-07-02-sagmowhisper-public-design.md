# SagmoWhisper — Design: versão pública open source

> Data: 2026-07-02
> Status: aprovado por Raul
> Escopo: evoluir o app Voz para repositório público "SagmoWhisper" no GitHub

## Contexto

O MVP (ditado por voz global no macOS: segurar F8 → gravar → transcrever via
Groq Whisper → colar no cursor) está funcional e validado de ponta a ponta.
Esta evolução corrige dois defeitos conhecidos, adiciona configuração por
interface e prepara o projeto para uso público.

Defeitos conhecidos que este design corrige:

1. **Sensibilidade do waveform**: a amplitude usa RMS linear (`rms * 120`,
   threshold 0.02). Voz normal em mic típico fica em RMS 0.01–0.05, então as
   barras quase não mexem e o aviso "áudio fraco" aparece sempre. Percepção de
   áudio é logarítmica — a escala correta é dB.
2. **Erros engolidos em silêncio**: falha de transcrição (ex.: 401 da Groq) só
   gera `print` bufferizado (perdido) e NSUserNotification (não entregue para
   Python fora de bundle). O usuário não vê nada.
3. **Instâncias duplicadas**: nada impede duas cópias do app rodando (dois
   ícones na barra, comportamento imprevisível).

## Decisões de produto (fechadas com o usuário)

| Decisão | Escolha |
|---|---|
| Nome público | **SagmoWhisper** |
| Licença | **MIT** |
| Documentação | README.md em EN + README.pt-BR.md; UI do app em PT-BR |
| Plataforma | **macOS primeiro**; core em camadas para port Windows futuro |
| Providers | **Groq + OpenAI + Local (faster-whisper)**, arquitetura pluggable |
| Armazenamento de keys | **`keyring`** (Keychain no macOS; Credential Manager quando houver port) |
| Configurações | **Janela nativa de preferências** (AppKit) |
| Visual do overlay | **Orbe + Barras** (mockup D: orbe pulsante estilo assistente de IA, roxo, anel expandindo, barras discretas ao lado) |

## Arquitetura

```
src/
  core/                    # 100% multiplataforma, sem AppKit, testável
    config.py              # settings JSON em ~/Library/Application Support/SagmoWhisper/
                           # (path resolvido por plataforma; .env continua como override de dev)
    secrets.py             # get/set de API keys via keyring
    audio_recorder.py      # sounddevice (existente, movido)
    audio_level.py         # NOVO: rms_to_level(rms) -> 0..1 via dB; classify(level)
    pipeline.py            # existente, movido
    text_injector.py       # existente; Cmd+V (darwin) / Ctrl+V (win32) por branch
    single_instance.py     # NOVO: lock file com PID; segunda instância sai com aviso
    providers/
      base.py              # contrato TranscriptionProvider / CleanupProvider
      groq_provider.py     # existente (transcriber.py + cleaner.py migram para cá)
      openai_provider.py   # NOVO
      local_provider.py    # NOVO: faster-whisper, import lazy
  macos/                   # única camada com AppKit
    menu_bar.py            # NSStatusBar: ícone de estado, menu (Configurações…, Sair)
    orb_overlay.py         # NOVO overlay Orbe + Barras (substitui waveform_overlay.py)
    settings_window.py     # NOVO janela de preferências
  app.py                   # entry point: single-instance -> config -> UI -> listener
```

Port Windows futuro = nova pasta `src/windows/` implementando a mesma
interface de UI; zero mudança no core.

### Contrato de provider

```python
class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: Path) -> str: ...

class CleanupProvider(Protocol):
    def clean(self, text: str) -> str: ...
```

- `groq_provider`: modelos `whisper-large-v3`, `whisper-large-v3-turbo`
  (transcrição) e `llama-3.1-8b-instant` (limpeza).
- `openai_provider`: `whisper-1`/`gpt-4o-transcribe` (transcrição),
  `gpt-4o-mini` (limpeza).
- `local_provider`: `faster-whisper` com modelo `small` como default
  (download automático no primeiro uso, com aviso na UI). Dependência
  **opcional**: `pip install sagmowhisper[local]` — import lazy para o app
  funcionar sem ela.
- Erros de provider viram exceção tipada `TranscriptionError(provider, detail)`
  para a UI exibir mensagem útil.

## Correção da sensibilidade (audio_level.py)

- `rms_to_db(rms) = 20 * log10(max(rms, 1e-6))`
- `rms_to_level(rms)`: mapeia −60 dB…−10 dB linearmente para 0.0…1.0 (clamp).
  Voz normal (~RMS 0.02 ≈ −34 dB) resulta em ~0.52 — amplitude visível.
- `classify(rms)` substitui `bar_color`: "fraco" < −50 dB, "alto" > −6 dB,
  "ok" no meio. Cores continuam decididas na camada de UI.
- Módulo puro, TDD, 100% de cobertura (LEIS 2 e 8). `bar_color.py` é removido.

## Janela de Configurações

Campos:

1. **Provider** (popup: Groq / OpenAI / Local)
2. **API key** do provider selecionado (campo secure text; salva no Keychain
   via `secrets.py`; oculto quando provider = Local)
3. **Modelo de transcrição** (popup filtrado pelo provider)
4. **Limpeza de texto** (checkbox + popup de modelo, quando provider suporta)
5. **Hotkey** (popup com F-keys; default F8)

Comportamento: salvar grava config JSON + Keychain e **aplica na hora**
(pipeline e listener são recriados; sem reiniciar o app). Validação: botão
"Testar conexão" faz uma chamada mínima ao provider e mostra ✓/✗ com a
mensagem de erro real.

Migração: na primeira execução, se existir `.env` com `GROQ_API_KEY` e não
existir config JSON, importa os valores silenciosamente (compatibilidade com
instalação atual do Raul).

## Overlay Orbe + Barras (orb_overlay.py)

- Janela flutuante borderless (como hoje), canto superior esquerdo.
- **Orbe** (~46 pt): gradiente radial roxo; escala 0.9→1.12 e brilho
  proporcionais ao nível de voz (`audio_level`); anel expandindo em loop.
- **Barras** (~20): à direita da orbe, altura pelo nível, cor roxa; histórico
  deslizante como hoje.
- Estados: **ouvindo** (roxo pulsante + "🎙️ Ouvindo...") · **transcrevendo**
  (orbe em rotação lenta, barras congeladas a 40% de alpha, "⏳
  Transcrevendo...") · **erro** (orbe vermelha por 2 s + primeira linha da
  mensagem antes do fade-out).
- Mesmo mecanismo thread-safe atual (lock + performSelectorOnMainThread).

## Erros visíveis (nunca mais em silêncio)

- `logging` estruturado para `~/Library/Logs/SagmoWhisper.log`
  (RotatingFileHandler, 1 MB × 3) + stderr.
- Em falha de pipeline: ícone da barra vira ⚠️, item de menu "Último erro: …"
  (clicável → abre o log), overlay mostra estado de erro.
- Exceções de provider sempre capturadas e logadas com stack trace; o app
  nunca morre por falha de transcrição.

## Instância única (single_instance.py)

Lock file com PID em `~/Library/Application Support/SagmoWhisper/app.lock`.
Na inicialização: se o lock existe e o PID está vivo → imprime aviso e sai
com código 1; se o PID está morto → assume o lock (crash anterior). Módulo
puro, TDD.

## Repositório público

- `LICENSE` (MIT) · `README.md` (EN, com GIF de demonstração e instruções das
  3 permissões macOS) · `README.pt-BR.md` · `CONTRIBUTING.md` (setup dev,
  TDD, ruff, como adicionar um provider).
- `pyproject.toml` empacotado: `pipx install sagmowhisper`, entry point
  `sagmowhisper`; extra `[local]` para faster-whisper.
- CI GitHub Actions: `pytest` + `ruff check` em cada push/PR (LEI 8
  automatizada).
- Higiene: `.gitignore` cobre `.superpowers/`, `.codegraph/`, caches, `.env`
  (já não rastreado — verificado); remover `rumps` do `requirements.txt`
  (órfão da migração AppKit); commitar o trabalho pendente; criar branch
  `main` e fazer dele o default.

## Testes

- **TDD obrigatório** (LEI 2) para: `audio_level`, `config`, `secrets`
  (keyring mockado), `single_instance`, `providers/*` (HTTP mockado),
  `pipeline` (existente).
- Camada `macos/` (AppKit): fumaça manual documentada no STATUS.md, como hoje.
- Cobertura 100% nos módulos puros; CC ≤ 4 por método (LEI 8, ruff).

## Milestones (cada um termina utilizável e commitado)

1. **Fundação** — `audio_level` em dB + erros visíveis (log/ícone/menu) +
   `single_instance` + higiene git (remover rumps, commitar migração AppKit,
   criar `main`).
2. **Providers + Configurações** — contrato de provider, migração do código
   Groq, OpenAI, local opcional, `secrets`/keyring, `config` JSON, janela de
   preferências com aplicar-na-hora e testar-conexão.
3. **Visual + lançamento** — `orb_overlay`, migração final dos arquivos
   restantes para `core/`/`macos/`, empacotamento pipx,
   README/LICENSE/CONTRIBUTING/CI, publicar no GitHub.

Regra de organização: módulo **novo** já nasce no caminho final
(`src/core/...` ou `src/macos/...`) desde o milestone 1; arquivo **existente**
migra quando for tocado, e o que sobrar migra no milestone 3.

## Fora de escopo (YAGNI explícito)

- Port Windows/Linux (arquitetura preparada, implementação futura)
- i18n da interface (PT-BR fixo por ora)
- App bundle (.app / DMG / brew cask) — pipx primeiro
- Histórico de ditados, atalhos múltiplos, streaming em tempo real
