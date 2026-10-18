"""Troca, depois da transcrição, o que o Whisper erra sempre igual (ROADMAP 1.2).

Só palavra inteira: "cloud code" vira Claude Code, "cloudflare" fica como está."""
import re
from pathlib import Path

from src.core.dados_usuario import PASTA_DADOS, erro_no_arquivo, ler_json

CORRECOES_INICIAIS = {
    "cloud code": "Claude Code",
    "rhythm.md": "README.md",
    # Decisão de 18/10: só com "Code"; um Cláudio de verdade fica intocado.
    "claudio code": "Claude Code",
    "cláudio code": "Claude Code",
}
CAMINHO_PADRAO = PASTA_DADOS / "correcoes.json"


def aplicar(texto: str, correcoes: dict[str, str]) -> str:
    if not correcoes:
        return texto
    por_chave = {errado.lower(): certo for errado, certo in correcoes.items()}
    # Chaves longas primeiro: "cloud code" vence "cloud".
    chaves = sorted(por_chave, key=len, reverse=True)
    padrao = r"(?<!\w)(" + "|".join(map(re.escape, chaves)) + r")(?!\w)"
    return re.sub(
        padrao, lambda m: por_chave[m.group(0).lower()], texto,
        flags=re.IGNORECASE,
    )


def carregar_correcoes(caminho: Path | None = None) -> dict[str, str]:
    """Lido a cada montagem do pipeline (abrir o app ou salvar Configurações)."""
    caminho = CAMINHO_PADRAO if caminho is None else caminho
    if not caminho.exists():
        return dict(CORRECOES_INICIAIS)
    return {**CORRECOES_INICIAIS, **_pares_do_arquivo(caminho)}


def _pares_do_arquivo(caminho: Path) -> dict[str, str]:
    dados = ler_json(caminho, "correcoes")
    if not isinstance(dados, dict) or not all(map(_par_valido, dados.items())):
        raise erro_no_arquivo(
            caminho, "correcoes", 'esperado {"errado": "certo", ...}'
        )
    return {errado.strip().lower(): certo for errado, certo in dados.items()}


def _par_valido(par) -> bool:
    return all(isinstance(lado, str) and lado.strip() for lado in par)


class TranscriberCorrigido:
    def __init__(self, original, correcoes: dict[str, str]):
        self.original = original
        self._correcoes = correcoes

    def transcribe(self, audio_path: Path) -> str:
        return aplicar(self.original.transcribe(audio_path), self._correcoes)
