"""Fala com a Francisca (Edge TTS) sem travar o app (ROADMAP 2.3, DEC-PV-003).

Uma thread só consome a fila: sintetiza o mp3 e toca com o afplay, que é um
processo à parte e por isso pode ser morto no meio da frase (interromper)."""
import asyncio
import logging
import queue
import subprocess
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger("sagmowhisper")

VOZ_PADRAO = "pt-BR-FranciscaNeural"
# Raul ouviu +0/10/20/30% em 2026-10-23 e escolheu +10% (mais natural).
VELOCIDADE_PADRAO = "+10%"


def sintetizar_edge(texto: str, voz: str, destino: Path) -> None:
    import edge_tts

    falar = edge_tts.Communicate(texto, voz, rate=VELOCIDADE_PADRAO)
    asyncio.run(falar.save(str(destino)))


def tocar_afplay(caminho: Path):
    return subprocess.Popen(["afplay", str(caminho)])


class VozEdge:
    def __init__(self, sintetizar=sintetizar_edge, tocar=tocar_afplay,
                 voz: str = VOZ_PADRAO):
        self._sintetizar = sintetizar
        self._tocar = tocar
        self._voz = voz
        self._fila = queue.Queue()
        self._trava = threading.Lock()
        # Cada interromper() abre uma geração nova; frases de gerações
        # anteriores que ainda estão na fila são descartadas.
        self._geracao = 0
        self._player = None
        threading.Thread(target=self._consumir, daemon=True).start()

    def falar(self, texto: str) -> None:
        if texto.strip():
            self._fila.put((self._geracao, texto))

    def interromper(self) -> None:
        with self._trava:
            self._geracao += 1
            player = self._player
        if player is not None:
            player.terminate()

    def esperar(self) -> None:
        """Bloqueia até a fila esvaziar (testes e encerramento)."""
        self._fila.join()

    def _consumir(self):
        while True:
            geracao, texto = self._fila.get()
            try:
                self._falar_agora(geracao, texto)
            except Exception as e:
                logger.exception("Voz falhou (%s): %r", e, texto)
            finally:
                self._fila.task_done()

    def _falar_agora(self, geracao: int, texto: str):
        if geracao != self._geracao:
            return
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "fala.mp3"
            self._sintetizar(texto, self._voz, caminho)
            player = self._iniciar(geracao, caminho)
            if player is not None:
                player.wait()
                self._player = None

    def _iniciar(self, geracao: int, caminho: Path):
        with self._trava:
            if geracao != self._geracao:
                return None
            self._player = self._tocar(caminho)
            return self._player
