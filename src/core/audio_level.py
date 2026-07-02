import math
import time
from collections import deque

DB_FLOOR = -60.0
DB_CEIL = -10.0
WEAK_DB = -50.0
LOUD_DB = -6.0
WINDOW_SECONDS = 1.5
_EPS = 1e-6


def rms_to_db(rms: float) -> float:
    return 20.0 * math.log10(max(rms, _EPS))


def rms_to_level(rms: float) -> float:
    level = (rms_to_db(rms) - DB_FLOOR) / (DB_CEIL - DB_FLOOR)
    return min(max(level, 0.0), 1.0)


def classify(rms: float) -> str:
    db = rms_to_db(rms)
    if db > LOUD_DB:
        return "loud"
    if db < WEAK_DB:
        return "weak"
    return "ok"


class RecentPeakClassifier:
    """Classifica pelo pico da janela recente, não pelo bloco instantâneo.

    O microfone entrega ~200 blocos/s e as pausas naturais da fala ficam
    abaixo de WEAK_DB — classificar bloco a bloco faria "áudio fraco"
    aparecer a cada pausa entre palavras.
    """

    def __init__(
        self,
        window_seconds: float = WINDOW_SECONDS,
        clock=time.monotonic,
    ):
        self._window_seconds = window_seconds
        self._clock = clock
        self._samples: deque = deque()

    def classify(self, rms: float) -> str:
        now = self._clock()
        self._samples.append((now, rms))
        cutoff = now - self._window_seconds
        while self._samples[0][0] < cutoff:
            self._samples.popleft()
        peak = max(sample_rms for _, sample_rms in self._samples)
        return classify(peak)

    def reset(self) -> None:
        self._samples.clear()
