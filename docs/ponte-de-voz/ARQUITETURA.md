# Arquitetura — Ponte de Voz

Monolito local em Python 3.11, dentro do app SagmoWhisper. Sem servidor externo,
sem banco de dados: arquivos JSON/JSONL em `~/.sagmowhisper/`.

## Fluxo

```
Segurar Control direito → gravação (existe) → [1] Whisper Groq + glossário → [2] correções aprendidas
   → [3] classificador de intenção (texto + app em foco)
        ├─ ditado  → limpeza (existe) → cola no cursor (existe)
        ├─ dúvida  → cola como ditado (sem voz, DEC-PV-013)
        ├─ status  → resposta do registro de progresso → [6] voz (não cola, não toca o Claude)
        └─ comando → limpeza/prompt XML (existe)
                     → [5] ponte Claude Code (modelo + esforço), direto, sem confirmação (DEC-PV-014)
                     → Claude trabalha; hooks gravam cada passo no registro de progresso (sem falar)
                     → hook Stop lê linha VOZ: → [6] voz
Toda decisão de [3] → [7] registro de treino (JSONL)
Tocar o Control direito enquanto ela fala → interrompe a voz
```

## Tecla de gravação (Control direito)

`src/hotkey.py` já resolve o nome da tecla pelo config (pynput: `ctrl_r`).
Trocar só o nome **não basta**: Control é modificador e dispararia em todo Ctrl+C, Ctrl+V etc.

Regras do gesto (DEC-PV-009):
- Gravar enquanto o **Control direito** estiver pressionado **sozinho**; soltar encerra a gravação.
- Se **qualquer outra tecla** for pressionada enquanto o Control direito está seguro, a gravação
  é **cancelada e descartada** (foi um atalho, não um ditado).
- Toque curto (menos de 0,3 s) não grava: evita disparo acidental.
- O Control esquerdo **nunca** dispara a gravação.
- F8 deixa de ser padrão, mas continua aceito no config.
- "Command direito" (`cmd_r`) também é aceito: em teclado de PC com Control↔Command trocado no
  macOS, é assim que o "Ctrl" físico da direita chega (DEC-PV-009).

## Módulos novos (todos em `src/core/`)

| # | Módulo | Responsabilidade | Reaproveita |
|---|---|---|---|
| 0 | `gesto_tecla.py` | Regras do gesto do Control direito; cancela em combinações | `hotkey.py` |
| 1 | `glossario.py` | Lista de termos enviada no parâmetro `prompt` do Whisper | `GroqTranscriber` (hoje não envia `prompt`) |
| 2 | `correcoes.py` | Substituições pós-transcrição + aprendizado com correções | — |
| 3 | `intencao.py` | Decide tipo, modelo, esforço e confiança | `prompt_register_triggered`, cliente Groq |
| 5 | `ponte_claude.py` | Entrega o comando ao Claude Code com o roteamento | `text_injector.py` |
| 6 | `voz.py` | Fala texto (Edge TTS), fila e interrupção | `gesto_tecla.py` |
| 7 | `registro_treino.py` | Grava decisões e correções do Raul em JSONL | — |
| 8 | `app_em_foco.py` | Informa qual app está na frente (sinal para o classificador) | — |

## Contratos (interfaces)

Seguir o padrão `Protocol` já usado em `src/core/providers/base.py`.

```python
@dataclass(frozen=True)
class Decisao:
    tipo: Literal["duvida", "comando", "ditado"]
    modelo: Literal["opus", "sonnet", "haiku"] | None   # só para comando
    esforco: Literal["low", "medium", "high"] | None    # só para comando
    confianca: float                                    # 0.0 a 1.0
    origem: Literal["groq", "laya", "regra"]
    tarefas: tuple[str, ...] = ()                       # só para comando; 1 por pedido (2.2)

class ClassificadorIntencao(Protocol):
    def classificar(self, texto: str, tem_imagem: bool, app_em_foco: str | None) -> Decisao: ...

class Voz(Protocol):
    def falar(self, texto: str) -> None: ...   # não bloqueia; entra na fila
    def interromper(self) -> None: ...         # chamado pelo toque no Control direito
```

Regra: o Laya entra no futuro como **outra implementação** de `ClassificadorIntencao`.
Nenhum outro módulo pode depender de qual classificador está ativo.

## Dados em `~/.sagmowhisper/`

| Arquivo | Conteúdo |
|---|---|
| `glossario.json` | `{"termos": ["Claude", "Anthropic", "Claude Code", "README", ...]}` Quando existe, seus termos **somam** aos do glossário inicial do código (Raul, 18/10); vale ao abrir o app ou salvar Configurações. Formato inválido vira erro no menu |
| `correcoes.json` | `{"cloud code": "Claude Code", "rhythm.md": "README.md", ...}` Soma às correções iniciais do código e pode reescrever uma delas; só palavra inteira, sem diferenciar maiúsculas. "Claudio Code" vira Claude Code, mas "Cláudio" sozinho não; "cloud" sozinho também não (é nuvem) (18/10). Também recebe pares pelo grupo Correções das Configurações, que grava aqui e remonta o pipeline na hora (1.3) |
| `treino/decisoes.jsonl` | Uma linha por fala (formato em `ROTEAMENTO.md`) |

## Integração com o Claude Code

- **Hook `Stop`** (em `~/.claude/settings.json`): `hooks/falar_stop.py` (lógica em
  `src/core/hook_stop.py`) pega a resposta do turno, extrai a **última** linha que começa com `VOZ:` e
  envia o texto ao app. Roda no `python3` do sistema (só stdlib, compatível com 3.9), sempre sai com 0 e
  não imprime nada. Lê a porta do `config.json` do app (`SAGMOWHISPER_CONFIG` troca o caminho).
- **Canal hook → app:** HTTP local em `127.0.0.1` (`voice_port` no config, padrão 47821), rota
  `POST /falar` com `{"texto": "..."}` (até 1000 caracteres). Exige `Content-Type: application/json` e
  `Host` local, porque qualquer página do navegador alcança 127.0.0.1. Porta ocupada: o app abre sem a voz.
  O cliente do hook (`cliente_voz.enviar`) devolve `False` em vez de levantar erro.
  Assim o app controla a fila e a tecla consegue interromper. Ver DEC-PV-005.
- **Hooks de progresso** (fase 3, `PreToolUse`/`PostToolUse`): enviam ao app o passo atual
  (rodando testes, editando arquivo, subagente acionado) por `POST /progresso`. O app só guarda;
  nada é falado. O hook do RTK que já existe continua; estes entram como entradas a mais.
- **Regra no CLAUDE.md global:** toda resposta termina com uma linha `VOZ:` em português, sem código,
  com até 5 frases curtas, uma por parte que se aplique: testes, o que está fazendo, o que já fez,
  próxima fase e o que falta (DEC-PV-013).

## Fronteiras

- Não altera o fluxo de ditado atual: ditado continua colando no cursor como hoje.
- Não chama a API da Anthropic diretamente. Só o Claude Code fala com a Anthropic.
- Nenhuma chave de API em arquivo do repositório: usar `src/core/secrets.py` (já existe).

## Qualidade

- TDD obrigatório (RED → GREEN → REFACTOR). Testes ao vivo do Groq/Edge com marcador opt-in,
  no mesmo padrão de `groq_live`.
- Ruff com complexidade ≤ 4 (já configurado). Adicionar **jscpd** para duplicação.
