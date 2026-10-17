"""Lógica pura do indicador de voz (ondas, tempo, aviso de mudo). Sem AppKit."""
import math
import time

from src.core.audio_level import RecentPeakClassifier

# (cor, ciclos na largura, velocidade de fase em rad/s)
ONDAS = (
    ("#7C5CFF", 3.0, 3.0),
    ("#36D1FF", 4.0, 4.0),
    ("#FF5CB4", 5.0, 5.0),
)
AMPLITUDE_MINIMA = 0.04
AMPLITUDE_TRANSCREVENDO = 0.25
SUAVIZACAO = 0.25
# Sem carência o aviso de mudo dispararia em toda gravação, antes de a pessoa
# começar a falar, e viraria ruído ignorado.
CARENCIA_S = 1.5

ESTILOS_ESCUTA = {
    "ok": ("Ouvindo…", "#E6E7EE"),
    "mudo": ("Não estou ouvindo nada — microfone mudo?", "#FFB4B4"),
    "alto": ("Volume alto", "#F5B942"),
}
_CLASSE_PARA_ESCUTA = {"ok": "ok", "weak": "mudo", "loud": "alto"}


def pontos_da_onda(
    amplitude: float, ciclos: float, fase: float, n: int = 80
) -> list[float]:
    # Envelope sin² zera as pontas: a onda "nasce" e "morre" dentro do cartão.
    return [
        amplitude
        * math.sin(math.pi * u) ** 2
        * math.sin(2 * math.pi * ciclos * u + fase)
        for u in (i / n for i in range(n + 1))
    ]


def suavizar(atual: float, alvo: float) -> float:
    return atual + (alvo - atual) * SUAVIZACAO


def amplitude_ouvindo(nivel: float) -> float:
    return max(AMPLITUDE_MINIMA, nivel)


def formatar_tempo(segundos: float) -> str:
    total = int(segundos)
    return f"{total // 60}:{total % 60:02d}"


def first_line(message: str, max_chars: int = 60) -> str:
    lines = message.splitlines()
    line = lines[0] if lines else ""
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 1] + "…"


class EscutaComCarencia:
    def __init__(self, relogio=time.monotonic):
        self._relogio = relogio
        self._classificador = RecentPeakClassifier(clock=relogio)
        self._inicio = relogio()

    def classificar(self, rms: float) -> str:
        escuta = _CLASSE_PARA_ESCUTA[self._classificador.classify(rms)]
        if escuta == "mudo" and self._em_carencia():
            return "ok"
        return escuta

    def reiniciar(self) -> None:
        self._classificador.reset()
        self._inicio = self._relogio()

    def _em_carencia(self) -> bool:
        return self._relogio() - self._inicio < CARENCIA_S
