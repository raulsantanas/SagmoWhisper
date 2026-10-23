"""Lógica do hook Stop do Claude Code: acha a linha `VOZ:` na resposta e a
entrega ao app (ROADMAP 3.1).

Só stdlib e anotações adiadas: o hook roda no python3 do sistema, não no venv
do app. Nada aqui pode levantar erro para fora de main()."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from src.core.cliente_voz import enviar
from src.core.servidor_voz import LIMITE_DE_CARACTERES

# Cópia de DEFAULTS["voice_port"]: importar config.py traria dotenv e keyring.
# Um teste garante que as duas continuam iguais.
PORTA_PADRAO = 47821

_LINHA_VOZ = re.compile(r"^[ \t]*[*_]*VOZ:[*_]*[ \t]*(.+?)[ \t]*$", re.MULTILINE)


def linha_voz(resposta: str) -> str | None:
    achadas = _LINHA_VOZ.findall(resposta)
    texto = achadas[-1].strip() if achadas else ""
    return texto[:LIMITE_DE_CARACTERES] or None


def texto_para_falar(entrada: dict) -> str | None:
    resposta = entrada.get("last_assistant_message")
    if not isinstance(resposta, str):
        resposta = _ultima_resposta(entrada.get("transcript_path"))
    return linha_voz(resposta)


def _ultima_resposta(caminho) -> str:
    """Texto do turno atual: o que vem depois da última entrada `user`."""
    if not isinstance(caminho, str):
        return ""
    trechos = []
    for entrada in _entradas_do_fim(caminho):
        if entrada.get("type") == "user":
            break
        trechos = _textos(entrada) + trechos
    return "\n".join(trechos)


def _entradas_do_fim(caminho: str):
    try:
        linhas = Path(caminho).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    for linha in reversed(linhas):
        entrada = _entrada(linha)
        if entrada is not None:
            yield entrada


def _entrada(linha: str) -> dict | None:
    try:
        entrada = json.loads(linha)
    except ValueError:
        return None
    return entrada if isinstance(entrada, dict) else None


def _textos(entrada: dict) -> list:
    if entrada.get("type") != "assistant":
        return []
    blocos = entrada.get("message", {}).get("content", [])
    return [b["text"] for b in blocos if b.get("type") == "text"]


def caminho_do_config(env, platform: str = sys.platform) -> Path:
    if env.get("SAGMOWHISPER_CONFIG"):
        return Path(env["SAGMOWHISPER_CONFIG"])
    casa = Path(env.get("HOME", "~")).expanduser()
    if platform == "darwin":
        return casa / "Library/Application Support/SagmoWhisper/config.json"
    return casa / ".config/sagmowhisper/config.json"


def porta_do_config(caminho: Path) -> int:
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return PORTA_PADRAO
    porta = dados.get("voice_port") if isinstance(dados, dict) else None
    ok = isinstance(porta, int) and not isinstance(porta, bool)
    return porta if ok else PORTA_PADRAO


def main(stdin_texto: str, env, entregar=enviar) -> int:
    """Sempre 0: falha na voz não pode atrapalhar o Claude Code."""
    try:
        entrada = json.loads(stdin_texto)
    except ValueError:
        return 0
    texto = texto_para_falar(entrada) if isinstance(entrada, dict) else None
    if texto:
        entregar(texto, porta_do_config(caminho_do_config(env)))
    return 0
