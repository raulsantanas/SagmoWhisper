# STATUS — SagmoWhisper

> Só o estado atual. O diário antigo (até 2026-10-17) está no git: `git log -p -- docs/STATUS.md`.

**Atualizado:** 2026-10-23

| # | Task | Critério de aceite | Status |
|---|------|---------------------|--------|
| — | Limpeza Groq: modelo vivo | Limpeza usa `openai/gpt-oss-120b` (único liberado na org); modelos removidos migram sozinhos | DONE (#35) |
| — | Interface "de assistente" | Indicador (#36, #37), ícone+menu (#38) e Configurações escuras (#39). Ajuste futuro: onda um pouco lenta (Raul, 17/10) | DONE |
| 1.3 | Aprender correção nas Configurações | Grupo Correções: "Quando ouvir" → "Escrever" grava em `correcoes.json` e vale sem reiniciar | DONE |
| 1.2 | Correções pós-transcrição | "cloud code"→Claude Code, "Rhythm.md"→README.md, "Claudio Code"→Claude Code; palavra inteira; `~/.sagmowhisper/correcoes.json` soma pares | DONE (#41) |
| 1.1 | Glossário no Whisper | Termos vão no `prompt` da Groq (≤ 224 tokens); `~/.sagmowhisper/glossario.json` soma termos ao inicial | DONE (#40) |
| 1.0 | Ponte de Voz: tecla F8 → segurar Control direito | Segurar sozinho grava; combinação ou toque < 0,3 s descarta; Control esquerdo nunca grava; F8 aceito | DONE (#34) |

**Próxima:** 1.4 (registro de treino em `decisoes.jsonl`), quando o Raul aprovar.
**Limite da Groq (free tier):** 8000 tokens/min no `gpt-oss-120b`; cada limpeza gasta ~700.
**Suíte:** 349 passed / 0 falhas
