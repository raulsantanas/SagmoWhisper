# Decisões — Ponte de Voz

Todas tomadas em 2026-10-17. Nenhuma pendente.

**DEC-PV-001 — Estender o SagmoWhisper em vez de criar projeto novo.**
Motivo: tecla de gravação, gravação, Groq, limpeza, detecção de prompt, testes e app já existem.
Custo de um projeto novo: duplicar ~2.200 linhas e 237 testes.

**DEC-PV-002 — Groq classifica agora; Laya depois, treinado.**
Motivo: o Groq já é chamado para limpar e montar o prompt; classificar na mesma chamada custa zero.
O Laya sem treino erra muito e é superconfiante. Entra na Fase 4 com dados reais do Raul.
Jev descartado: nuvem, acesso antecipado e comandos saindo da máquina.

**DEC-PV-003 — Voz: Edge TTS `pt-BR-FranciscaNeural`.**
Escolhida pelo Raul ouvindo amostras de Piper (Faber, Cadu, Jeff) e Edge (Francisca, Antonio).
Voz do Mac (Luciana) rejeitada por soar robótica. Depende de internet (ver DEC-PV-008).

**DEC-PV-004 — Roteamento de modelo e esforço.**
Opus sempre em `medium` (design, layout, imagem, arquitetura). Sonnet e Haiku com esforço
escolhido pelo classificador. O Claude Code não troca esforço sozinho por mensagem
(doc oficial, 2026-10-17); por isso o roteamento é feito por subagentes com `model` e `effort`
no frontmatter, ou pelo modo não interativo `claude -p --model X --effort Y`.
Verificar a sintaxe exata na documentação antes de implementar o item 3.4.

**DEC-PV-005 — Hook → app por HTTP local.**
Motivo: o app precisa controlar a fila de fala e a tecla precisa interromper. Um script isolado
tocando áudio não conseguiria ser interrompido pelo app.

**DEC-PV-006 — Confirmação antes de enviar comando: envio automático após 3 s.**
Antes de mandar um comando ao Claude Code, ela fala o resumo do prompt em uma frase
("Vou pedir ao Claude: ..."). Se o Raul não apertar **Esc** em 3 segundos, envia sozinha.
Esc cancela e não envia nada. Contagem começa quando a fala do resumo termina.
Motivo: evita gastar token com prompt mal entendido sem obrigar a confirmar sempre.

**DEC-PV-007 — Linguagem.**
A Ponte de Voz fica em Python porque roda só no Mac. Projetos novos de back-end hospedado
da Sagmo serão em PHP (decisão separada, registrar no DECISIONS.md do SAGMO OS).

**DEC-PV-008 — Sem internet: cair para Piper Faber local.**
Se o Edge TTS falhar (sem conexão ou erro), a mesma frase é falada pela voz Piper
`pt_BR-faber-medium`, que roda no Mac sem internet. Volta para a Francisca na próxima fala
quando a conexão retornar. O modelo da Faber (~63 MB) fica em `~/.sagmowhisper/vozes/`.
Observação: sem internet o Groq também não funciona, então nesse caso só os avisos locais
(progresso e resultado do Claude, se ele estiver rodando) são falados.

**DEC-PV-009 — Tecla de gravação: segurar o Control direito sozinho.**
Substitui o F8. Grava enquanto o Control direito estiver pressionado; soltar encerra.
Combinação com qualquer outra tecla cancela e descarta; toque menor que 0,3 s não grava;
Control esquerdo nunca grava. Tocar o Control direito enquanto a voz fala interrompe a fala.
Alternativas descartadas: dois toques no Control; segurar qualquer Control.
Verificado no item 1.0 (2026-10-17): o teclado do Raul é de PC, com Control↔Command trocado no
macOS; o "Ctrl" físico da direita chega como `cmd_r`. Decisão do Raul: o app oferece também
"Command direito" (`cmd_r`), com as mesmas regras do gesto; o remapeamento do macOS fica intacto.

**DEC-PV-010 — Detecção automática de prompt.**
O Raul não precisa dizer "isso é um prompt". O classificador decide pela intenção da fala
(pedido de ação → `comando`), usando também o app em foco. Na dúvida entre dúvida e comando,
vale `comando`. O gate `prompt_register_triggered` continua como atalho forçado, não obrigatório.
Regras e casos de teste em `ROTEAMENTO.md` §1.
