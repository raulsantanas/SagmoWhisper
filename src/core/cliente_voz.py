"""Lado do hook: entrega o texto ao app e nunca levanta erro, porque uma falha
aqui não pode quebrar o Claude Code (ROADMAP 3.2)."""
import http.client
import json

from src.core.servidor_voz import ENDERECO, ROTA


def enviar(texto: str, porta: int, timeout: float = 1.0) -> bool:
    conexao = http.client.HTTPConnection(ENDERECO, porta, timeout=timeout)
    try:
        conexao.request(
            "POST", ROTA,
            body=json.dumps({"texto": texto}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return conexao.getresponse().status == 204
    except (OSError, http.client.HTTPException):
        return False
    finally:
        conexao.close()
