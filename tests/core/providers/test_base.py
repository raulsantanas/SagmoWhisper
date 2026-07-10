from src.core.providers.base import (
    CLEANUP_EXAMPLES,
    CLEANUP_EXAMPLES_PROMPT,
    CLEANUP_SYSTEM_PROMPT,
    PROVIDER_CATALOG,
    TranscriptionError,
    cleanup_messages,
)


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
    assert info.cleanup_models == ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
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


def test_cleanup_messages_comeca_no_system_e_termina_no_texto_bruto():
    messages = cleanup_messages("texto bruto")
    assert messages[0] == {"role": "system", "content": CLEANUP_SYSTEM_PROMPT}
    assert messages[-1] == {"role": "user", "content": "texto bruto"}


def test_cleanup_messages_tem_exemplo_de_pergunta_nao_respondida():
    messages = cleanup_messages("qualquer coisa")
    exemplos = [
        (messages[i], messages[i + 1])
        for i in range(1, len(messages) - 1, 2)
    ]
    assert len(exemplos) >= 2
    perguntas = [
        (u, a) for u, a in exemplos if a["content"].strip().endswith("?")
    ]
    assert perguntas, "precisa de exemplo em que a pergunta continua pergunta"
    u, a = perguntas[0]
    assert u["role"] == "user" and a["role"] == "assistant"
    assert "capital" in u["content"] and "capital" in a["content"]


def test_system_prompt_define_dois_registros_e_proibe_responder():
    prompt = CLEANUP_SYSTEM_PROMPT
    assert "escreva/atualize/melhore o prompt" in prompt.lower()  # comando
    assert "whatsapp" in prompt.lower()  # registro MENSAGEM
    assert "NUNCA RESPONDER" in prompt
    assert "bullets" in prompt.lower()


def test_exemplo_com_gatilho_remove_o_comando_da_saida():
    com_gatilho = [
        (u, a) for u, a in CLEANUP_EXAMPLES_PROMPT
        if u.startswith("escreva o prompt")
    ]
    assert com_gatilho, "precisa de exemplo few-shot do registro PROMPT"
    _, saida = com_gatilho[0]
    assert "escreva o prompt" not in saida.lower()
    assert "\n- " in saida  # saída estruturada em bullets


def test_exemplo_de_enumeracao_vira_bullets():
    bullets = [a for _, a in CLEANUP_EXAMPLES if a.count("\n- ") >= 2]
    assert bullets, "precisa de exemplo de enumeração ditada virando bullets"


def test_exemplo_real_de_mensagem_longa_preserva_a_pergunta():
    helena = [(u, a) for u, a in CLEANUP_EXAMPLES if "helena" in u]
    assert helena, "precisa do caso real da mensagem da Helena como âncora"
    ditado, saida = helena[0]
    assert "?" not in ditado and "?" in saida
    assert "matrículas" in saida and "evasão" in saida


def test_ditado_sem_prompt_nao_inclui_exemplos_gateados():
    msgs = cleanup_messages("oi tudo bem me liga depois")
    esperado = 1 + 2 * len(CLEANUP_EXAMPLES) + 1
    assert len(msgs) == esperado
    conteudos = [m["content"] for m in msgs]
    for entrada, _ in CLEANUP_EXAMPLES_PROMPT:
        assert entrada not in conteudos


def test_ditado_com_prompt_inclui_exemplos_gateados():
    msgs = cleanup_messages("isso seria um prompt teste qualquer")
    esperado = 1 + 2 * (len(CLEANUP_EXAMPLES) + len(CLEANUP_EXAMPLES_PROMPT)) + 1
    assert len(msgs) == esperado


def test_gate_ignora_caixa():
    msgs_maiusculo = cleanup_messages("escreva o Prompt de teste")
    msgs_minusculo = cleanup_messages("escreva o prompt de teste")
    assert len(msgs_maiusculo) == len(msgs_minusculo)


def test_system_prompt_dispara_com_qualquer_mencao_a_palavra_prompt():
    prompt = CLEANUP_SYSTEM_PROMPT
    assert "QUALQUER menção" in prompt
    # regra antiga ("'prompt' como assunto não dispara") não pode sobreviver
    assert "apenas assunto" not in prompt


def test_system_prompt_estrutura_prompts_compostos_com_tags_xml():
    prompt = CLEANUP_SYSTEM_PROMPT
    assert "<contexto>" in prompt
    assert "<tarefas>" in prompt
    assert "<restricoes>" in prompt


def test_exemplo_composto_usa_tags_xml_no_prompt_gerado():
    flask = [(u, a) for u, a in CLEANUP_EXAMPLES_PROMPT if "flask" in u]
    assert flask, "precisa do exemplo composto (Flask) como âncora"
    _, saida = flask[0]
    assert "<contexto>" in saida and "</contexto>" in saida
    assert "<tarefas>" in saida and "</tarefas>" in saida
    assert "<restricoes>" in saida and "</restricoes>" in saida


def test_mencao_casual_a_prompt_vira_prompt_e_nao_conversa():
    mencao = [
        (u, a) for u, a in CLEANUP_EXAMPLES_PROMPT
        if not u.startswith("escreva o prompt") and "esqueci" not in u
    ]
    assert mencao, "precisa de exemplo de menção casual à palavra prompt"
    ditado, saida = mencao[0]
    assert "prompt" in ditado
    assert not saida.lower().startswith("ei")
    # a moldura ("preciso de um prompt...") sai; fica só o prompt em si
    assert "preciso" not in saida.lower()


def test_nenhum_exemplo_gateado_sai_como_mensagem_de_conversa():
    for _, saida in CLEANUP_EXAMPLES_PROMPT:
        assert not saida.startswith("Ei, Bruno")


def test_system_prompt_lista_melhore_como_comando_de_moldura():
    # Bug real (2026-07-07): "melhora esse prompt e analisa..." virou
    # meta-prompt ("Melhore o prompt fornecido" como objetivo e tarefa 1).
    assert "escreva/atualize/melhore" in CLEANUP_SYSTEM_PROMPT.lower()


def test_system_prompt_proibe_prompt_sobre_outro_prompt():
    assert "NUNCA um prompt para criar ou melhorar outro prompt" in (
        CLEANUP_SYSTEM_PROMPT
    )


def test_exemplo_melhore_remove_moldura_e_nao_vira_meta_prompt():
    melhore = [
        (u, a) for u, a in CLEANUP_EXAMPLES_PROMPT if u.startswith("melhora")
    ]
    assert melhore, "precisa de exemplo few-shot com o comando 'melhora'"
    _, saida = melhore[0]
    # a saída é o prompt final sobre o conteúdo — a palavra "prompt" e o
    # verbo da moldura não podem sobrar nela
    assert "prompt" not in saida.lower()
    assert "melhor" not in saida.lower().split("\n")[0]


def test_system_prompt_sempre_completo_e_primeiro():
    msgs = cleanup_messages("qualquer coisa")
    assert msgs[0] == {"role": "system", "content": CLEANUP_SYSTEM_PROMPT}
    assert "1) PROMPT" in CLEANUP_SYSTEM_PROMPT


def test_ultima_mensagem_e_o_ditado_do_usuario():
    msgs = cleanup_messages("meu ditado")
    assert msgs[-1] == {"role": "user", "content": "meu ditado"}
