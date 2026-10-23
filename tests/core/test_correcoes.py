import json
from pathlib import Path

import pytest

from src.core.correcoes import (
    CORRECOES_INICIAIS,
    TranscriberCorrigido,
    adicionar_correcao,
    aplicar,
    carregar_correcoes,
)
from src.core.providers.base import TranscriptionError


@pytest.mark.parametrize(
    ("falado", "esperado"),
    [
        ("abre o cloud code", "abre o Claude Code"),
        ("abre o Cloud Code agora", "abre o Claude Code agora"),
        ("lê o Rhythm.md e me fala", "lê o README.md e me fala"),
        ("roda o Claudio Code", "roda o Claude Code"),
        ("roda o Cláudio code", "roda o Claude Code"),
    ],
)
def test_corrige_os_erros_conhecidos(falado, esperado):
    assert aplicar(falado, CORRECOES_INICIAIS) == esperado


@pytest.mark.parametrize(
    "intocado",
    [
        "o DNS está na cloudflare", "o Cláudio ligou ontem", "soundcloud", "",
        # Decisão de 18/10: "cloud" sozinho é nuvem, não Claude.
        "salvar na cloud", "app cloud-native",
    ],
)
def test_so_troca_palavra_inteira(intocado):
    assert aplicar(intocado, CORRECOES_INICIAIS) == intocado


def test_sem_arquivo_usa_correcoes_iniciais(tmp_path):
    assert carregar_correcoes(tmp_path / "nao_existe.json") == CORRECOES_INICIAIS


def test_arquivo_do_raul_soma_e_pode_reescrever_uma_inicial(tmp_path):
    caminho = tmp_path / "correcoes.json"
    pares = {"Hostinguer": "Hostinger", "rhythm.md": "Readme.md"}
    caminho.write_text(json.dumps(pares))

    correcoes = carregar_correcoes(caminho)

    assert correcoes["hostinguer"] == "Hostinger"
    assert correcoes["rhythm.md"] == "Readme.md"
    assert correcoes["cloud code"] == "Claude Code"


@pytest.mark.parametrize(
    "conteudo", ['["cloud"]', '{"cloud": 3}', '{"": "x"}', '{"cloud",}']
)
def test_arquivo_invalido_vira_erro_que_o_app_mostra(tmp_path, conteudo):
    caminho = tmp_path / "correcoes.json"
    caminho.write_text(conteudo)

    with pytest.raises(TranscriptionError, match="correcoes.json"):
        carregar_correcoes(caminho)


def test_transcriber_corrigido_corrige_o_que_o_outro_devolve():
    class _Fake:
        def transcribe(self, audio_path):
            return "abre o cloud code"

    t = TranscriberCorrigido(_Fake(), CORRECOES_INICIAIS)

    assert t.transcribe(Path("x.wav")) == "abre o Claude Code"


def test_sem_correcoes_o_texto_passa_intacto():
    assert aplicar("a  b", {}) == "a  b"


def test_chave_com_maiuscula_funciona_sem_normalizar_antes():
    assert aplicar("abre o hostinguer", {"Hostinguer": "Hostinger"}) == (
        "abre o Hostinger"
    )


def test_adicionar_grava_par_que_o_proximo_carregamento_ve(tmp_path):
    caminho = tmp_path / "pasta_nova" / "correcoes.json"

    adicionar_correcao("  Hostinguer ", " Hostinger ", caminho)

    assert carregar_correcoes(caminho)["hostinguer"] == "Hostinger"


def test_adicionar_preserva_pares_que_ja_estavam_no_arquivo(tmp_path):
    caminho = tmp_path / "correcoes.json"
    caminho.write_text(json.dumps({"laia": "Laya"}))

    adicionar_correcao("Sagmo Whisper", "SagmoWhisper", caminho)

    assert json.loads(caminho.read_text(encoding="utf-8")) == {
        "laia": "Laya", "sagmo whisper": "SagmoWhisper",
    }


def test_adicionar_grava_acento_legivel(tmp_path):
    caminho = tmp_path / "correcoes.json"

    adicionar_correcao("neuroenfe", "NeuroEnf é", caminho)

    assert "NeuroEnf é" in caminho.read_text(encoding="utf-8")


@pytest.mark.parametrize(("errado", "certo"), [("", "x"), ("x", "  "), (" ", "")])
def test_adicionar_recusa_lado_vazio_sem_criar_arquivo(tmp_path, errado, certo):
    caminho = tmp_path / "correcoes.json"

    with pytest.raises(ValueError):
        adicionar_correcao(errado, certo, caminho)

    assert not caminho.exists()


def test_adicionar_nao_sobrescreve_arquivo_invalido(tmp_path):
    caminho = tmp_path / "correcoes.json"
    caminho.write_text('{"cloud",}')

    with pytest.raises(TranscriptionError, match="correcoes.json"):
        adicionar_correcao("a", "b", caminho)

    assert caminho.read_text() == '{"cloud",}'
