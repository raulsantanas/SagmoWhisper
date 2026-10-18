"""Arquivos que o Raul edita em ~/.sagmowhisper (ARQUITETURA.md)."""
import json
from pathlib import Path

from src.core.providers.base import TranscriptionError

PASTA_DADOS = Path.home() / ".sagmowhisper"


def ler_json(caminho: Path, origem: str):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except ValueError as e:
        raise erro_no_arquivo(caminho, origem, f"JSON inválido ({e})") from e


def erro_no_arquivo(caminho: Path, origem: str, motivo: str):
    return TranscriptionError(origem, f"{caminho.name}: {motivo}")
