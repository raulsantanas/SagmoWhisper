"""Decide se a fala é dúvida, comando ou ditado (ROADMAP 2.2, ROTEAMENTO.md).

O Groq propõe; as regras fixas do ROTEAMENTO têm a palavra final, para que
o Laya (Fase 4) herde as mesmas garantias implementando o mesmo Protocol."""
import json
from dataclasses import dataclass, replace
from typing import Literal, Protocol

from src.core.providers.base import TranscriptionError, prompt_register_triggered

TIPOS = ("duvida", "comando", "ditado")
MODELOS = ("opus", "sonnet", "haiku")
ESFORCOS = ("low", "medium", "high")
CONFIANCA_MINIMA = 0.6


@dataclass(frozen=True)
class Decisao:
    tipo: Literal["duvida", "comando", "ditado"]
    modelo: Literal["opus", "sonnet", "haiku"] | None
    esforco: Literal["low", "medium", "high"] | None
    confianca: float
    origem: Literal["groq", "laya", "regra"]
    tarefas: tuple[str, ...] = ()


class ClassificadorIntencao(Protocol):
    def classificar(
        self, texto: str, tem_imagem: bool, app_em_foco: str | None
    ) -> Decisao: ...


_DECISAO_DO_GATILHO = Decisao("comando", "sonnet", "medium", 1.0, "regra")


def aplicar_regras_fixas(decisao: Decisao) -> Decisao:
    if decisao.confianca < CONFIANCA_MINIMA:
        # Mais barato confirmar um prompt do que perder um pedido.
        return replace(decisao, tipo="comando", modelo="sonnet", esforco="medium")
    if decisao.tipo != "comando":
        return replace(decisao, modelo=None, esforco=None, tarefas=())
    return _roteamento_do_comando(decisao)


def _roteamento_do_comando(decisao: Decisao) -> Decisao:
    if decisao.modelo is None:
        return replace(decisao, modelo="sonnet", esforco="medium")
    if decisao.modelo == "opus" or decisao.esforco is None:
        return replace(decisao, esforco="medium")
    return decisao


class ClassificadorGroq:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def classificar(
        self, texto: str, tem_imagem: bool, app_em_foco: str | None
    ) -> Decisao:
        if prompt_register_triggered(texto):
            return _DECISAO_DO_GATILHO
        resposta = self._perguntar(_mensagem(texto, tem_imagem, app_em_foco))
        return aplicar_regras_fixas(_decisao_do_json(resposta))

    def _perguntar(self, mensagem: str) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *EXEMPLO,
                    {"role": "user", "content": mensagem},
                ],
            )
        except Exception as e:
            raise TranscriptionError("groq", str(e)) from e
        return completion.choices[0].message.content


def _mensagem(texto: str, tem_imagem: bool, app_em_foco: str | None) -> str:
    return (
        f"App em foco: {app_em_foco or 'desconhecido'}\n"
        f"Imagem anexada: {'sim' if tem_imagem else 'não'}\n"
        f"Fala transcrita: {texto}"
    )


def _decisao_do_json(resposta: str) -> Decisao:
    try:
        dados = json.loads(resposta)
    except (TypeError, ValueError) as e:
        raise _invalida("não é JSON") from e
    if not isinstance(dados, dict):
        raise _invalida("esperado um objeto JSON")
    return Decisao(
        tipo=_escolha(dados, "tipo", TIPOS),
        modelo=_escolha_opcional(dados, "modelo", MODELOS),
        esforco=_escolha_opcional(dados, "esforco", ESFORCOS),
        confianca=_confianca(dados.get("confianca")),
        origem="groq",
        tarefas=_tarefas(dados.get("tarefas", [])),
    )


def _escolha(dados: dict, campo: str, opcoes: tuple[str, ...]) -> str:
    valor = dados.get(campo)
    if valor not in opcoes:
        raise _invalida(f"{campo}={valor!r}")
    return valor


def _escolha_opcional(dados: dict, campo: str, opcoes: tuple[str, ...]):
    if dados.get(campo) is None:
        return None
    return _escolha(dados, campo, opcoes)


def _confianca(valor) -> float:
    numero = isinstance(valor, (int, float)) and not isinstance(valor, bool)
    if not numero or not 0.0 <= valor <= 1.0:
        raise _invalida(f"confianca={valor!r}")
    return float(valor)


