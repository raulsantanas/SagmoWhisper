import re

import pytest

from src.core.providers import base
from src.core.providers.base import (
    CLEANUP_EXAMPLES,
    CLEANUP_EXAMPLES_PROMPT,
    PROVIDER_CATALOG,
    TranscriptionError,
    cleanup_messages,
)


def _pares(msgs):
    """Extrai os pares (user, assistant) few-shot do miolo das mensagens."""
    return [(msgs[i], msgs[i + 1]) for i in range(1, len(msgs) - 1, 2)]


# --------------------------------------------------------------------------
# Catálogo e erro tipado — inalterados pelo novo contrato
# --------------------------------------------------------------------------


def test_error_expoe_provider_e_detail():
    err = TranscriptionError("groq", "401 invalid key")
    assert err.provider == "groq"
    assert err.detail == "401 invalid key"
    assert str(err) == "groq: 401 invalid key"


def test_catalogo_tem_os_tres_providers():
    assert set(PROVIDER_CATALOG) == {"groq", "openai", "local"}
    assert [PROVIDER_CATALOG[k].label for k in ("groq", "openai", "local")] == [
        "Groq", "OpenAI", "Local"
    ]


def test_modelos_groq_verbatim_do_spec():
    info = PROVIDER_CATALOG["groq"]
    assert info.transcription_models == (
        "whisper-large-v3-turbo", "whisper-large-v3"
    )
    assert info.cleanup_models == ("llama-3.3-70b-versatile",)
    assert info.needs_api_key is True


def test_modelos_openai_verbatim_do_spec():
    info = PROVIDER_CATALOG["openai"]
    assert info.transcription_models == ("whisper-1", "gpt-4o-transcribe")
    assert info.cleanup_models == ("gpt-4o-mini",)
    assert info.needs_api_key is True


def test_local_sem_key_e_sem_limpeza():
    info = PROVIDER_CATALOG["local"]
    assert info.transcription_models == ("small",)
    assert info.cleanup_models == ()
    assert info.needs_api_key is False


# --------------------------------------------------------------------------
# Gate em código seleciona o SYSTEM PROMPT do registro (decisão 100% em código)
# --------------------------------------------------------------------------


def test_gate_sem_prompt_seleciona_system_mensagem():
    msgs = cleanup_messages("oi tudo bem me liga depois")
    assert msgs[0] == {
        "role": "system", "content": base.CLEANUP_SYSTEM_PROMPT_MENSAGEM
    }


# --------------------------------------------------------------------------
# Contrato novo do GATILHO: o registro PROMPT dispara APENAS com comando
# explícito dirigido ao editor ou meta-declaração — nunca por qualquer menção
# à palavra "prompt". Ditados reais do log do app são as âncoras.
# --------------------------------------------------------------------------

# Comando dirigido ao editor (verbo de criação/melhoria + "prompt") ou
# meta-declaração (demonstrativo + "é um prompt" no presente).
DITADOS_QUE_DISPARAM_PROMPT = [
    # --- meta-declaração (demonstrativo + "é um prompt" no presente) ---
    "Isso é um prompt. Será que você vai conseguir identificar? Eu quero "
    "que você gere um relatório final e um PR final sobre tudo que foi feito.",
    "isso aqui é um prompt: preciso que você organize os arquivos csv de "
    "clientes",
    "isto é um prompt para gerar um resumo do artigo",
    "esse texto é um prompt de teste do editor",
    # --- comando dirigido ao editor (verbo + "prompt" na mesma oração) ---
    "escreva o prompt a gente tem uma api em rails e o endpoint de "
    "relatórios está lento",
    "melhora esse prompt e analisa o código final se existe alguma falha "
    "de segurança",
    "aprimora esse prompt. Eu não entendi absolutamente nada do que você fez",
    "quero um prompt pra gerar três posts de instagram sobre café coado",
    "A página não está abrindo, melhore o prompt para corrigir isso",
    "crie um prompt pra organizar a agenda da semana",
    "preciso de um prompt pra revisar o meu código",
    "atualize esse prompt pra incluir o passo de deploy",
    # verbo DEPOIS da palavra ("um prompt, melhore ele")
    "um prompt, melhore ele pra ficar mais objetivo",
]

