# Roadmap — Ponte de Voz

Cada item: teste RED primeiro, depois implementação mínima. Um item por PR.

## Fase 1 — Ouvir certo e aprender (resolve o "cloud")

| Item | Entrega | Critério de aceite |
|---|---|---|
| 1.0 | Tecla de gravação: F8 → segurar Control direito (`gesto_tecla.py`) | Segurar o Control direito sozinho grava e soltar para; Ctrl+C, Ctrl+V e qualquer combinação cancelam e descartam; toque menor que 0,3 s não grava; Control esquerdo nunca grava; F8 continua aceito no config |
| 1.1 | `glossario.py` + `GroqTranscriber` enviando `prompt` | Teste unitário garante que os termos chegam no parâmetro `prompt`; respeita o limite de tamanho do prompt do Whisper (confirmar na doc da Groq). Glossário inicial inclui Claude, Anthropic, Claude Code, README, Laya, Groq, Sagmo, NeuroEnf |
| 1.2 | `correcoes.py` aplicado após a transcrição | "cloud code" vira "Claude Code"; "Rhythm.md" vira "README.md"; palavra inteira; não troca "cloudflare" |
| 1.3 | Aprender correção | Na janela de configurações, o Raul adiciona um par errado→certo e ele passa a valer sem reiniciar |
| 1.4 | `registro_treino.py` | Cada fala gera uma linha válida em `decisoes.jsonl` |

## Fase 2 — Decidir sozinho e responder em voz

| Item | Entrega | Critério de aceite |
|---|---|---|
| 2.1 | `app_em_foco.py` | Retorna o bundle id do app na frente no macOS (DEC-PV-011); `None` no Linux sem quebrar |
| 2.2 | `intencao.py` com Groq em modo JSON | Classifica **todos** os exemplos reais de `ROTEAMENTO.md` §1 sem o Raul dizer "isso é um prompt" (teste ao vivo opt-in). O caso "eu alterei o README... dá uma olhada" sai como `comando` com 2 tarefas |
| 2.3 | `voz.py` com Edge TTS Francisca | Fala sem travar o app; tocar o Control direito interrompe a fala |
| 2.4 | Voz reserva Piper Faber (DEC-PV-008) | Com o Edge falhando (simulado no teste), a mesma frase sai pela Faber local; volta para a Francisca quando o Edge responde |
| 2.5 | ~~`resposta_duvida.py`~~ | **Descartado** (DEC-PV-013): a voz só fala a saída do Claude Code. Pergunta ditada é colada como ditado |
| 2.6 | Ditado sem regressão | Os 237 testes atuais continuam passando |

## Fase 3 — Ponte com o Claude Code

| Item | Entrega | Critério de aceite |
|---|---|---|
| 3.1 | Regra `VOZ:` no `~/.claude/CLAUDE.md` + hook `Stop` | Ao terminar, o Mac fala só a linha `VOZ:` |
| 3.2 | Servidor local `POST /falar` no app | Hook entrega o texto; falha do app não quebra o Claude Code |
| 3.3 | Subagentes com modelo e esforço fixos em `~/.claude/agents/` | Um subagente por classe de `ROTEAMENTO.md` |
| 3.4 | Confirmação com envio automático (DEC-PV-006) | Fala o resumo; sem Esc em 3 s após o fim da fala, envia; Esc cancela e nada é enviado |
| 3.5 | `ponte_claude.py` | Comando chega ao Claude Code com indicação do subagente/modelo certo (ver DEC-PV-004) |
| 3.6 | Avisos de progresso (`PreToolUse`) | Fala só "subagente acionado" e "rodando testes"; resto em silêncio |

## Fase 4 — Laya (só com dados)

| Item | Entrega | Critério de aceite |
|---|---|---|
| 4.1 | Conjunto rotulado | ≥ 300 linhas em `decisoes.jsonl`, com as correções do Raul aplicadas |
| 4.2 | Treinar Laya (checkpoint multilíngue ou pt/es) | Em um conjunto separado para teste, acerta pelo menos tanto quanto o Groq |
| 4.3 | `ClassificadorLaya` | Implementa o mesmo `Protocol`; abaixo da confiança mínima, cai para o Groq |

## Fora do escopo agora

- Modelo de voz local em tempo real (PersonaPlex etc.): hardware não suporta.
- Reescrever em Rust: ganho de milissegundos num fluxo de segundos.
- Treinar o próprio Whisper: a Groq não oferece; o glossário + correções resolvem o caso.
