# Ponte de Voz — épico do SagmoWhisper

> Criado em 2026-10-17. Fonte da verdade para esta evolução. Documentação vence código.

## O que é

Evolução do SagmoWhisper: hoje ele **ouve** (F8 → Whisper Groq → limpeza → cola no cursor).
A Ponte de Voz faz ele também **entender, decidir e responder falando**:

0. Troca a tecla de gravação de **F8 para segurar o Control direito** (DEC-PV-009, item 1.0 do ROADMAP).
1. Transcreve sem errar termos técnicos ("Claude", não "cloud"; "README", não "Rhythm") e **aprende** com as correções do Raul.
2. Decide **sozinho** se a fala é **dúvida**, **comando** para o Claude Code ou **ditado**.
   O Raul **não precisa** dizer "isso é um prompt" (DEC-PV-010 e `ROTEAMENTO.md`).
3. Dúvida → não é respondida em voz: a voz só fala a saída do Claude Code (DEC-PV-013).
4. Comando → prompt estruturado + escolha de **modelo e esforço** → Claude Code.
5. Enquanto o Claude trabalha, o Raul pergunta o status ("em que estágio está?") e ela responde.
   Quando o Claude termina → fala um resumo de até 5 frases: testes, o que está fazendo, o que já
   fez, próxima fase e o que falta. A voz só fala isso (DEC-PV-013).
6. Registra cada decisão para, no futuro, treinar o **Laya** como classificador local.

## Por que dentro deste repositório (e não um projeto novo)

O SagmoWhisper já tem: tecla de gravação configurável, Groq (Whisper + llama-3.3-70b),
limpeza com detecção de "isso é um prompt" (`prompt_register_triggered`), estruturação em
tags XML, 237 testes, Ruff com complexidade ≤ 4 e o app de macOS instalado. Um projeto novo
duplicaria tudo isso. Ver DEC-PV-001 em `DECISOES.md`.

## Ordem de leitura

| Arquivo | Para quê |
|---|---|
| `ARQUITETURA.md` | Módulos novos, contratos (interfaces) e fluxo |
| `ROTEAMENTO.md` | Regras de negócio: dúvida/comando/ditado, modelo e esforço |
| `ROADMAP.md` | Fases, itens, critérios de aceite e testes RED |
| `DECISOES.md` | Decisões tomadas e decisões pendentes do Raul |
| `../STATUS.md` | Estado atual do projeto e do épico (curto, só o presente) |

## Como iniciar no Claude Code

```
cd /Users/raul/Documents/dev/SagmoWhisper/voz && claude
```

Primeiro prompt sugerido:

> Leia CLAUDE.md e docs/ponte-de-voz/README.md, ARQUITETURA.md e ROADMAP.md.
> Comece pelo item 1.0 do ROADMAP. Escreva primeiro o teste RED, mostre a falha,
> depois implemente o mínimo para passar. Não avance de item sem eu aprovar.

## Custos

| Parte | Quem faz | Custo |
|---|---|---|
| Transcrição, classificação, prompt | Groq (plano gratuito) | R$ 0 |
| Voz de resposta | Edge TTS, voz fr-FR-VivienneMultilingualNeural | R$ 0 (usa internet) |
| Trabalho de código | Claude Code | plano Anthropic |
| Resumo falado | linha `VOZ:` no fim da resposta | ~60 a 80 palavras por resposta |
