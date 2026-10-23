import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.core import registro_treino
from src.core.correcoes import CORRECOES_INICIAIS, TranscriberCorrigido
from src.core.registro_treino import RegistroTreino

_BRT = timezone(timedelta(hours=-3))


def _relogio():
    return datetime(2026, 10, 17, 17, 40, tzinfo=_BRT)


def _linhas(caminho: Path) -> list[dict]:
    return [json.loads(linha) for linha in caminho.read_text("utf-8").splitlines()]


def test_cada_fala_vira_uma_linha_no_formato_do_roteamento(tmp_path):
    caminho = tmp_path / "treino" / "decisoes.jsonl"
    registro = RegistroTreino(caminho, relogio=_relogio)

    registro.registrar(
        "corrige o teste do cloud code", "corrige o teste do Claude Code"
    )
    registro.registrar("o que é Turbo Stream?", "o que é Turbo Stream?")

    linhas = _linhas(caminho)
    assert len(linhas) == 2
    assert linhas[0] == {
        "ts": "2026-10-17T17:40:00-03:00",
        "app_em_foco": None,
        "texto_bruto": "corrige o teste do cloud code",
        "texto_corrigido": "corrige o teste do Claude Code",
        "decisao": None,
        "correcao_do_raul": None,
    }


def test_grava_acento_legivel(tmp_path):
    caminho = tmp_path / "decisoes.jsonl"

    RegistroTreino(caminho, relogio=_relogio).registrar("ação", "ação")

    assert "ação" in caminho.read_text("utf-8")


def test_sem_caminho_usa_o_padrao_da_home_isolada():
    RegistroTreino(relogio=_relogio).registrar("oi", "oi")

    assert len(_linhas(registro_treino.CAMINHO_PADRAO)) == 1


def test_falha_de_disco_nao_derruba_o_ditado(tmp_path, caplog):
    bloqueio = tmp_path / "arquivo"
    bloqueio.write_text("")
    registro = RegistroTreino(bloqueio / "decisoes.jsonl", relogio=_relogio)

    registro.registrar("oi", "oi")

    assert "registro de treino" in caplog.text


class _Fake:
    def __init__(self, texto):
        self._texto = texto

    def transcribe(self, audio_path):
        return self._texto


def test_transcriber_corrigido_registra_bruto_e_corrigido(tmp_path):
    caminho = tmp_path / "decisoes.jsonl"
    registro = RegistroTreino(caminho, relogio=_relogio)
    t = TranscriberCorrigido(
        _Fake("abre o cloud code"), CORRECOES_INICIAIS, registro
    )

    assert t.transcribe(Path("x.wav")) == "abre o Claude Code"
    linha = _linhas(caminho)[0]
    assert linha["texto_bruto"] == "abre o cloud code"
    assert linha["texto_corrigido"] == "abre o Claude Code"


def test_silencio_nao_vira_linha(tmp_path):
    caminho = tmp_path / "decisoes.jsonl"
    registro = RegistroTreino(caminho, relogio=_relogio)

    TranscriberCorrigido(_Fake("  "), CORRECOES_INICIAIS, registro).transcribe(
        Path("x.wav")
    )

    assert not caminho.exists()
