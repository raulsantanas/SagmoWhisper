import pytest


@pytest.fixture(autouse=True)
def _glossario_fora_da_home(monkeypatch, tmp_path):
    """Nenhum teste lê os arquivos reais do Raul em ~/.sagmowhisper."""
    from src.core import correcoes, glossario, registro_treino

    monkeypatch.setattr(
        glossario, "CAMINHO_PADRAO", tmp_path / "glossario.json"
    )
    monkeypatch.setattr(
        correcoes, "CAMINHO_PADRAO", tmp_path / "correcoes.json"
    )
    monkeypatch.setattr(
        registro_treino, "CAMINHO_PADRAO", tmp_path / "treino" / "decisoes.jsonl"
    )
