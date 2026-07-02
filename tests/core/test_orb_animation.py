import pytest

from src.core.orb_animation import (
    first_line,
    orb_glow,
    orb_scale,
    ring_progress,
    rotation_angle,
)


def test_orb_scale_e_linear_entre_09_e_112():
    assert orb_scale(0.0) == pytest.approx(0.9)
    assert orb_scale(0.5) == pytest.approx(1.01)
    assert orb_scale(1.0) == pytest.approx(1.12)


def test_orb_glow_e_linear_entre_035_e_1():
    assert orb_glow(0.0) == pytest.approx(0.35)
    assert orb_glow(1.0) == pytest.approx(1.0)


def test_ring_progress_faz_loop_de_12s():
    assert ring_progress(0.0) == pytest.approx(0.0)
    assert ring_progress(0.6) == pytest.approx(0.5)
    assert ring_progress(1.2) == pytest.approx(0.0)
    assert ring_progress(1.8) == pytest.approx(0.5)


def test_rotation_angle_faz_loop_de_4s_em_360_graus():
    assert rotation_angle(0.0) == pytest.approx(0.0)
    assert rotation_angle(2.0) == pytest.approx(180.0)
    assert rotation_angle(4.0) == pytest.approx(0.0)


def test_first_line_pega_so_a_primeira_linha():
    assert first_line("401 Invalid API Key\nstack trace...") == "401 Invalid API Key"


def test_first_line_trunca_com_reticencias():
    longa = "x" * 100
    assert first_line(longa) == "x" * 59 + "…"
    assert len(first_line(longa)) == 60


def test_first_line_curta_fica_intacta():
    assert first_line("curta") == "curta"


def test_first_line_vazia_devolve_vazio():
    assert first_line("") == ""
