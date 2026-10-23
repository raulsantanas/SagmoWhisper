"""Servidor local por onde o hook do Claude Code manda o texto a ser falado
(ROADMAP 3.2, DEC-PV-005).

Só o loopback escuta. Qualquer página aberta no navegador consegue disparar
um POST para 127.0.0.1, então a rota exige JSON (o que obriga o navegador a
fazer preflight) e confere o Host (contra DNS rebinding)."""
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger("sagmowhisper")

ENDERECO = "127.0.0.1"
ROTA = "/falar"
LIMITE_DE_CARACTERES = 1000
LIMITE_DO_CORPO = 8192


class _Recusa(Exception):
    def __init__(self, status: int):
        super().__init__(status)
        self.status = status


class _Servidor(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, endereco, voz):
        super().__init__(endereco, _Pedido)
        self.voz = voz


class _Pedido(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            self._conferir_origem()
            texto = self._ler_texto()
        except _Recusa as recusa:
            return self._responder(recusa.status)
        self.server.voz.falar(texto)
        self._responder(204)

    def do_GET(self):
        self._responder(405)

    def log_message(self, formato, *args):
        logger.debug("servidor de voz: " + formato, *args)

    def _responder(self, status: int):
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        self.end_headers()

    def _conferir_origem(self):
        porta = self.server.server_address[1]
        hosts = (f"{ENDERECO}:{porta}", f"localhost:{porta}")
        if self.headers.get("Host") not in hosts:
            raise _Recusa(403)
        if self.path != ROTA:
            raise _Recusa(404)
        if self.headers.get("Content-Type") != "application/json":
            raise _Recusa(415)

    def _ler_texto(self) -> str:
        return _texto_valido(_json_do_corpo(self._corpo()))

    def _corpo(self) -> bytes:
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise _Recusa(400) from None
        if tamanho > LIMITE_DO_CORPO:
            raise _Recusa(413)
        return self.rfile.read(tamanho)


def _json_do_corpo(corpo: bytes) -> dict:
    try:
        dados = json.loads(corpo)
    except ValueError:
        raise _Recusa(400) from None
    if not isinstance(dados, dict):
        raise _Recusa(400)
    return dados


def _texto_valido(dados: dict) -> str:
    texto = dados.get("texto")
    if not isinstance(texto, str):
        raise _Recusa(400)
    texto = texto.strip()
    if not texto or len(texto) > LIMITE_DE_CARACTERES:
        raise _Recusa(400)
    return texto


class ServidorVoz:
    endereco = ENDERECO

    def __init__(self, voz, porta: int):
        self._voz = voz
        self._porta = porta
        self._http = None

    @property
    def porta(self) -> int:
        return self._http.server_address[1]

    def iniciar(self) -> bool:
        """False se a porta estiver ocupada: o ditado não depende da voz."""
        try:
            self._http = _Servidor((ENDERECO, self._porta), self._voz)
        except OSError as e:
            logger.error("Servidor de voz não iniciou: porta %s (%s)", self._porta, e)
            return False
        # poll curto: parar() espera um ciclo do serve_forever (padrão 0,5 s)
        threading.Thread(
            target=self._http.serve_forever, args=(0.05,), daemon=True
        ).start()
        return True

    def parar(self) -> None:
        if self._http is not None:
            self._http.shutdown()
            self._http.server_close()
