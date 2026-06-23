from src.bar_color import bar_color


def test_normal_volume_returns_blue():
    color, label = bar_color(0.3)
    assert color == "#4A90E2"
    assert label == "🎙️ Ouvindo..."


def test_high_volume_returns_red():
    color, label = bar_color(0.7)
    assert color == "#E74C3C"
    assert label == "⚠️ Volume alto"


def test_low_volume_returns_yellow():
    color, label = bar_color(0.01)
    assert color == "#F39C12"
    assert label == "⚠️ Áudio fraco"


def test_boundary_high_is_inclusive():
    color, label = bar_color(0.6)
    assert color == "#E74C3C"


def test_boundary_low_is_exclusive():
    color, label = bar_color(0.02)
    assert color == "#4A90E2"
