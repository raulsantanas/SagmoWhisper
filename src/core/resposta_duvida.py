"""Responde dúvidas faladas em até 3 frases (ROADMAP 2.5, ROTEAMENTO §4).

A resposta vai para a voz, não para a tela: o limite e a limpeza de markdown
rodam em código, porque o modelo às vezes passa do limite pedido no prompt."""
import logging
import re

from src.core.app_em_foco import app_em_foco as _app_em_foco
from src.core.providers.base import TranscriptionError

logger = logging.getLogger("sagmowhisper")

LIMITE_DE_FRASES = 3

SYSTEM_PROMPT = (
    "Você responde dúvidas que o Raul fez em voz alta. A resposta será falada, "
    "não lida. Responda em português do Brasil, em no máximo 3 frases curtas, "
    "direto ao ponto. Sem markdown, sem listas, sem código e sem links. "
    "Se não reconhecer um nome ou termo, diga que não sabe o que é em vez de "
    "inventar."
)

_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")
_MARCAS_DE_MARKDOWN = re.compile(r"[*`#]")


def ate_tres_frases(texto: str) -> str:
    frases = _FIM_DE_FRASE.split(texto.strip())
    return " ".join(frases[:LIMITE_DE_FRASES])


class RespostaGroq:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def responder(self, pergunta: str) -> str:
        bruta = _MARCAS_DE_MARKDOWN.sub("", self._perguntar(pergunta))
        resposta = ate_tres_frases(bruta)
        if not resposta:
            raise TranscriptionError("groq", "resposta vazia para a dúvida")
        return resposta

    def _perguntar(self, pergunta: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": pergunta},
                ],
            )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        return completion.choices[0].message.content or ""


class AtendenteDeDuvida:
    """atender() devolve True quando a fala era dúvida e já foi respondida em
    voz; False devolve a fala ao ditado. Qualquer falha cai no ditado, que
    cola o texto: perder a fala é pior do que colar uma pergunta."""

    def __init__(self, classificador, resposta, voz, app_em_foco=_app_em_foco):
        self._classificador = classificador
        self._resposta = resposta
        self.voz = voz
        self._app_em_foco = app_em_foco

    def atender(self, texto: str) -> bool:
        try:
            if not self._e_duvida(texto):
                return False
            self.voz.falar(self._resposta.responder(texto))
        except TranscriptionError as e:
            logger.error("Dúvida não atendida, vai como ditado: %s", e)
            return False
        return True

    def _e_duvida(self, texto: str) -> bool:
        decisao = self._classificador.classificar(texto, False, self._app_em_foco())
        logger.info("Intenção: %s (%.2f)", decisao.tipo, decisao.confianca)
        return decisao.tipo == "duvida"
