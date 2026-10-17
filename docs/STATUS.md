# STATUS — SagmoWhisper

> Só o estado atual. O diário antigo (até 2026-10-17) está no git: `git log -p -- docs/STATUS.md`.

**Atualizado:** 2026-10-17

| # | Task | Critério de aceite | Status |
|---|------|---------------------|--------|
| 1.0 | Ponte de Voz: tecla F8 → segurar Control direito | Segurar sozinho grava; combinação ou toque < 0,3 s descarta; Control esquerdo nunca grava; F8 aceito | EM ANDAMENTO (PR aberta) |
| — | Interface mais moderna | A definir com o Raul (desenho antes do código) | EM ANDAMENTO |

**Próxima:** 1.1 (glossário no Whisper), depois de o Raul aprovar o 1.0.
**Pendências do Raul:** reinstalar o app (`./install.sh`), reconceder Microfone, Acessibilidade e
Monitoramento de Entrada, e testar ao vivo o Control direito (DEC-PV-009) e a auto-cura do Groq (#32).
**Suíte:** 265 passed / 0 falhas
