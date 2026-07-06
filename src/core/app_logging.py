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
        # errors="backslashreplace": no Linux sob LC_ALL=C, CPython decodifica
        # argv/filesystem com surrogateescape — um acento como "já" chega ao
        # processo como lone surrogate ("j\udce1"). UTF-8 sozinho não
        # consegue codificar surrogates soltos e o emit() do handler
        # explode; backslashreplace torna qualquer coisa representável sem
        # perder a mensagem (o caso normal com acento real segue intacto).
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
            errors="backslashreplace",
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(file_handler)
        logger.addHandler(logging.StreamHandler(sys.stderr))
    return logger
