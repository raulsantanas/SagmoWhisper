import pytest

from src.core.audio_level import classify, rms_to_db, rms_to_level


def test_rms_to_db_conversao_basica():
    assert rms_to_db(0.1) == pytest.approx(-20.0)
    assert rms_to_db(1.0) == pytest.approx(0.0)


def test_rms_to_db_nao_explode_com_zero():
    assert rms_to_db(0.0) <= -60.0


def test_voz_normal_gera_amplitude_visivel():
    # RMS 0.02 (~-34dB) era invisível na escala linear; em dB deve dar ~52%
    assert rms_to_level(0.02) == pytest.approx(0.52, abs=0.01)


def test_level_clampa_nos_extremos():
    assert rms_to_level(1.0) == 1.0       # 0dB > teto de -10dB
    assert rms_to_level(0.0000001) == 0.0  # abaixo do piso de -60dB


def test_level_e_monotonico():
    assert rms_to_level(0.01) < rms_to_level(0.05) < rms_to_level(0.2)


def test_classify_voz_normal_e_ok():
    assert classify(0.02) == "ok"


def test_classify_silencio_e_weak():
    assert classify(0.001) == "weak"   # ~-60dB


def test_classify_grito_e_loud():
    assert classify(0.6) == "loud"     # ~-4.4dB
