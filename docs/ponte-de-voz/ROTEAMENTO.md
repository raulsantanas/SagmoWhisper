# Roteamento — regras de negócio

## 1. Tipo da fala — detecção automática

O Raul **não diz** "isso é um prompt". O sistema decide sozinho pela **intenção** da fala,
não por palavras-chave. Ver DEC-PV-010.

| Tipo | Regra | Sinais |
|---|---|---|
| `comando` | A fala **pede uma ação** a uma IA: mudar, criar, corrigir, analisar, olhar, revisar | Imperativo ("faz", "troca", "dá uma olhada"); desejo ("gostaria que", "quero que", "preciso que"); relato de contexto seguido de pedido ("eu alterei X porque quero Y... então olha") |
| `duvida` | A fala **só quer uma explicação** e não pede nenhuma mudança | "o que é", "como funciona", "por que", "qual a diferença", "vale a pena" — sem pedido de ação |
| `ditado` | O texto é **para outra pessoa ou documento** | Saudação ou vocativo ("Prezada", "Oi, João"), assinatura, tom de mensagem; app em foco é e-mail, WhatsApp, Word, Docs |

Regras de desempate (nesta ordem):
1. **Pedido prevalece.** Se a fala tem uma dúvida **e** um pedido de ação, é `comando`.
2. **App em foco.** VS Code, Terminal, Claude Code ou Claude Desktop → favorece `comando`/`duvida`.
   Mail, WhatsApp, Messages, Word, Pages, Google Docs → favorece `ditado`.
3. **Fala longa com vários assuntos** ("e outra coisa...") → `comando` com várias `<tarefas>`.
4. Confiança abaixo de 0,6 → `comando` (é mais barato confirmar um prompt do que perder um pedido).

O gate atual `prompt_register_triggered` ("isso é um prompt") continua funcionando como
**atalho forçado**: se disparar, é `comando` sem consultar o classificador. Ele deixa de ser obrigatório.

### Exemplos que viram teste (casos reais do Raul)

| Fala transcrita | Tipo esperado | Por quê |
|---|---|---|
| "Eu alterei o README porque gostaria de trocar a tecla F8 pelo Control. E outra coisa, eu gostaria que ele entendesse automaticamente o que é um prompt ou não... então dá uma olhada lá no README" | `comando` | Contexto + dois pedidos + "dá uma olhada". Vira prompt com 2 tarefas |
| "O que é Turbo Stream?" | `duvida` | Só explicação |
| "Qual a diferença entre o Laya e o Jev?" | `duvida` | Só explicação |
| "O Laya tem muito falso positivo, certo? Se tiver, troca pelo Groq na classificação" | `comando` | Dúvida + pedido → pedido prevalece |
| "Prezada Dra. Yukimi, segue em anexo o folder revisado" | `ditado` | Texto para outra pessoa |
| "Corrige o teste do checkout que está falhando" | `comando` | Imperativo direto |

## 2. Modelo e esforço (só para `comando`)

| Classe | Modelo | Esforço | Sinais |
|---|---|---|---|
| Visual | **Opus** | **medium (sempre)** | Imagem anexada; layout, tela, página, design, print |
| Arquitetura | **Opus** | **medium (sempre)** | "define", "arquitetura", "como vai funcionar", schema, integração |
| Código complexo | Sonnet | high | Bug difícil, vários arquivos, "não sei por que" |
| Código padrão | Sonnet | medium | Funcionalidade nova, testes, mudança em documentação — é o padrão |
| Código simples | Sonnet | low | Correção pontual, um arquivo |
| Mecânico simples | Haiku | low | Renomear, formatar, mover, apagar |
| Mecânico com geração | Haiku | medium | Texto ou código pequeno e repetitivo |

Regras fixas:
- O Opus **nunca** roda com esforço diferente de `medium`.
- Na dúvida entre duas classes, escolher a de **maior** capacidade (errar para cima custa menos
  que refazer).
- Confiança abaixo de 0,6 → usar Sonnet medium e registrar como "incerto".

## 3. Formato do registro de treino (`decisoes.jsonl`)

```json
{"ts": "2026-10-17T17:40:00-03:00",
 "app_em_foco": "Code",
 "texto_bruto": "corrige o teste do cloud code",
 "texto_corrigido": "corrige o teste do Claude Code",
 "decisao": {"tipo": "comando", "modelo": "sonnet", "esforco": "low", "confianca": 0.82, "origem": "groq"},
 "correcao_do_raul": null}
```

`correcao_do_raul` é preenchido quando o Raul diz que a decisão estava errada, por exemplo
`{"tipo": "duvida"}`. Essas linhas são o material de treino do Laya.

## 4. Respostas em voz

| Situação | Quem gera o texto | Limite |
|---|---|---|
| Dúvida | Groq | 3 frases |
| Confirmação antes de enviar comando | Groq (resumo do prompt) | 1 frase — ver DEC-PV-006 |
| Fim do trabalho | Claude, linha `VOZ:` | 2 frases |
| Progresso (fase 3) | Texto fixo por evento | 1 frase curta |

Voz: Edge TTS `pt-BR-FranciscaNeural`. Medido no Mac do Raul em 2026-10-17:
primeiro som entre 650 e 1.170 ms (normalmente ~700–900 ms); áudio completo de uma
frase curta entre 0,9 e 1,8 s.