# Contêm "prompt" (ou não), mas NÃO são comando/meta-declaração no presente:
# meta-fala sobre prompts, verbo em 3ª pessoa, reclamação, ou sem a palavra.
DITADOS_QUE_NAO_DISPARAM_PROMPT = [
    "Esse texto, entre chaves, era um prompt. Eu ainda avisei, é um prompt. "
    "E ele não gerou bullet points, não gerou a estrutura que a Antropik "
    "diz que tem que fazer, não fez nada disso.",
    "se eu falar alguma palavra com prompt e ele gera um prompt aleatório "
    "em vez de ser o ponto em cima do texto que eu estou falando",
    "o prompt não funcionou nada do que eu pedi",
    "Qual LLM estamos utilizando além da LLM de voz?",
    "vou usar o login do google como login do admin",
]


@pytest.mark.parametrize("ditado", DITADOS_QUE_DISPARAM_PROMPT)
def test_predicado_dispara_registro_prompt(ditado):
    assert base.prompt_register_triggered(ditado) is True


@pytest.mark.parametrize("ditado", DITADOS_QUE_NAO_DISPARAM_PROMPT)
def test_predicado_nao_dispara_registro_prompt(ditado):
    assert base.prompt_register_triggered(ditado) is False


@pytest.mark.parametrize("ditado", DITADOS_QUE_DISPARAM_PROMPT)
def test_cleanup_messages_seleciona_system_prompt_quando_dispara(ditado):
    msgs = cleanup_messages(ditado)
    assert msgs[0] == {
        "role": "system", "content": base.CLEANUP_SYSTEM_PROMPT_PROMPT
    }


@pytest.mark.parametrize("ditado", DITADOS_QUE_NAO_DISPARAM_PROMPT)
def test_cleanup_messages_seleciona_system_mensagem_quando_nao_dispara(ditado):
    msgs = cleanup_messages(ditado)
    assert msgs[0] == {
        "role": "system", "content": base.CLEANUP_SYSTEM_PROMPT_MENSAGEM
    }


def test_predicado_dispara_ignora_caixa():
    for variante in ("escreva o PROMPT de teste",
                     "Escreva o Prompt de teste",
                     "escreva o prompt de teste"):
        assert base.prompt_register_triggered(variante) is True


# --------------------------------------------------------------------------
# Gate seleciona os EXEMPLOS de forma exclusiva por registro
# (PROMPT → só CLEANUP_EXAMPLES_PROMPT; MENSAGEM → só CLEANUP_EXAMPLES)
# --------------------------------------------------------------------------


def test_registro_mensagem_usa_apenas_exemplos_de_mensagem():
    msgs = cleanup_messages("bom dia preciso confirmar a reunião de amanhã")
    assert msgs[0]["content"] == base.CLEANUP_SYSTEM_PROMPT_MENSAGEM
    assert len(msgs) == 1 + 2 * len(CLEANUP_EXAMPLES) + 1
    pares = [(u["content"], a["content"]) for u, a in _pares(msgs)]
    assert pares == list(CLEANUP_EXAMPLES)
    conteudos = [m["content"] for m in msgs]
    for entrada, _ in CLEANUP_EXAMPLES_PROMPT:
        assert entrada not in conteudos


def test_registro_prompt_usa_apenas_exemplos_de_prompt():
    msgs = cleanup_messages("quero um prompt pra gerar posts de instagram")
    assert msgs[0]["content"] == base.CLEANUP_SYSTEM_PROMPT_PROMPT
    assert len(msgs) == 1 + 2 * len(CLEANUP_EXAMPLES_PROMPT) + 1
    pares = [(u["content"], a["content"]) for u, a in _pares(msgs)]
    assert pares == list(CLEANUP_EXAMPLES_PROMPT)
    conteudos = [m["content"] for m in msgs]
    for entrada, _ in CLEANUP_EXAMPLES:
        assert entrada not in conteudos


# --------------------------------------------------------------------------
# Estrutura das mensagens: system primeiro, ditado por último, pares no meio
# --------------------------------------------------------------------------


