"""Fumaça com o Edge TTS real — opt-in, precisa de internet.

Rodar: .venv/bin/pytest -m edge_live --no-cov -v
"""
import pytest

from src.core.voz import VOZ_PADRAO, sintetizar_edge

pytestmark = pytest.mark.edge_live


def test_francisca_gera_mp3_de_verdade(tmp_path):
    destino = tmp_path / "fala.mp3"

    sintetizar_edge("Olá, Raul. Terminei os testes.", VOZ_PADRAO, destino)

    conteudo = destino.read_bytes()
    assert len(conteudo) > 1000
    assert conteudo[:3] == b"ID3" or conteudo[0] == 0xFF
