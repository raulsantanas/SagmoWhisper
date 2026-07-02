import logging
import logging.handlers

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
