#!/bin/bash
# Instala o SagmoWhisper CLI no Ubuntu (sessão Xorg).
# Uso: ./install-linux.sh            instala
#      ./install-linux.sh --uninstall  remove (preserva config e chave no cofre)
set -euo pipefail

APP_DIR="$HOME/.local/share/sagmowhisper"
VENV="$APP_DIR/venv"
BIN_LINK="$HOME/.local/bin/sagmowhisper"
UNIT="$HOME/.config/systemd/user/sagmowhisper.service"

if [ "${1:-}" = "--uninstall" ]; then
    systemctl --user disable sagmowhisper.service 2>/dev/null || true
    rm -f "$UNIT"
    systemctl --user daemon-reload 2>/dev/null || true
    rm -f "$BIN_LINK"
    rm -rf "$APP_DIR"
    echo "✓ Desinstalado. Sua config (~/.config/sagmowhisper) e a chave no cofre foram preservadas."
    exit 0
fi

if command -v apt-get >/dev/null; then
    echo "Instalando dependências do sistema (o sudo pode pedir sua senha)…"
    sudo apt-get update -qq
    sudo apt-get install -y -qq xclip libportaudio2 libsndfile1 python3-venv
fi

echo "Instalando o SagmoWhisper…"
mkdir -p "$APP_DIR" "$HOME/.local/bin"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet .
ln -sf "$VENV/bin/sagmowhisper" "$BIN_LINK"

echo "✓ Instalado."
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) echo "⚠️  ~/.local/bin não está no PATH. Rode:"
     echo '   echo '\''export PATH="$HOME/.local/bin:$PATH"'\'' >> ~/.bashrc && source ~/.bashrc' ;;
esac
echo
echo "Próximo passo:  sagmowhisper setup"
