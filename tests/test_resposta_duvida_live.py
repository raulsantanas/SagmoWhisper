"""Fumaça com o Groq real — opt-in.

Rodar: GROQ_API_KEY=... .venv/bin/pytest -m groq_live --no-cov -v
"""
import os

import pytest

from src.core.resposta_duvida import RespostaGroq, ate_tres_frases

pytestmark = pytest.mark.groq_live


@pytest.fixture(scope="module")
def resposta():
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        pytest.skip("GROQ_API_KEY ausente")
    from src.core.providers.groq_provider import make_client

    return RespostaGroq(make_client(chave), "openai/gpt-oss-120b")


@pytest.mark.parametrize("pergunta", [
    "O que é Turbo Stream?",
    "Qual a diferença entre o Laya e o Jev?",
    "Me explica em detalhes como funciona o garbage collector do Python",
])
def test_responde_em_ate_tres_frases_sem_markdown(resposta, pergunta):
    texto = resposta.responder(pergunta)

    print(f"\n{pergunta} → {texto}")
    assert texto == ate_tres_frases(texto)
    assert not any(marca in texto for marca in "*`#")
