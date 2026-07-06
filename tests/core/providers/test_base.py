from src.core.providers.base import PROVIDER_CATALOG, TranscriptionError


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
    from src.core.providers.base import CLEANUP_SYSTEM_PROMPT, cleanup_messages

    messages = cleanup_messages("texto bruto")
    assert messages[0] == {"role": "system", "content": CLEANUP_SYSTEM_PROMPT}
    assert messages[-1] == {"role": "user", "content": "texto bruto"}


def test_cleanup_messages_tem_exemplo_de_pergunta_nao_respondida():
    from src.core.providers.base import cleanup_messages

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
    from src.core.providers.base import CLEANUP_SYSTEM_PROMPT

    prompt = CLEANUP_SYSTEM_PROMPT
    assert "escreva o " in prompt.lower()  # gatilho do registro PROMPT
    assert "whatsapp" in prompt.lower()  # registro MENSAGEM
    assert "NUNCA RESPONDER" in prompt
    assert "bullets" in prompt.lower()


def test_exemplo_com_gatilho_remove_o_comando_da_saida():
    from src.core.providers.base import CLEANUP_EXAMPLES

    com_gatilho = [
        (u, a) for u, a in CLEANUP_EXAMPLES
        if u.startswith("escreva o prompt")
    ]
    assert com_gatilho, "precisa de exemplo few-shot do registro PROMPT"
    _, saida = com_gatilho[0]
    assert "escreva o prompt" not in saida.lower()
    assert "\n- " in saida  # saída estruturada em bullets


def test_exemplo_de_enumeracao_vira_bullets():
    from src.core.providers.base import CLEANUP_EXAMPLES

    bullets = [a for _, a in CLEANUP_EXAMPLES if a.count("\n- ") >= 2]
    assert bullets, "precisa de exemplo de enumeração ditada virando bullets"


def test_exemplo_real_de_mensagem_longa_preserva_a_pergunta():
    from src.core.providers.base import CLEANUP_EXAMPLES

    rose = [(u, a) for u, a in CLEANUP_EXAMPLES if "rose" in u]
    assert rose, "precisa do caso real da mensagem da Rose como âncora"
    ditado, saida = rose[0]
    assert "?" not in ditado and "?" in saida
    assert "leads" in saida and "qualidade" in saida
