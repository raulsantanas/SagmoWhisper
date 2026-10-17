"""Lógica pura do indicador de voz (ondas, tempo, aviso de mudo). Sem AppKit."""
import math
import time

from src.core.audio_level import DB_FLOOR, RecentPeakClassifier, rms_to_db

# (cor, ciclos na largura, velocidade de fase em rad/s)
ONDAS = (
    ("#7C5CFF", 3.0, 3.0),
    ("#36D1FF", 4.0, 4.0),
    ("#FF5CB4", 5.0, 5.0),
)
AMPLITUDE_MINIMA = 0.04
AMPLITUDE_TRANSCREVENDO = 0.25
# A onda mede a voz contra o ruído de fundo do ambiente, não contra uma
# escala fixa: com escala fixa, ruído a -45 dB já ocupava ~30% da altura e a
# fala mal se destacava. O piso desce rápido (pausas) e sobe devagar, para a
# fala contínua não virar "ruído". O ruído em si não é filtrado.
MARGEM_DB = 4.0
FAIXA_DB = 14.0
PISO_SOBE = 0.003
PISO_DESCE = 0.3
SUBIDA = 0.6
DESCIDA = 0.15
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


class PicoEntreQuadros:
    """O microfone entrega ~200 blocos/s e a tela desenha 30: guarda o maior."""

    def __init__(self):
        self._pico = 0.0

    def registrar(self, rms: float) -> None:
        self._pico = max(self._pico, rms)

    def consumir(self) -> float:
        pico, self._pico = self._pico, 0.0
        return pico


class NivelDaVoz:
    def __init__(self):
        self._piso_db = None
        self._nivel = 0.0

    def avancar(self, rms: float) -> float:
        db = rms_to_db(rms)
        self._atualizar_piso(db)
        alvo = (db - self._piso_db - MARGEM_DB) / FAIXA_DB
        alvo = min(max(alvo, 0.0), 1.0)
        passo = SUBIDA if alvo > self._nivel else DESCIDA
        self._nivel += (alvo - self._nivel) * passo
        return self._nivel

    def _atualizar_piso(self, db: float) -> None:
        if self._piso_db is None:
            self._piso_db = max(db, DB_FLOOR)
            return
        taxa = PISO_DESCE if db < self._piso_db else PISO_SOBE
        self._piso_db = max(self._piso_db + (db - self._piso_db) * taxa, DB_FLOOR)
