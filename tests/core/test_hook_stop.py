import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.core.hook_stop import (
    PORTA_PADRAO,
    linha_voz,
    porta_do_config,
    texto_para_falar,
)
from src.core.servidor_voz import ServidorVoz

SCRIPT = Path(__file__).parents[2] / "hooks" / "falar_stop.py"


# ---------- linha VOZ: da resposta


def test_pega_o_texto_depois_de_voz():
    resposta = "Corrigi o bug.\n\nVOZ: Corrigi o teste. Falta rodar a suíte."

    assert linha_voz(resposta) == "Corrigi o teste. Falta rodar a suíte."


def test_com_mais_de_uma_linha_voz_vale_a_ultima():
    assert linha_voz("VOZ: primeira\ntexto\nVOZ: segunda") == "segunda"


def test_negrito_em_volta_do_marcador_e_aceito():
    assert linha_voz("**VOZ:** Pronto.") == "Pronto."


@pytest.mark.parametrize("resposta", [
    "", "Sem marcador nenhum.", "VOZ:", "VOZ:   ", "Falei sobre VOZ: no meio",
])
def test_sem_linha_voz_util_devolve_none(resposta):
    assert linha_voz(resposta) is None


def test_texto_gigante_e_cortado_no_limite_do_servidor():
    assert len(linha_voz("VOZ: " + "a" * 5000)) == 1000


# ---------- de onde vem a resposta


def _transcript(tmp_path, linhas):
    caminho = tmp_path / "t.jsonl"
    caminho.write_text("\n".join(json.dumps(x) for x in linhas), encoding="utf-8")
    return str(caminho)


def _assistente(texto):
    return {"type": "assistant", "message": {"content": [
        {"type": "text", "text": texto}]}}


def _ferramenta():
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash"}]}}


def _usuario(texto):
    return {"type": "user", "message": {"content": texto}}


def test_le_a_ultima_resposta_do_transcript(tmp_path):
    caminho = _transcript(tmp_path, [
        _usuario("faz isso"),
        _assistente("VOZ: velha, de outro turno."),
        _usuario("agora aquilo"),
        _ferramenta(),
        _usuario("resultado"),
        _assistente("Terminei."),
        _assistente("VOZ: Terminei aquilo."),
    ])

    assert texto_para_falar({"transcript_path": caminho}) == "Terminei aquilo."


def test_turno_sem_voz_nao_fala_a_do_turno_anterior(tmp_path):
    caminho = _transcript(tmp_path, [
        _assistente("VOZ: velha."), _usuario("e agora?"), _assistente("Sem marcador."),
    ])

    assert texto_para_falar({"transcript_path": caminho}) is None


def test_last_assistant_message_vence_o_transcript(tmp_path):
    caminho = _transcript(tmp_path, [_assistente("VOZ: do arquivo.")])
    entrada = {"last_assistant_message": "VOZ: direto.", "transcript_path": caminho}

    assert texto_para_falar(entrada) == "direto."


@pytest.mark.parametrize("entrada", [
    {}, {"transcript_path": "/nao/existe.jsonl"}, {"transcript_path": 3},
])
def test_entrada_sem_resposta_devolve_none(entrada):
    assert texto_para_falar(entrada) is None


def test_linha_quebrada_no_transcript_e_ignorada(tmp_path):
    caminho = tmp_path / "t.jsonl"
    caminho.write_text("{quebrado\n" + json.dumps(_assistente("VOZ: ok.")))

    assert texto_para_falar({"transcript_path": str(caminho)}) == "ok."


# ---------- porta


def test_porta_vem_do_config(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"voice_port": 50123}))

    assert porta_do_config(config) == 50123


@pytest.mark.parametrize("conteudo", [None, "{quebrado", '{"voice_port": "x"}', "[]"])
def test_porta_padrao_quando_config_falta_ou_estraga(tmp_path, conteudo):
    config = tmp_path / "config.json"
    if conteudo is not None:
        config.write_text(conteudo)

    assert porta_do_config(config) == PORTA_PADRAO


# ---------- o script de verdade, como o Claude Code o chama


class _Voz:
    def __init__(self):
        self.falas = []

    def falar(self, texto):
        self.falas.append(texto)


def _rodar(entrada, porta, tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"voice_port": porta}))
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(entrada), text=True,
        capture_output=True, timeout=10,
        env={"SAGMOWHISPER_CONFIG": str(config), "PATH": "/usr/bin:/bin"},
    )


def test_script_entrega_a_linha_voz_ao_app(tmp_path):
    voz = _Voz()
    servidor = ServidorVoz(voz, porta=0)
    servidor.iniciar()
    try:
        resultado = _rodar(
            {"last_assistant_message": "feito\nVOZ: Terminei a tarefa."},
            servidor.porta, tmp_path,
        )
    finally:
        servidor.parar()

    assert resultado.returncode == 0
    assert voz.falas == ["Terminei a tarefa."]


@pytest.mark.parametrize("stdin", ["", "não é json", "[]"])
def test_script_nunca_quebra_o_claude_code(tmp_path, stdin):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"voice_port": 1}))

    resultado = subprocess.run(
        [sys.executable, str(SCRIPT)], input=stdin, text=True,
        capture_output=True, timeout=10,
        env={"SAGMOWHISPER_CONFIG": str(config), "PATH": "/usr/bin:/bin"},
    )

    assert resultado.returncode == 0


def test_script_com_app_fechado_sai_com_zero_e_sem_ruido(tmp_path):
    resultado = _rodar({"last_assistant_message": "VOZ: oi."}, 1, tmp_path)

    assert resultado.returncode == 0
    assert resultado.stdout == "" and resultado.stderr == ""


def test_porta_padrao_acompanha_o_config_do_app():
    from src.core.config import DEFAULTS

    assert PORTA_PADRAO == DEFAULTS["voice_port"]
