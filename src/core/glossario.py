"""Termos que o Whisper deve escrever certo ("Claude", não "cloud").

Vão no parâmetro `prompt` da transcrição (ROADMAP 1.1)."""
import json
from pathlib import Path

GLOSSARIO_INICIAL = (
    "Claude", "Anthropic", "Claude Code", "README", "Laya", "Groq", "Sagmo",
    "NeuroEnf",
)
CAMINHO_PADRAO = Path.home() / ".sagmowhisper" / "glossario.json"
# A Groq limita o prompt do Whisper a 224 tokens. Sem tokenizer local,
# contamos 2 caracteres por token: pior caso razoável para nomes próprios.
LIMITE_CARACTERES = 448
_SEPARADOR = ", "


def montar_prompt(termos) -> str:
    prompt = ""
    for termo in termos:
        candidato = f"{prompt}{_SEPARADOR}{termo}" if prompt else termo
        if len(candidato) > LIMITE_CARACTERES:
            break
        prompt = candidato
    return prompt


def carregar_termos(caminho: Path | None = None) -> tuple[str, ...]:
    caminho = CAMINHO_PADRAO if caminho is None else caminho
    if not caminho.exists():
        return GLOSSARIO_INICIAL
    termos = json.loads(caminho.read_text()).get("termos")
    if not isinstance(termos, list):
        raise ValueError(f'{caminho.name}: esperado {{"termos": [...]}}')
    return tuple(str(t) for t in termos)