def _tarefas(valor) -> tuple[str, ...]:
    if not isinstance(valor, list) or not all(isinstance(t, str) for t in valor):
        raise _invalida("tarefas deve ser lista de textos")
    return tuple(t.strip() for t in valor if t.strip())


def _invalida(motivo: str) -> TranscriptionError:
    return TranscriptionError("groq", f"classificação inválida: {motivo}")


SYSTEM_PROMPT = """\
Você classifica falas transcritas do Raul, em português do Brasil. Ele NÃO \
avisa que é um prompt: decida pela INTENÇÃO da fala, não por palavras-chave. \
Nunca responda à fala; só classifique.

TIPOS
- "comando": a fala PEDE UMA AÇÃO a uma IA (mudar, criar, corrigir, \
analisar, olhar, revisar). Sinais: imperativo ("faz", "troca", "dá uma \
olhada"); desejo ("gostaria que", "quero que", "preciso que"); relato de \
contexto seguido de pedido.
- "duvida": a fala SÓ quer uma explicação e não pede mudança nenhuma ("o \
que é", "como funciona", "por que", "qual a diferença", "vale a pena").
- "ditado": o texto é PARA OUTRA PESSOA ou documento (saudação, vocativo, \
assinatura, tom de mensagem).

DESEMPATE, nesta ordem
1. Pedido prevalece: dúvida + pedido de ação é "comando".
2. App em foco (bundle id): com.microsoft.VSCode, com.apple.Terminal, \
com.anthropic.claudefordesktop favorecem "comando"/"duvida"; com.apple.mail, \
net.whatsapp.WhatsApp, com.apple.MobileSMS, com.microsoft.Word, \
com.apple.iWork.Pages favorecem "ditado". Navegador é neutro.
3. Fala longa com vários assuntos ("e outra coisa...") é "comando" com \
várias tarefas: uma por pedido distinto. Contexto sem pedido não é tarefa. \
"Dá uma olhada em X" que só aponta onde estão os pedidos já ditos não é \
tarefa a mais.

MODELO E ESFORÇO (só para "comando"; senão null)
- opus/medium: visual (imagem anexada, layout, tela, página, design, print) \
ou arquitetura ("define", "arquitetura", "como vai funcionar", schema, \
integração).
- sonnet/high: bug difícil, vários arquivos, "não sei por que".
- sonnet/medium: funcionalidade nova, testes, documentação. É o padrão.
- sonnet/low: correção pontual, um arquivo.
- haiku/low: renomear, formatar, mover, apagar.
- haiku/medium: texto ou código pequeno e repetitivo.
Haiku é só para trabalho MECÂNICO, que não muda o comportamento do sistema. \
"Trocar" um componente, uma tecla ou uma regra muda comportamento: não é \
mecânico.
Na dúvida entre duas classes, escolha a de MAIOR capacidade.

RESPOSTA: só um objeto JSON, sem texto fora dele:
{"tipo": "comando"|"duvida"|"ditado", "modelo": "opus"|"sonnet"|"haiku"|null, \
"esforco": "low"|"medium"|"high"|null, "confianca": número de 0 a 1, \
"tarefas": [cada pedido em uma frase imperativa curta]}
Para "duvida" e "ditado", "tarefas" é [].
"""

# Contexto + dois pedidos + "olha lá": o "olha lá" só aponta onde estão os
# pedidos. Sem este exemplo o gpt-oss contava 3 tarefas em ~50% das vezes
# (medido em 23/10). Conteúdo diferente dos casos de teste de propósito.
EXEMPLO = (
    {"role": "user", "content": _mensagem(
        "Eu mexi no config porque quero que o log fique mais curto. E outra "
        "coisa, queria que o backup rodasse toda noite... então olha lá no "
        "config.yml", False, None,
    )},
    {"role": "assistant", "content": json.dumps({
        "tipo": "comando", "modelo": "sonnet", "esforco": "medium",
        "confianca": 0.9,
        "tarefas": [
            "Encurtar o log conforme o config.yml",
            "Agendar o backup para rodar toda noite",
        ],
    }, ensure_ascii=False)},
)
