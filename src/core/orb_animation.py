"""Matemática pura da animação da orbe (mockup D). Sem AppKit."""

ORB_SCALE_MIN = 0.9
ORB_SCALE_MAX = 1.12
GLOW_MIN = 0.35
GLOW_MAX = 1.0
RING_PERIOD_S = 1.2
ROTATION_PERIOD_S = 4.0


def orb_scale(level: float) -> float:
    return ORB_SCALE_MIN + level * (ORB_SCALE_MAX - ORB_SCALE_MIN)


def orb_glow(level: float) -> float:
    return GLOW_MIN + level * (GLOW_MAX - GLOW_MIN)


def ring_progress(elapsed: float) -> float:
    return (elapsed % RING_PERIOD_S) / RING_PERIOD_S


def rotation_angle(elapsed: float) -> float:
    return (elapsed % ROTATION_PERIOD_S) / ROTATION_PERIOD_S * 360.0


def first_line(message: str, max_chars: int = 60) -> str:
    lines = message.splitlines()
    line = lines[0] if lines else ""
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 1] + "…"
