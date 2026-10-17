# SagmoWhisper

Ditado por voz global (tecla de gravação → Whisper Groq → limpeza → cola no cursor), Python 3.11, macOS e Ubuntu.
A tecla está migrando de F8 para segurar o Control direito (DEC-PV-009).
Épico em andamento: **Ponte de Voz** — ler `docs/ponte-de-voz/README.md` antes de qualquer tarefa dele.

## Regras

- TDD obrigatório: teste RED primeiro, mostrar a falha, depois o mínimo para passar.
- Ruff com complexidade ≤ 4: `ruff check src tests`.
- Testes: `pytest`. Testes que chamam APIs reais são opt-in: `pytest -m groq_live --no-cov`.
- Não inventar regra de negócio: o que não estiver em `docs/ponte-de-voz/` deve ser perguntado ao Raul.
- Chaves de API só via `src/core/secrets.py`. Nunca em arquivo versionado.
- Um item do ROADMAP por PR. Atualizar `docs/ponte-de-voz/STATUS.md` ao final (curto).
- Depois de merge que muda o app: rebuild com `./install.sh` (exige reconceder permissões de
  Acessibilidade e Monitoramento de Entrada no macOS).

## Leitura sob demanda

- `docs/STATUS.md` tem 630 linhas de histórico: não ler inteiro; consultar só se o Raul pedir.
