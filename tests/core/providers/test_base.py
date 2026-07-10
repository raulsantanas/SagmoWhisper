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


def test_gate_com_prompt_seleciona_system_prompt():
    msgs = cleanup_messages("isso aqui é um prompt de teste qualquer")
    assert msgs[0] == {
        "role": "system", "content": base.CLEANUP_SYSTEM_PROMPT_PROMPT
    }


def test_gate_ignora_caixa_ao_selecionar_system():
    alto = cleanup_messages("escreva o PROMPT de teste")
    misto = cleanup_messages("escreva o Prompt de teste")
    baixo = cleanup_messages("escreva o prompt de teste")
    esperado = {"role": "system", "content": base.CLEANUP_SYSTEM_PROMPT_PROMPT}
    assert alto[0] == misto[0] == baixo[0] == esperado


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
