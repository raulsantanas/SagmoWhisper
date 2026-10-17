# STATUS — SagmoWhisper

> Só o estado atual. O diário antigo (até 2026-10-17) está no git: `git log -p -- docs/STATUS.md`.

**Atualizado:** 2026-10-17

| # | Task | Critério de aceite | Status |
|---|------|---------------------|--------|
| — | Limpeza Groq: modelo vivo | Limpeza usa `openai/gpt-oss-120b` (único liberado na org); modelos removidos migram sozinhos | DONE (#35) |
| — | Interface "de assistente" | Indicador com ondas (PR 1); depois ícone+menu (PR 2) e Configurações (PR 3) | EM ANDAMENTO |
| 1.0 | Ponte de Voz: tecla F8 → segurar Control direito | Segurar sozinho grava; combinação ou toque < 0,3 s descarta; Control esquerdo nunca grava; F8 aceito | DONE (#34) |

**Próxima:** 1.1 (glossário no Whisper), quando o Raul aprovar.
**Limite da Groq (free tier):** 8000 tokens/min no `gpt-oss-120b`; cada limpeza gasta ~700.
**Suíte:** 281 passed / 0 falhas
