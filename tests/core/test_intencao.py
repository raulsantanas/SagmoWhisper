import json
from types import SimpleNamespace

import pytest

from src.core.intencao import ClassificadorGroq, Decisao, aplicar_regras_fixas
from src.core.providers.base import TranscriptionError


def _decisao(**campos) -> Decisao:
    base = {
        "tipo": "comando", "modelo": "sonnet", "esforco": "low",
        "confianca": 0.9, "origem": "groq",
    }
    return Decisao(**{**base, **campos})


# ---------- regras fixas do ROTEAMENTO (valem para qualquer classificador)


def test_confianca_baixa_vira_comando_sonnet_medium():
    incerta = _decisao(tipo="duvida", modelo=None, esforco=None, confianca=0.4)

    assert aplicar_regras_fixas(incerta) == _decisao(
        tipo="comando", modelo="sonnet", esforco="medium", confianca=0.4
    )


@pytest.mark.parametrize("esforco", ["low", "high"])
def test_opus_sempre_em_medium(esforco):
    decisao = aplicar_regras_fixas(_decisao(modelo="opus", esforco=esforco))

    assert decisao.esforco == "medium"


@pytest.mark.parametrize("tipo", ["duvida", "ditado"])
def test_so_comando_tem_modelo_e_esforco(tipo):
    decisao = aplicar_regras_fixas(_decisao(tipo=tipo, tarefas=("x",)))

    assert (decisao.modelo, decisao.esforco, decisao.tarefas) == (None, None, ())


def test_comando_sem_modelo_usa_o_padrao_sonnet_medium():
    decisao = aplicar_regras_fixas(_decisao(modelo=None, esforco=None))

    assert (decisao.modelo, decisao.esforco) == ("sonnet", "medium")


# ---------- ClassificadorGroq com cliente falso


class _ClienteFalso:
    def __init__(self, resposta: str | Exception):
        self.chamadas = []
        self._resposta = resposta
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        if isinstance(self._resposta, Exception):
            raise self._resposta
        mensagem = SimpleNamespace(content=self._resposta)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


def _json(**campos) -> str:
    base = {
        "tipo": "comando", "modelo": "sonnet", "esforco": "low",
        "confianca": 0.82, "tarefas": ["corrigir o teste do checkout"],
    }
    return json.dumps({**base, **campos})


def test_groq_em_modo_json_vira_decisao():
    cliente = _ClienteFalso(_json())

    decisao = ClassificadorGroq(cliente, "modelo-x").classificar(
        "corrige o teste do checkout", False, "com.microsoft.VSCode"
    )

    assert decisao == _decisao(
        confianca=0.82, tarefas=("corrigir o teste do checkout",)
    )
    chamada = cliente.chamadas[0]
    assert chamada["model"] == "modelo-x"
    assert chamada["response_format"] == {"type": "json_object"}
    assert chamada["temperature"] == 0


def test_texto_app_e_imagem_chegam_ao_groq():
    cliente = _ClienteFalso(_json())

    ClassificadorGroq(cliente, "m").classificar(
        "olha esse layout", True, "com.apple.mail"
    )

    usuario = cliente.chamadas[0]["messages"][-1]["content"]
    assert "olha esse layout" in usuario
    assert "com.apple.mail" in usuario
    assert "imagem" in usuario.lower()


def test_regras_fixas_valem_sobre_a_resposta_do_groq():
    cliente = _ClienteFalso(_json(modelo="opus", esforco="high"))

    decisao = ClassificadorGroq(cliente, "m").classificar("x", False, None)

    assert decisao.esforco == "medium"


def test_gatilho_isso_e_um_prompt_e_comando_sem_consultar_o_groq():
    cliente = _ClienteFalso(RuntimeError("não devia chamar"))

    decisao = ClassificadorGroq(cliente, "m").classificar(
        "Isso é um prompt. Eu quero que você gere um relatório final.",
        False, None,
    )

    assert (decisao.tipo, decisao.origem) == ("comando", "regra")
    assert cliente.chamadas == []


@pytest.mark.parametrize(
    "resposta",
    [
        "não é json",
        "[]",
        _json(tipo="pergunta"),
        _json(modelo="gpt"),
        _json(esforco="max"),
        _json(confianca=1.5),
        _json(confianca="alta"),
        _json(tarefas="uma só"),
    ],
)
def test_resposta_invalida_vira_erro_tipado(resposta):
    with pytest.raises(TranscriptionError, match="groq"):
        ClassificadorGroq(_ClienteFalso(resposta), "m").classificar(
            "x", False, None
        )


def test_falha_de_rede_vira_erro_tipado():
    cliente = _ClienteFalso(ConnectionError("sem internet"))

    with pytest.raises(TranscriptionError, match="sem internet"):
        ClassificadorGroq(cliente, "m").classificar("x", False, None)
