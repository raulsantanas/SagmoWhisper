import logging
import logging.handlers
import os
import subprocess
import sys
from pathlib import Path

from src.core.app_logging import setup_logging


def _fresh_logger():
    logger = logging.getLogger("sagmowhisper")
    logger.handlers.clear()
    return logger


def test_setup_cria_arquivo_de_log(tmp_path):
    _fresh_logger()
    log_path = tmp_path / "logs" / "app.log"
    logger = setup_logging(log_path)
    logger.error("falha de teste")
    for handler in logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.flush()
            handler.close()
    assert log_path.exists()
    assert "falha de teste" in log_path.read_text()


def test_log_com_acento_sobrevive_a_locale_ascii(tmp_path):
    # Reproduz o bundle py2app: sem locale UTF-8 o open() padrão vira ascii
    # e mensagens acentuadas ("já está rodando") quebravam o file handler.
    log_path = tmp_path / "app.log"
    # O source embutido é ASCII-only (acentos via escape \xe1): `python -c`
    # com bytes não-ASCII no argv falha no STARTUP sob LC_ALL=C no Linux
    # ("Unable to decode the command from the command line") — o subprocesso
    # nem chega a rodar. Em runtime o \xe1 vira o "á" real no log.
    code = (
        "from pathlib import Path\n"
        "from src.core.app_logging import setup_logging\n"
        f"logger = setup_logging(Path({str(log_path)!r}))\n"
        "logger.error('SagmoWhisper j\\xe1 est\\xe1 rodando.')\n"
        # \udce1 é um lone surrogate literal: é exatamente o que o CPython
        # produz ao decodificar argv/filesystem com surrogateescape no
        # Linux sob LC_ALL=C (ex.: "já" -> "j\udce1"). Escrever o escape
        # \uXXXX aqui reproduz o caractere em qualquer plataforma, sem
        # depender da decodificação de argv do SO (que no macOS é sempre
        # UTF-8 e nunca gera surrogates).
        "logger.error('processo j\\udce1 finalizado (surrogate solto)')\n"
    )
    # -X utf8=0: o Python de dev liga UTF-8 mode sozinho em locale C
    # (PEP 540); o Python do bundle não — sem o flag o teste não reproduz.
    env = {**os.environ, "LC_ALL": "C", "LANG": "C"}
    result = subprocess.run(
        [sys.executable, "-X", "utf8=0", "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=Path(__file__).parents[2],
    )
    assert result.returncode == 0, result.stderr
    assert "UnicodeEncodeError" not in result.stderr
    log_text = log_path.read_text(encoding="utf-8")
    assert "já está rodando" in log_text
    assert "j\\udce1 finalizado" in log_text


def test_setup_e_idempotente_nao_duplica_handlers(tmp_path):
    _fresh_logger()
    log_path = tmp_path / "app.log"
    setup_logging(log_path)
    logger = setup_logging(log_path)
    file_handlers = [
        h for h in logger.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert len(file_handlers) == 1
