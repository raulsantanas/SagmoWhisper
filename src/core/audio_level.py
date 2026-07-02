import math

DB_FLOOR = -60.0
DB_CEIL = -10.0
WEAK_DB = -50.0
LOUD_DB = -6.0
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
