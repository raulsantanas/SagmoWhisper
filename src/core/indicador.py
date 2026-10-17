"""Lógica pura do indicador de voz (ondas, tempo, aviso de mudo). Sem AppKit."""
import math

# (cor, ciclos na largura, velocidade de fase em rad/s)
ONDAS = (
    ("#7C5CFF", 3.0, 3.0),
    ("#36D1FF", 4.0, 4.0),
    ("#FF5CB4", 5.0, 5.0),
)
AMPLITUDE_MINIMA = 0.04
AMPLITUDE_TRANSCREVENDO = 0.25
SUAVIZACAO = 0.25


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