def test_cleanup_messages_system_primeiro_e_ditado_por_ultimo():
    msgs = cleanup_messages("um ditado qualquer sem gatilho")
    assert msgs[0]["role"] == "system"
    assert msgs[-1] == {"role": "user", "content": "um ditado qualquer sem gatilho"}


def test_cleanup_messages_miolo_alterna_user_assistant():
    msgs = cleanup_messages("me manda o relatório por favor")
    meio = msgs[1:-1]
    assert meio and len(meio) % 2 == 0
    for i in range(0, len(meio), 2):
        assert meio[i]["role"] == "user"
        assert meio[i + 1]["role"] == "assistant"


# --------------------------------------------------------------------------
# Conteúdo obrigatório de CADA system prompt
# --------------------------------------------------------------------------


def test_ambos_system_prompts_tem_regra_suprema():
    for prompt in (
        base.CLEANUP_SYSTEM_PROMPT_MENSAGEM,
        base.CLEANUP_SYSTEM_PROMPT_PROMPT,
    ):
        assert "REGRA SUPREMA" in prompt
        assert "NUNCA RESPONDER" in prompt


def test_ambos_system_prompts_tem_formato_da_resposta():
    for prompt in (
        base.CLEANUP_SYSTEM_PROMPT_MENSAGEM,
        base.CLEANUP_SYSTEM_PROMPT_PROMPT,
    ):
        assert "FORMATO DA RESPOSTA" in prompt


def test_system_mensagem_descreve_registro_whatsapp():
    prompt = base.CLEANUP_SYSTEM_PROMPT_MENSAGEM.lower()
    assert "whatsapp" in prompt
    assert "bullets" in prompt


def test_system_mensagem_texto_curto_volta_identico():
    assert "idêntico" in base.CLEANUP_SYSTEM_PROMPT_MENSAGEM.lower()


def test_system_mensagem_nao_menciona_o_registro_prompt():
    prompt = base.CLEANUP_SYSTEM_PROMPT_MENSAGEM.casefold()
    assert "prompt" not in prompt
    assert "<contexto>" not in prompt


def test_system_prompt_estrutura_composto_com_tags_xml():
    prompt = base.CLEANUP_SYSTEM_PROMPT_PROMPT
    assert "<contexto>" in prompt
    assert "<tarefas>" in prompt
    assert "<restricoes>" in prompt


def test_system_prompt_assume_o_registro_de_forma_imperativa():
    prompt = base.CLEANUP_SYSTEM_PROMPT_PROMPT.casefold()
    assert "é um prompt" in prompt
    assert "imperativ" in prompt


def test_system_prompt_proibe_meta_prompt():
    prompt = base.CLEANUP_SYSTEM_PROMPT_PROMPT.casefold()
    assert "criar ou melhorar outro prompt" in prompt
    assert "melhore o prompt" in prompt


def test_system_prompt_sem_linguagem_condicional_de_disparo():
    # A decisão do registro já foi tomada em código; o system prompt do
    # registro PROMPT não pode conter a lógica de gatilho condicional.
    prompt = base.CLEANUP_SYSTEM_PROMPT_PROMPT.casefold()
    assert "dispara" not in prompt
    assert "qualquer menção" not in prompt


def test_system_prompt_nao_descreve_o_registro_mensagem():
    assert "whatsapp" not in base.CLEANUP_SYSTEM_PROMPT_PROMPT.casefold()


def test_constante_antiga_de_prompt_unico_foi_removida():
    # CLEANUP_SYSTEM_PROMPT (prompt único que delegava o registro ao LLM)
    # deixa de existir no novo contrato.
    assert not hasattr(base, "CLEANUP_SYSTEM_PROMPT")


# --------------------------------------------------------------------------
# Few-shots (constantes) — âncoras de comportamento de cada registro
# --------------------------------------------------------------------------


def test_exemplo_real_de_mensagem_longa_preserva_a_pergunta():
    helena = [(u, a) for u, a in CLEANUP_EXAMPLES if "helena" in u]
    assert helena, "precisa do caso real da mensagem da Helena como âncora"
    ditado, saida = helena[0]
    assert "?" not in ditado and "?" in saida
    assert "matrículas" in saida and "evasão" in saida


def test_exemplo_de_enumeracao_vira_bullets():
    bullets = [a for _, a in CLEANUP_EXAMPLES if a.count("\n- ") >= 2]
    assert bullets, "precisa de exemplo de enumeração ditada virando bullets"


