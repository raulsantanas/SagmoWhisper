import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("sagmowhisper")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # encoding explícito: no bundle py2app (sem locale UTF-8) o default
        # vira ascii e mensagens acentuadas quebravam o handler.
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(file_handler)
        logger.addHandler(logging.StreamHandler(sys.stderr))
    return logger
