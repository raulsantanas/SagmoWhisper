#!/bin/bash
# Instala o SagmoWhisper como app nativo do macOS.
# Uso: ./install.sh            build + instala + liga "Abrir no login" + abre
#      ./install.sh --build-only   só monta e assina dist/SagmoWhisper.app (CI)
#      ./install.sh --uninstall    remove app/LaunchAgent/lock (preserva config e Keychain)
set -euo pipefail

APP_NAME="SagmoWhisper"
APP_PATH="/Applications/${APP_NAME}.app"
LOCK_FILE="$HOME/Library/Application Support/SagmoWhisper/app.lock"
AGENT_PLIST="$HOME/Library/LaunchAgents/com.raulsantana.sagmowhisper.plist"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_VENV="$REPO_DIR/.build-venv"

erro() { echo "✗ $1" >&2; exit 1; }

kill_running() {
  if [ -f "$LOCK_FILE" ]; then
    local pid
    pid=$(cat "$LOCK_FILE" 2>/dev/null || true)
    # lock corrompido com "0" ou lixo viraria "kill 0" (grupo inteiro)
    [[ "$pid" =~ ^[1-9][0-9]*$ ]] || return 0
    if kill -0 "$pid" 2>/dev/null; then
      echo "Encerrando instância em execução (PID $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
  fi
}

uninstall() {
  echo "Removendo ${APP_NAME}..."
  kill_running
  rm -rf "$APP_PATH"
  # rm do plist == login_item.disable (sem depender de venv)
  rm -f "$AGENT_PLIST"
  rm -f "$LOCK_FILE"
  echo "✓ App, início no login e lock removidos."
  echo "Suas configurações e chaves foram PRESERVADAS. Para removê-las também:"
  echo "  rm -rf \"\$HOME/Library/Application Support/SagmoWhisper\""
  echo "  security delete-generic-password -s SagmoWhisper"
  exit 0
}

build() {
  [ "$(uname)" = "Darwin" ] || erro "este instalador é só para macOS."
  command -v python3 >/dev/null \
    || erro "python3 não encontrado. Instale o Python 3.11+ (brew install python@3.11)."
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || erro "Python 3.11+ é necessário (encontrado: $(python3 --version))."
  echo "Criando ambiente de build limpo (.build-venv)..."
  rm -rf "$BUILD_VENV"
  python3 -m venv "$BUILD_VENV"
  "$BUILD_VENV/bin/pip" install --quiet --upgrade pip
  "$BUILD_VENV/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt" py2app
  echo "Empacotando ${APP_NAME}.app (pode levar alguns minutos)..."
  cd "$REPO_DIR"
  rm -rf build dist
  "$BUILD_VENV/bin/python" setup.py py2app
  codesign --force --deep -s - "dist/${APP_NAME}.app"
  echo "✓ dist/${APP_NAME}.app montado e assinado (ad-hoc)."
}

case "${1:-}" in
  --uninstall) uninstall ;;
  --build-only) build; exit 0 ;;
  "") ;;
  *) erro "opção desconhecida: $1 (use --build-only ou --uninstall)" ;;
esac

build
kill_running
echo "Instalando em /Applications..."
rm -rf "$APP_PATH"
cp -R "dist/${APP_NAME}.app" "$APP_PATH"
"$BUILD_VENV/bin/python" -m src.core.login_item enable
echo "✓ 'Abrir no login' ligado (desligue quando quiser em 🎙️ → Configurações…)."
open "$APP_PATH"
echo ""
echo "✓ ${APP_NAME} instalado e aberto!"
echo "Passos finais (uma única vez, em Ajustes do Sistema → Privacidade e Segurança):"
echo "  1. Acessibilidade → + → ${APP_NAME}"
echo "  2. Monitoramento de Entrada → + → ${APP_NAME}"
echo "  3. O pedido de Microfone aparece sozinho na primeira gravação."
echo "  4. Configure sua chave em 🎙️ → Configurações…"
echo ""
echo "⚠️  REINSTALANDO? A assinatura nova invalida as permissões antigas em"
echo "   silêncio (as chavinhas parecem ligadas). REMOVA o ${APP_NAME} de"
echo "   Acessibilidade e Monitoramento de Entrada (selecione → −), adicione"
echo "   de novo com +, e reabra o app. Desligar/ligar a chavinha NÃO basta."
