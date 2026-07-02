# Spec — Milestone 3: SagmoWhisper.app (app nativo do macOS)

> Data: 2026-07-02 · Autor: Raul Santana + Claude · Status: aprovado no brainstorm
> Pré-requisito: Milestone 2 merged (PR #4, providers + Configurações + Keychain)

## Objetivo

Empacotar o SagmoWhisper como app nativo do macOS (`SagmoWhisper.app`): sem "Python"
no Dock, sem terminal aberto, instalável por **um único comando** a partir do
repositório público, com início automático no login controlável pela janela de
Configurações. Custo zero (LEI 10): sem Apple Developer Program.

## Decisões de escopo (fechadas com Raul)

1. **Distribuição = build-from-source.** Quem instala clona o repo e roda
   `./install.sh` — compila na própria máquina (assinatura ad-hoc gratuita; sem
   Gatekeeper/quarentena para builds locais). Binário pronto em GitHub Releases
   (exigiria notarização, US$ 99/ano) fica FORA do M3 — backlog.
2. **Início no login é padrão e mora nas Configurações.** `./install.sh` instala
   com "Abrir no login" LIGADO; a janela de Configurações ganha um checkbox
   "Abrir no login" que liga/desliga sem terminal. Nenhuma flag `--login`/`--no-login`.
3. **Provider Local (faster-whisper) NÃO embarca no bundle** (evita ~1 GB).
   Continua disponível no modo dev (`pip install -e .[local]`). Bundle com Local
   é backlog (futuro `--local`).
4. **CI obrigatório**: em todo PR e push na main, testes + lint + build completo
   do `.app` — proteção para contribuições externas no repo público.

## Ferramenta de empacotamento

**py2app** (canônico para apps pyobjc/AppKit, mesmo ecossistema do autor do pyobjc).

**Plano B declarado: PyInstaller.** Se o build do py2app travar nas libs nativas
(numpy/sounddevice/soundfile) além de ajustes razoáveis de `packages`/`frameworks`,
troca-se apenas o passo de build (setup.py → spec do PyInstaller com `--windowed`
e mesmo Info.plist). `install.sh`, LaunchAgent, Configurações e CI não mudam.

## Componentes

### 1. `launcher.py` (raiz do repo)

Ponto de entrada exigido pelo py2app:

```python
from src.app import main

main()
```

### 2. `setup.py` (raiz do repo)

Configuração py2app:

- `app=["launcher.py"]`
- `packages`: libs compiladas que o py2app não resolve sozinho (mínimo: `numpy`,
  `sounddevice`, `soundfile`, `_soundfile_data` se aplicável; ajustar
  empiricamente no primeiro build)
- Versão lida do `pyproject.toml` (fonte única — sem duplicar número)
- `plist` inline:
  - `CFBundleIdentifier = "com.raulsantana.sagmowhisper"`
  - `CFBundleName = "SagmoWhisper"`
  - `CFBundleShortVersionString` = versão do pyproject
  - **`LSUIElement = True`** — sem ícone no Dock, sem menu de app; só o status item
  - `NSMicrophoneUsageDescription` = "O SagmoWhisper usa o microfone para transcrever sua voz enquanto você segura a tecla de ditado." (dispara o prompt de permissão automaticamente)

### 3. `install.sh` (raiz do repo, executável)

O comando único. Três modos:

- **`./install.sh`** (pessoas):
  1. Valida macOS + Python ≥ 3.11 disponível (mensagem clara se faltar).
  2. Cria venv de build limpo (`.build-venv/`, git-ignorado), instala
     `requirements.txt` + `py2app`.
  3. `python setup.py py2app` → `dist/SagmoWhisper.app`.
  4. Assinatura ad-hoc: `codesign --force --deep -s - dist/SagmoWhisper.app`.
  5. Derruba instância em execução (PID do lock em
     `~/Library/Application Support/SagmoWhisper/app.lock`; ignora se PID morto).
  6. Substitui `/Applications/SagmoWhisper.app` (rm -rf + cp -R).
  7. Liga "Abrir no login": `python -m src.core.login_item enable` (ver §4).
  8. `open /Applications/SagmoWhisper.app` e imprime próximos passos
     (permissões de Acessibilidade/Monitoramento de Entrada).
- **`./install.sh --build-only`** (CI): passos 1–4 e para; não toca em
  /Applications, login nem app rodando.
- **`./install.sh --uninstall`**: remove `/Applications/SagmoWhisper.app`, desliga
  o login (`python -m src.core.login_item disable`), remove o lock. **Preserva**
  `config.json` e chaves no Keychain; imprime instruções de como removê-los
  manualmente se a pessoa quiser (comando `security delete-generic-password` e
  `rm` do config).

Falhas param o script (`set -euo pipefail`) com mensagem em pt-BR.

### 4. `src/core/login_item.py` (novo módulo core — TDD, 100% cobertura)

Lógica do "Abrir no login" via LaunchAgent — puro e testável:

- `AGENT_LABEL = "com.raulsantana.sagmowhisper"`
- `AGENT_PATH = ~/Library/LaunchAgents/com.raulsantana.sagmowhisper.plist`
- `APP_BINARY = /Applications/SagmoWhisper.app/Contents/MacOS/SagmoWhisper`
- `plist_xml(binary_path) -> str` — gera o XML do LaunchAgent
  (`Label`, `ProgramArguments=[binary]`, `RunAtLoad=true`) — função pura.
- `is_enabled(path=AGENT_PATH) -> bool` — o arquivo existe?
- `enable(path=AGENT_PATH, binary=APP_BINARY) -> None` — escreve o plist
  (mkdir parents).
- `disable(path=AGENT_PATH) -> None` — remove o arquivo (silencioso se ausente).
- `app_installed(binary=APP_BINARY) -> bool` — o bundle existe em /Applications?
- CLI mínimo: `python -m src.core.login_item enable|disable|status` — reuso pelo
  `install.sh` sem duplicar a lógica em bash.

Sem `launchctl`: `RunAtLoad` passa a valer no próximo login ao criar o arquivo e
deixa de valer ao removê-lo — sem estado extra, sem processo. O estado do
checkbox É a existência do arquivo (fonte única de verdade, sem campo novo no
config.json).

### 5. Configurações — checkbox "Abrir no login" (`src/macos/settings_window.py`)

- Novo checkbox "Abrir no login" na janela (mesma coluna dos demais controles).
- Estado inicial: `login_item.is_enabled()`.
- Toggle chama `login_item.enable()` / `login_item.disable()` na hora (não espera
  "Salvar" — é estado do sistema, não do config.json; feedback imediato).
- **Modo dev** (bundle não instalado, `login_item.app_installed() == False`):
  checkbox desabilitado com texto auxiliar "Instale o app (./install.sh) para
  ativar" — evita registrar um LaunchAgent apontando para binário inexistente.

### 6. CI — `.github/workflows/ci.yml`

Dois jobs em `macos-latest`, disparados em `pull_request` e `push` na `main`:

1. **test**: setup Python 3.11 → `pip install -r requirements.txt` → `pytest`
   (suíte completa; cobertura já embutida via pyproject) → `ruff check src tests`.
2. **build**: `./install.sh --build-only` → asserts:
   `dist/SagmoWhisper.app/Contents/MacOS/SagmoWhisper` existe e é executável;
   `plutil -extract LSUIElement raw dist/.../Info.plist` == `true`.

Sem segredos no CI (nenhuma chave de API é necessária: testes usam fakes).

### 7. Permissões (TCC) e README

O bundle tem identidade própria — o macOS pede permissões de novo, uma vez:

- **Microfone**: prompt automático na primeira gravação (graças ao usage
  description do plist).
- **Acessibilidade** e **Monitoramento de Entrada**: sem prompt automático para
  apps não assinados com Developer ID; o README (EN + pt-BR) ganha seção
  "Instalação" com o comando único e o passo a passo: Ajustes do Sistema →
  Privacidade e Segurança → adicionar SagmoWhisper nas duas listas.
- Permissões já dadas ao terminal continuam valendo para o modo dev
  (`python -m src.app`).

## Fora de escopo (backlog registrado)

- Notarização + binário em GitHub Releases (US$ 99/ano — decidir se houver demanda)
- Bundle com provider Local embarcado (`--local`, ~1 GB)
- Auto-update do app
- Ícone customizado do bundle (usa o genérico por ora; item barato para depois)
- Backlog herdado do M2 (fallback config corrompido, delete de chave no Keychain,
  persistência do enable_cleanup por provider, aviso de download do modelo local)

## Critérios de sucesso

1. `./install.sh` num clone limpo termina sem erro e resulta em
   `/Applications/SagmoWhisper.app` rodando: ícone 🎙️ na barra, **nenhum ícone no
   Dock, nenhum "Python" visível**.
2. Após conceder permissões e configurar a chave (Configurações → Testar conexão →
   Salvar), F8 dita e cola texto — sem terminal aberto.
3. Checkbox "Abrir no login" nas Configurações liga/desliga o LaunchAgent;
   reiniciar o Mac com ele ligado abre o app sozinho.
4. `./install.sh --uninstall` deixa o Mac sem app, sem LaunchAgent, preservando
   config/Keychain.
5. CI verde em PR: 85+ testes, ruff, e `.app` montado do zero no runner.
6. `src/core/login_item.py` com 100% de cobertura, CC ≤ 4, escrito TDD.
7. Suíte existente intocada e verde; modo dev continua funcionando.

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| py2app falha com numpy/sounddevice | Ajustar `packages`/`excludes`; se persistir, plano B PyInstaller (só muda o passo de build) |
| App zumbi ao sobrescrever binário em execução | install.sh mata pelo PID do lock antes de copiar |
| LaunchAgent apontando para app removido | `--uninstall` sempre chama `disable`; checkbox desabilitado quando bundle ausente |
| Runner do CI sem áudio/GUI | Suíte não toca hardware (core puro + fakes); build não executa o app |
