import json
from pathlib import Path

import pytest

from src.core import glossario
from src.core.providers.base import TranscriptionError
from src.core.glossario import (
    GLOSSARIO_INICIAL,
    LIMITE_CARACTERES,
    carregar_termos,
    montar_prompt,
)


def test_glossario_inicial_tem_os_termos_do_roadmap():
    for termo in ("Claude", "Anthropic", "Claude Code", "README", "Laya",
                  "Groq", "Sagmo", "NeuroEnf"):
        assert termo in GLOSSARIO_INICIAL


def test_prompt_lista_os_termos_separados_por_virgula():
    assert montar_prompt(("Claude", "README")) == "Claude, README"


def test_prompt_nunca_passa_do_limite_e_nao_corta_termo_ao_meio():
    termos = tuple(f"Termo{i:04d}" for i in range(500))
    prompt = montar_prompt(termos)

    assert len(prompt) <= LIMITE_CARACTERES
    assert all(parte in termos for parte in prompt.split(", "))


def test_limite_cabe_em_224_tokens_mesmo_no_pior_caso_razoavel():
    # Groq: prompt do Whisper "limited to 224 tokens". Contando ~2
    # caracteres por token (pior caso para nomes próprios), sobra margem.
    assert LIMITE_CARACTERES <= 224 * 2


def test_sem_arquivo_usa_glossario_inicial(tmp_path):
    assert carregar_termos(tmp_path / "nao_existe.json") == GLOSSARIO_INICIAL


def test_arquivo_do_raul_substitui_o_inicial(tmp_path):
    caminho = tmp_path / "glossario.json"
    caminho.write_text(json.dumps({"termos": ["Claude", "Hostinger"]}))

    assert carregar_termos(caminho) == ("Claude", "Hostinger")


@pytest.mark.parametrize(
    "conteudo",
    ['{"termos": "Claude"}', '{"termos": ["Claude",]}', '["Claude"]', "\xff"],
)
def test_arquivo_invalido_vira_erro_que_o_app_mostra(tmp_path, conteudo):
    caminho = tmp_path / "glossario.json"
    caminho.write_bytes(conteudo.encode("latin-1"))

    with pytest.raises(TranscriptionError, match="glossario.json"):
        carregar_termos(caminho)


def test_ignora_termos_vazios_repetidos_e_que_nao_sao_texto(tmp_path):
    caminho = tmp_path / "glossario.json"
    caminho.write_text('{"termos": ["Claude", null, "", " ", "Claude", 3, "Groq"]}')

    assert carregar_termos(caminho) == ("Claude", "Groq")


def test_pasta_de_dados_e_a_da_arquitetura():
    assert glossario.PASTA_DADOS == Path.home() / ".sagmowhisper"
