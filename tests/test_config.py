import pytest
from unittest.mock import patch

from src.config import Config


def test_from_env_reads_all_vars(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")
    monkeypatch.setenv("CLEANUP_MODEL", "llama-3.1-8b-instant")
    monkeypatch.setenv("LANGUAGE", "pt")
    monkeypatch.setenv("ENABLE_CLEANUP", "true")
    monkeypatch.setenv("HOTKEY", "f8")
    monkeypatch.setenv("SAMPLE_RATE", "16000")

    cfg = Config.from_env()

    assert cfg.groq_api_key == "gsk_test"
    assert cfg.transcription_model == "whisper-large-v3-turbo"
    assert cfg.cleanup_model == "llama-3.1-8b-instant"
    assert cfg.language == "pt"
    assert cfg.enable_cleanup is True
    assert cfg.hotkey == "f8"
    assert cfg.sample_rate == 16000


@patch("src.config.load_dotenv")
def test_from_env_raises_clear_error_when_api_key_missing(
    mock_load_dotenv, monkeypatch
):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        Config.from_env()


def test_enable_cleanup_parses_false(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("ENABLE_CLEANUP", "false")

    cfg = Config.from_env()

    assert cfg.enable_cleanup is False


def test_enable_cleanup_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("ENABLE_CLEANUP", "TRUE")

    cfg = Config.from_env()

    assert cfg.enable_cleanup is True


@patch("src.config.load_dotenv")
def test_defaults_applied_when_optional_vars_absent(mock_load_dotenv, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    for var in (
        "TRANSCRIPTION_MODEL",
        "CLEANUP_MODEL",
        "LANGUAGE",
        "ENABLE_CLEANUP",
        "HOTKEY",
        "SAMPLE_RATE",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = Config.from_env()

    assert cfg.transcription_model == "whisper-large-v3-turbo"
    assert cfg.cleanup_model == "llama-3.1-8b-instant"
    assert cfg.language == "pt"
    assert cfg.enable_cleanup is True
    assert cfg.hotkey == "f8"
    assert cfg.sample_rate == 16000
