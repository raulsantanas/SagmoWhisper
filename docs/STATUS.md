# STATUS — SagmoWhisper

> Só o estado atual. O diário antigo (até 2026-10-17) está no git: `git log -p -- docs/STATUS.md`.

**Atualizado:** 2026-10-23

| # | Task | Critério de aceite | Status |
|---|------|---------------------|--------|
| — | Limpeza Groq: modelo vivo | Limpeza usa `openai/gpt-oss-120b` (único liberado na org); modelos removidos migram sozinhos | DONE (#35) |
| — | Interface "de assistente" | Indicador (#36, #37), ícone+menu (#38) e Configurações escuras (#39). Ajuste futuro: onda um pouco lenta (Raul, 17/10) | DONE |
| 2.5 | Responder dúvida em voz | Com provider Groq, toda fala passa pelo classificador; dúvida vira resposta de até 3 frases falada pela Francisca e nada é colado; ditado e comando colam como antes (+0,5–1,2 s). Falha cai no ditado (DEC-PV-012) | DONE |
| 2.3 | Voz Francisca (Edge TTS) | `VozEdge.falar()` volta na hora e toca em fila (afplay); apertar a tecla de gravação corta a fala em ~5 ms. Síntese leva ~2 s por frase (internet) | DONE (#46) |
| 2.2 | Classificador de intenção | `ClassificadorGroq` acerta os 6 casos do ROTEAMENTO §1 e o caso README sai com 2 tarefas (`pytest -m groq_live`, estável em 3 rodadas). Ligado ao app na 2.5 | DONE (#45) |
| 2.1 | App em foco | `app_em_foco()` devolve o bundle id do app na frente no macOS (DEC-PV-011); `None` no Linux | DONE (#44) |
| 1.4 | Registro de treino | Cada fala não vazia vira uma linha em `~/.sagmowhisper/treino/decisoes.jsonl` (`decisao` null até a Fase 2) | DONE (#43) |
| 1.3 | Aprender correção nas Configurações | Grupo Correções: "Quando ouvir" → "Escrever" grava em `correcoes.json` e vale sem reiniciar | DONE (#42) |
| 1.2 | Correções pós-transcrição | "cloud code"→Claude Code, "Rhythm.md"→README.md, "Claudio Code"→Claude Code; palavra inteira; `~/.sagmowhisper/correcoes.json` soma pares | DONE (#41) |
| 1.1 | Glossário no Whisper | Termos vão no `prompt` da Groq (≤ 224 tokens); `~/.sagmowhisper/glossario.json` soma termos ao inicial | DONE (#40) |
| 1.0 | Ponte de Voz: tecla F8 → segurar Control direito | Segurar sozinho grava; combinação ou toque < 0,3 s descarta; Control esquerdo nunca grava; F8 aceito | DONE (#34) |

**Próxima:** 2.6 (ditado sem regressão) ou 2.4 (voz reserva Piper Faber), quando o Raul escolher. Reinstalar o app (TCC) depois do merge da 2.5.
**Limite da Groq (free tier):** 8000 tokens/min no `gpt-oss-120b`. Por fala: classificador ~1.030 + limpeza ~600 (ditado) ou resposta ~340 (dúvida) → ~5 falas/min. Unir classificação e limpeza numa chamada (DEC-PV-002) reduz isso.
**Suíte:** 409 passed / 0 falhas
