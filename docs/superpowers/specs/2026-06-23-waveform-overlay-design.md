# Waveform Overlay — Design Spec
**Data:** 2026-06-23  
**Status:** Aprovado

---

## Objetivo

Exibir uma janela flutuante nativa macOS sobre todos os apps enquanto o usuário grava via F8, mostrando waveform em tempo real com alertas visuais de qualidade de áudio.

---

## Arquitetura

Novo módulo `src/waveform_overlay.py` totalmente isolado. Recebe comandos do `app.py` e dados de RMS do `AudioRecorder`. Não conhece pipeline, transcriber nem cleaner.

Fluxo:
```
F8 press  → overlay.show()           → "Ouvindo..." + barras animadas
audio in  → overlay.update_bars(rms) → barras atualizam a 30fps
F8 release→ overlay.set_transcribing()→ "Transcrevendo..." + barras congeladas
pipeline  → overlay.hide()           → fade out 0.3s
```

---

## Componentes

### `WaveformOverlay` (`src/waveform_overlay.py`)
- `NSWindow` sem título, `NSFloatingWindowLevel`, fundo transparente
- Dimensões: 320×80px, posição: canto superior esquerdo, 20px abaixo da barra de menu
- Bordas arredondadas 12px, fundo `#1a1a2e` com alpha 0.92
- Expõe: `show()`, `hide()`, `set_transcribing()`, `update_bars(rms: float)`
- 30 barras verticais, altura = `rms * fator_escala`, mínimo 4px, máximo 48px
- Atualização via `setNeedsDisplay_` disparado sob demanda pelo callback de áudio (sem NSTimer fixo): redesenha apenas quando novo RMS chega, mais eficiente que um timer a 30fps

### `WaveformView` (NSView interno)
- Desenha barras com `NSBezierPath`
- Cor determinada pelo RMS atual:
  - Normal (`rms < 0.6`): azul `#4A90E2`
  - Alto / saturação (`rms >= 0.6`): vermelho `#E74C3C`
  - Fraco (`rms < 0.02`): amarelo `#F39C12`
- Label no canto superior esquerdo: emoji + texto de estado

---

## Estados Visuais

| Estado | Label | Cor barras | Animação |
|--------|-------|------------|----------|
| Gravando — normal | 🎙️ Ouvindo... | Azul `#4A90E2` | Barras vivas |
| Gravando — saturação | ⚠️ Volume alto | Vermelho `#E74C3C` | Barras vivas |
| Gravando — fraco | ⚠️ Áudio fraco | Amarelo `#F39C12` | Barras vivas |
| Transcrevendo | ⏳ Transcrevendo... | Cinza, 50% alpha | Barras congeladas |
| Concluído | — | — | Fade out 0.3s |

---

## Mudanças nos arquivos existentes

### `audio_recorder.py`
- Construtor aceita `sample_callback: callable | None = None`
- `_on_audio` chama `sample_callback(rms)` após enfileirar, se definido
- RMS calculado com `numpy`: `float(np.sqrt(np.mean(indata**2)))`

### `app.py`
- Inicializa `WaveformOverlay` após criar o pipeline
- `_on_press`: chama `overlay.show()`
- `_on_release`: chama `overlay.set_transcribing()` antes do pipeline
- `_handle_recording`: chama `overlay.hide()` após pipeline concluir
- Passa `overlay.update_bars` como `sample_callback` para `AudioRecorder`

### Arquivos não alterados
`pipeline.py`, `transcriber.py`, `cleaner.py`, `config.py`, `text_injector.py`

---

## Dependências

Nenhuma nova — `AppKit` e `numpy` já estão no projeto.

---

## Testes

- `test_waveform_overlay.py`: testa os 3 estados de cor via RMS (normal, alto, fraco)
- `test_audio_recorder.py`: verifica que `sample_callback` é chamado com valor float
