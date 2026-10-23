from types import SimpleNamespace

import pytest

from src.core.intencao import Decisao
from src.core.providers.base import TranscriptionError
from src.core.resposta_duvida import (
    LIMITE_DE_FRASES,
    AtendenteDeDuvida,
    RespostaGroq,
    ate_tres_frases,
)


class _ClienteFalso:
    def __init__(self, conteudo="Resposta.", erro=None):
        self.chamadas = []
        self._conteudo = conteudo
        self._erro = erro
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        if self._erro:
            raise self._erro
        mensagem = SimpleNamespace(content=self._conteudo)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


def test_limite_e_tres_frases():
    assert LIMITE_DE_FRASES == 3


def test_corta_depois_da_terceira_frase():
    texto = "Um. Dois! Três? Quatro. Cinco."

    assert ate_tres_frases(texto) == "Um. Dois! Três?"


def test_texto_curto_fica_igual():
    assert ate_tres_frases("  Só uma frase.  ") == "Só uma frase."


def test_numero_decimal_nao_quebra_frase():
    texto = "Custa 0,5 dólar. Versão 3.11 do Python. Fim. Sobra."

    assert ate_tres_frases(texto) == "Custa 0,5 dólar. Versão 3.11 do Python. Fim."


def test_pergunta_vai_ao_groq_com_o_prompt_de_voz():
    cliente = _ClienteFalso()

    RespostaGroq(cliente, "modelo-x").responder("O que é Turbo Stream?")

    chamada = cliente.chamadas[0]
    assert chamada["model"] == "modelo-x"
    pergunta = {"role": "user", "content": "O que é Turbo Stream?"}
    assert chamada["messages"][-1] == pergunta
    sistema = chamada["messages"][0]["content"]
    assert "3 frases" in sistema and "português" in sistema
    assert "não sabe" in sistema


def test_resposta_longa_sai_cortada_em_tres_frases():
    cliente = _ClienteFalso("A. B. C. D.")

    assert RespostaGroq(cliente, "m").responder("?") == "A. B. C."


def test_markdown_some_porque_vai_ser_falado():
    cliente = _ClienteFalso("**Turbo Stream** é `HTML` parcial.")

    assert RespostaGroq(cliente, "m").responder("?") == "Turbo Stream é HTML parcial."


def test_falha_do_groq_vira_transcription_error():
    cliente = _ClienteFalso(erro=RuntimeError("timeout"))

    with pytest.raises(TranscriptionError, match="timeout"):
        RespostaGroq(cliente, "m").responder("?")


def test_resposta_vazia_vira_erro():
    with pytest.raises(TranscriptionError, match="vazia"):
        RespostaGroq(_ClienteFalso("   "), "m").responder("?")


# ---------- atendente: classifica, responde em voz e diz se a fala foi atendida


class _Classificador:
    def __init__(self, tipo="duvida", erro=None):
        self.chamadas = []
        self._tipo = tipo
        self._erro = erro

    def classificar(self, texto, tem_imagem, app_em_foco):
        self.chamadas.append((texto, tem_imagem, app_em_foco))
        if self._erro:
            raise self._erro
        return Decisao(self._tipo, None, None, 0.9, "groq")


class _Resposta:
    def __init__(self, texto="Resposta curta.", erro=None):
        self._texto = texto
        self._erro = erro

    def responder(self, pergunta):
        if self._erro:
            raise self._erro
        return self._texto


class _Voz:
    def __init__(self):
        self.falas = []

    def falar(self, texto):
        self.falas.append(texto)


def _atendente(classificador=None, resposta=None, voz=None):
    return AtendenteDeDuvida(
        classificador or _Classificador(),
        resposta or _Resposta(),
        voz or _Voz(),
        app_em_foco=lambda: "com.apple.Terminal",
    )


def test_duvida_e_respondida_em_voz_e_conta_como_atendida():
    voz = _Voz()
    classificador = _Classificador()

    atendida = _atendente(classificador, voz=voz).atender("O que é Turbo Stream?")

    assert atendida is True
    assert voz.falas == ["Resposta curta."]
    assert classificador.chamadas == [
        ("O que é Turbo Stream?", False, "com.apple.Terminal")
    ]


@pytest.mark.parametrize("tipo", ["ditado", "comando"])
def test_ditado_e_comando_seguem_o_fluxo_de_colar(tipo):
    voz = _Voz()

    atendida = _atendente(_Classificador(tipo), voz=voz).atender("texto")

    assert atendida is False
    assert voz.falas == []


def test_classificador_falhando_nao_perde_o_ditado(caplog):
    classificador = _Classificador(erro=TranscriptionError("groq", "timeout"))

    assert _atendente(classificador).atender("texto") is False
    assert "timeout" in caplog.text


def test_resposta_falhando_cola_a_pergunta_em_vez_de_sumir(caplog):
    voz = _Voz()
    resposta = _Resposta(erro=TranscriptionError("groq", "sem rede"))

    assert _atendente(resposta=resposta, voz=voz).atender("?") is False
    assert voz.falas == []
    assert "sem rede" in caplog.text
