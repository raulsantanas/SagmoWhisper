"""Critério de aceite da 2.2 com a Groq real — opt-in, fora do CI.

Rodar: GROQ_API_KEY=... .venv/bin/pytest -m groq_live --no-cov -v
Casos reais do Raul em ROTEAMENTO.md §1; nenhum deles diz "isso é um prompt".
"""
import os

import pytest

from src.core.config import DEFAULTS

pytestmark = [
    pytest.mark.groq_live,
    pytest.mark.skipif(
        not os.environ.get("GROQ_API_KEY"),
        reason="precisa de GROQ_API_KEY no ambiente",
    ),
]

CASO_README = (
    "Eu alterei o README porque gostaria de trocar a tecla F8 pelo Control. "
    "E outra coisa, eu gostaria que ele entendesse automaticamente o que é "
    "um prompt ou não... então dá uma olhada lá no README"
)

CASOS_DO_ROTEAMENTO = [
    (CASO_README, "comando"),
    ("O que é Turbo Stream?", "duvida"),
    ("Qual a diferença entre o Laya e o Jev?", "duvida"),
    (
        "O Laya tem muito falso positivo, certo? Se tiver, troca pelo Groq "
        "na classificação",
        "comando",
    ),
    ("Prezada Dra. Yukimi, segue em anexo o folder revisado", "ditado"),
    ("Corrige o teste do checkout que está falhando", "comando"),
]


@pytest.fixture(scope="module")
def classificador():
    from src.core.intencao import ClassificadorGroq
    from src.core.providers.groq_provider import make_client

    client = make_client(os.environ["GROQ_API_KEY"])
    return ClassificadorGroq(client, DEFAULTS["cleanup_model"])


@pytest.mark.parametrize(("fala", "tipo"), CASOS_DO_ROTEAMENTO)
def test_classifica_os_casos_reais_do_roteamento(classificador, fala, tipo):
    decisao = classificador.classificar(fala, False, None)

    assert decisao.tipo == tipo
    assert decisao.origem == "groq"


def test_caso_readme_vira_comando_com_duas_tarefas(classificador):
    decisao = classificador.classificar(CASO_README, False, None)

    assert decisao.tipo == "comando"
    assert len(decisao.tarefas) == 2