def test_exemplo_com_gatilho_remove_o_comando_da_saida():
    com_gatilho = [
        (u, a) for u, a in CLEANUP_EXAMPLES_PROMPT
        if u.startswith("escreva o prompt")
    ]
    assert com_gatilho, "precisa de exemplo few-shot do registro PROMPT"
    _, saida = com_gatilho[0]
    assert "escreva o prompt" not in saida.lower()
    assert "\n- " in saida  # saída estruturada em bullets


def test_exemplo_composto_usa_tags_xml_no_prompt_gerado():
    flask = [(u, a) for u, a in CLEANUP_EXAMPLES_PROMPT if "flask" in u]
    assert flask, "precisa do exemplo composto (Flask) como âncora"
    _, saida = flask[0]
    assert "<contexto>" in saida and "</contexto>" in saida
    assert "<tarefas>" in saida and "</tarefas>" in saida
    assert "<restricoes>" in saida and "</restricoes>" in saida


def test_exemplo_melhore_remove_moldura_e_nao_vira_meta_prompt():
    melhore = [
        (u, a) for u, a in CLEANUP_EXAMPLES_PROMPT if u.startswith("melhora")
    ]
    assert melhore, "precisa de exemplo few-shot com o comando 'melhora'"
    _, saida = melhore[0]
    assert "prompt" not in saida.lower()
    assert "melhor" not in saida.lower().split("\n")[0]


def test_mencao_casual_a_prompt_vira_prompt_e_nao_conversa():
    mencao = [
        (u, a) for u, a in CLEANUP_EXAMPLES_PROMPT
        if not u.startswith("escreva o prompt") and "esqueci" not in u
    ]
    assert mencao, "precisa de exemplo de menção casual à palavra prompt"
    ditado, saida = mencao[0]
    assert "prompt" in ditado
    assert "preciso" not in saida.lower()


def test_nenhum_exemplo_gateado_sai_como_mensagem_de_conversa():
    for _, saida in CLEANUP_EXAMPLES_PROMPT:
        assert not saida.startswith("Ei, Bruno")


# --------------------------------------------------------------------------
# Contrato novo: os DOIS conjuntos de few-shots respeitam o gate determinístico
# (todo exemplo PROMPT dispara; nenhum exemplo MENSAGEM dispara).
# --------------------------------------------------------------------------


def test_todo_exemplo_do_registro_prompt_dispara_o_gate():
    for entrada, _ in CLEANUP_EXAMPLES_PROMPT:
        assert base.prompt_register_triggered(entrada) is True, entrada


def test_nenhum_exemplo_do_registro_mensagem_dispara_o_gate():
    for entrada, _ in CLEANUP_EXAMPLES:
        assert base.prompt_register_triggered(entrada) is False, entrada


# --------------------------------------------------------------------------
# Contrato novo: ESTRUTURA SEMPRE. O system prompt do registro PROMPT perde a
# saída "curto: texto direto, sem tags"; havendo 2+ informações a saída é
# estruturada (objetivo imperativo + seções em tags XML), nunca parágrafo solto.
# --------------------------------------------------------------------------


def test_system_prompt_nao_oferece_saida_sem_estrutura():
    prompt = base.CLEANUP_SYSTEM_PROMPT_PROMPT.casefold()
    assert "texto direto" not in prompt
    assert "sem tags" not in prompt


def _tem_bullets(texto: str) -> bool:
    return "\n- " in texto or re.search(r"\n\d+\.\s", texto) is not None


@pytest.mark.parametrize("par", CLEANUP_EXAMPLES_PROMPT)
def test_exemplo_prompt_com_bullets_fica_dentro_de_tarefas(par):
    _, saida = par
    if _tem_bullets(saida):
        assert "<tarefas>" in saida and "</tarefas>" in saida


@pytest.mark.parametrize("par", CLEANUP_EXAMPLES_PROMPT)
def test_exemplo_prompt_primeira_linha_nao_dangla_dois_pontos(par):
    _, saida = par
    primeira_linha = saida.splitlines()[0].strip()
    assert primeira_linha
    assert not primeira_linha.endswith(":")
