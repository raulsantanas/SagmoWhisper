"""Termos que o Whisper deve escrever certo ("Claude", não "cloud").

Vão no parâmetro `prompt` da transcrição (ROADMAP 1.1)."""
import json
from pathlib import Path

from src.core.providers.base import TranscriptionError

GLOSSARIO_INICIAL = (
    "Claude", "Anthropic", "Claude Code", "README", "Laya", "Groq", "Sagmo",
    "NeuroEnf", "Paula Thuany",
)
PASTA_DADOS = Path.home() / ".sagmowhisper"
CAMINHO_PADRAO = PASTA_DADOS / "glossario.json"
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
    """Lido a cada montagem do pipeline (abrir o app ou salvar Configurações)."""
    caminho = CAMINHO_PADRAO if caminho is None else caminho
    if not caminho.exists():
        return GLOSSARIO_INICIAL
    return _termos_validos([*GLOSSARIO_INICIAL, *_lista_de_termos(caminho)])


def _lista_de_termos(caminho: Path) -> list:
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except ValueError as e:
        raise _erro(caminho, f"JSON inválido ({e})") from e
    termos = dados.get("termos") if isinstance(dados, dict) else None
    if not isinstance(termos, list):
        raise _erro(caminho, 'esperado {"termos": [...]}')
    return termos


def _termos_validos(termos: list) -> tuple[str, ...]:
    limpos = (t.strip() for t in termos if isinstance(t, str))
    return tuple(dict.fromkeys(t for t in limpos if t))


def _erro(caminho: Path, motivo: str) -> TranscriptionError:
    return TranscriptionError("glossario", f"{caminho.name}: {motivo}")
