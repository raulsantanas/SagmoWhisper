import pytest


@pytest.fixture(autouse=True)
def _glossario_fora_da_home(monkeypatch, tmp_path):
    """Nenhum teste lê o glossário real do Raul em ~/.sagmowhisper."""
    from src.core import glossario

    monkeypatch.setattr(
        glossario, "CAMINHO_PADRAO", tmp_path / "glossario.json"
    )
