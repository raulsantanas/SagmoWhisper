"""Fumaça com a API real da Groq — opt-in, fora do CI.

Rodar: GROQ_API_KEY=... .venv/bin/pytest -m groq_live --no-cov -v
Asserções estruturais apenas: saída de LLM varia entre execuções.
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

DITADO_LONGO = (
    "oi carlos tudo bem cara deixa eu te falar eu vi que o faturamento "
    "de junho subiu bastante mas você consegue me passar um resumo das "
    "despesas do mês"
)


@pytest.fixture(scope="module")
def cleaner():
    from src.core.providers.groq_provider import GroqCleaner, make_client

    client = make_client(os.environ["GROQ_API_KEY"])
    return GroqCleaner(client, DEFAULTS["cleanup_model"])


def test_mensagem_longa_ganha_pontuacao_e_preserva_a_pergunta(cleaner):
    saida = cleaner.clean(DITADO_LONGO)
    assert "?" in saida
    assert "Carlos" in saida
    assert "despesas" in saida.lower()
    assert "<think>" not in saida.lower()


def test_pergunta_ditada_nao_e_respondida(cleaner):
    saida = cleaner.clean("quanto é dois mais dois")
    assert "?" in saida
    assert "quatro" not in saida.lower()
    assert "4" not in saida


def test_gatilho_escreva_o_prompt_e_removido_da_saida(cleaner):
    saida = cleaner.clean(
        "escreva o prompt é crie um endpoint de health check no rails "
        "que retorna status e versão do app"
    )
    assert "escreva o prompt" not in saida.lower()
    assert "rails" in saida.lower()


def test_enumeracao_ditada_vira_bullets(cleaner):
    saida = cleaner.clean(
        "preciso de três coisas primeiro o relatório de vendas depois "
        "a lista de leads e por último o acesso ao dashboard"
    )
    assert saida.count("- ") >= 2 or saida.count("• ") >= 2


def test_texto_curto_volta_identico(cleaner):
    assert cleaner.clean("ok").strip().strip(".!").lower() == "ok"
