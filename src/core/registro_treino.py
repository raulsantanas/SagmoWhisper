"""Uma linha por fala em treino/decisoes.jsonl (ROADMAP 1.4, ROTEAMENTO.md §3).

Material de treino do Laya na Fase 4. Até a Fase 2 não há classificador nem
app em foco: `decisao` e `app_em_foco` saem null."""
import json
import logging
from datetime import datetime
from pathlib import Path

from src.core.dados_usuario import PASTA_DADOS

logger = logging.getLogger("sagmowhisper")

CAMINHO_PADRAO = PASTA_DADOS / "treino" / "decisoes.jsonl"


def _agora() -> datetime:
    return datetime.now().astimezone()


class RegistroTreino:
    def __init__(self, caminho: Path | None = None, relogio=_agora):
        self._caminho = caminho
        self._relogio = relogio

    def registrar(self, texto_bruto: str, texto_corrigido: str) -> None:
        linha = {
            "ts": self._relogio().isoformat(timespec="seconds"),
            "app_em_foco": None,
            "texto_bruto": texto_bruto,
            "texto_corrigido": texto_corrigido,
            "decisao": None,
            "correcao_do_raul": None,
        }
        try:
            self._anexar(json.dumps(linha, ensure_ascii=False))
        except OSError:
            # Ditado não pode se perder por causa do registro.
            logger.exception("Falha ao gravar o registro de treino")

    def _anexar(self, linha: str) -> None:
        caminho = CAMINHO_PADRAO if self._caminho is None else self._caminho
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(linha + "\n")
