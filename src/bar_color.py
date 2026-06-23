def bar_color(rms: float) -> tuple[str, str]:
    if rms >= 0.6:
        return "#E74C3C", "⚠️ Volume alto"
    if rms < 0.02:
        return "#F39C12", "⚠️ Áudio fraco"
    return "#4A90E2", "🎙️ Ouvindo..."
