# STATUS — SagmoWhisper

> Só o estado atual. O diário antigo (até 2026-10-17) está no git: `git log -p -- docs/STATUS.md`.

**Atualizado:** 2026-10-23

| # | Task | Critério de aceite | Status |
|---|------|---------------------|--------|
| — | Limpeza Groq: modelo vivo | Limpeza usa `openai/gpt-oss-120b` (único liberado na org); modelos removidos migram sozinhos | DONE (#35) |
| — | Interface "de assistente" | Indicador (#36, #37), ícone+menu (#38) e Configurações escuras (#39). Ajuste futuro: onda um pouco lenta (Raul, 17/10) | DONE |
| 2.3 | Voz Francisca (Edge TTS) | `VozEdge.falar()` volta na hora e toca em fila (afplay); apertar a tecla de gravação corta a fala em ~5 ms. Síntese leva ~2 s por frase (internet). Nada fala ainda: quem chama é a 2.5 | DONE |
| 2.2 | Classificador de intenção | `ClassificadorGroq` acerta os 6 casos do ROTEAMENTO §1 e o caso README sai com 2 tarefas (`pytest -m groq_live`, estável em 3 rodadas). Ainda não ligado ao app | DONE (#45) |
| 2.1 | App em foco | `app_em_foco()` devolve o bundle id do app na frente no macOS (DEC-PV-011); `None` no Linux | DONE (#44) |
| 1.4 | Registro de treino | Cada fala não vazia vira uma linha em `~/.sagmowhisper/treino/decisoes.jsonl` (`decisao` null até a Fase 2) | DONE (#43) |
| 1.3 | Aprender correção nas Configurações | Grupo Correções: "Quando ouvir" → "Escrever" grava em `correcoes.json` e vale sem reiniciar | DONE (#42) |
| 1.2 | Correções pós-transcrição | "cloud code"→Claude Code, "Rhythm.md"→README.md, "Claudio Code"→Claude Code; palavra inteira; `~/.sagmowhisper/correcoes.json` soma pares | DONE (#41) |
| 1.1 | Glossário no Whisper | Termos vão no `prompt` da Groq (≤ 224 tokens); `~/.sagmowhisper/glossario.json` soma termos ao inicial | DONE (#40) |
| 1.0 | Ponte de Voz: tecla F8 → segurar Control direito | Segurar sozinho grava; combinação ou toque < 0,3 s descarta; Control esquerdo nunca grava; F8 aceito | DONE (#34) |

**Próxima:** 2.4 (voz reserva Piper Faber sem internet) ou 2.5 (responder dúvida em voz), quando o Raul escolher.
**Limite da Groq (free tier):** 8000 tokens/min no `gpt-oss-120b`; cada limpeza gasta ~700.
**Suíte:** 390 passed / 0 falhas
