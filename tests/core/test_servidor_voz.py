import http.client
import json
import socket

import pytest

from src.core.cliente_voz import enviar
from src.core.servidor_voz import LIMITE_DE_CARACTERES, ServidorVoz


class _Voz:
    def __init__(self):
        self.falas = []

    def falar(self, texto):
        self.falas.append(texto)


@pytest.fixture
def servidor():
    voz = _Voz()
    servidor = ServidorVoz(voz, porta=0)
    assert servidor.iniciar() is True
    yield servidor, voz
    servidor.parar()


def _post(servidor, corpo, caminho="/falar", tipo="application/json", host=None):
    conexao = http.client.HTTPConnection("127.0.0.1", servidor.porta, timeout=3)
    cabecalhos = {"Content-Type": tipo}
    if host:
        cabecalhos["Host"] = host
    conexao.request("POST", caminho, body=corpo, headers=cabecalhos)
    return conexao.getresponse().status


def _json(**campos):
    return json.dumps(campos)


def test_post_falar_entrega_o_texto_a_voz(servidor):
    servidor, voz = servidor

    status = _post(servidor, _json(texto="  Terminei os testes.  "))

    assert status == 204
    assert voz.falas == ["Terminei os testes."]


def test_escuta_so_no_loopback(servidor):
    servidor, _ = servidor

    assert servidor.endereco == "127.0.0.1"


def test_content_type_diferente_de_json_e_recusado(servidor):
    # Uma página web consegue disparar POST text/plain para 127.0.0.1 sem
    # preflight; exigir application/json a obriga a passar por ele.
    servidor, voz = servidor

    status = _post(servidor, _json(texto="oi"), tipo="text/plain")

    assert status == 415
    assert voz.falas == []


def test_host_de_fora_e_recusado_contra_dns_rebinding(servidor):
    servidor, voz = servidor

    status = _post(servidor, _json(texto="oi"), host="atacante.com")

    assert status == 403
    assert voz.falas == []


@pytest.mark.parametrize("corpo", [
    "não é json",
    "[]",
    "{}",
    '{"texto": 3}',
    '{"texto": "   "}',
])
def test_corpo_invalido_e_400(servidor, corpo):
    servidor, voz = servidor

    assert _post(servidor, corpo) == 400
    assert voz.falas == []


def test_texto_acima_do_limite_e_400(servidor):
    servidor, voz = servidor

    status = _post(servidor, _json(texto="a" * (LIMITE_DE_CARACTERES + 1)))

    assert status == 400
    assert voz.falas == []


def test_corpo_gigante_e_413_sem_ler(servidor):
    servidor, voz = servidor

    assert _post(servidor, "x" * 20_000) == 413
    assert voz.falas == []


def test_rota_desconhecida_e_404_e_get_e_405(servidor):
    servidor, voz = servidor
    conexao = http.client.HTTPConnection("127.0.0.1", servidor.porta, timeout=3)

    assert _post(servidor, _json(texto="oi"), caminho="/outra") == 404
    conexao.request("GET", "/falar")
    assert conexao.getresponse().status == 405
    assert voz.falas == []


def test_porta_ocupada_nao_derruba_o_app(caplog):
    ocupada = socket.socket()
    ocupada.bind(("127.0.0.1", 0))
    ocupada.listen()
    try:
        servidor = ServidorVoz(_Voz(), porta=ocupada.getsockname()[1])

        assert servidor.iniciar() is False
    finally:
        ocupada.close()
    assert "porta" in caplog.text.lower()


def test_parar_libera_a_porta():
    servidor = ServidorVoz(_Voz(), porta=0)
    servidor.iniciar()
    porta = servidor.porta

    servidor.parar()

    with socket.socket() as teste:
        teste.bind(("127.0.0.1", porta))


# ---------- cliente: o lado do hook, que nunca pode quebrar o Claude Code


def test_cliente_entrega_e_diz_que_entregou(servidor):
    servidor, voz = servidor

    assert enviar("Pronto.", porta=servidor.porta) is True
    assert voz.falas == ["Pronto."]


def test_cliente_com_app_fechado_devolve_false_sem_levantar():
    with socket.socket() as livre:
        livre.bind(("127.0.0.1", 0))
        porta = livre.getsockname()[1]

    assert enviar("Pronto.", porta=porta) is False


def test_cliente_com_resposta_de_erro_devolve_false(servidor):
    servidor, _ = servidor

    assert enviar("   ", porta=servidor.porta) is False
