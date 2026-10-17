import pytest

from src.core.indicador import (
    AMPLITUDE_MINIMA,
    ONDAS,
    amplitude_ouvindo,
    first_line,
    formatar_tempo,
    pontos_da_onda,
    suavizar,
)


def test_onda_zera_nas_pontas():
    pts = pontos_da_onda(1.0, 3.0, 0.7)
    assert len(pts) == 81
    assert pts[0] == pytest.approx(0.0)
    assert pts[-1] == pytest.approx(0.0)


def test_onda_nunca_passa_da_amplitude():
    assert max(abs(p) for p in pontos_da_onda(0.5, 4.0, 1.3)) <= 0.5


def test_onda_com_amplitude_zero_e_plana():
    assert all(p == 0 for p in pontos_da_onda(0.0, 5.0, 2.0))


def test_suavizar_anda_um_quarto_do_caminho():
    assert suavizar(0.0, 1.0) == pytest.approx(0.25)


def test_amplitude_ouvindo_tem_piso():
    assert amplitude_ouvindo(0.0) == AMPLITUDE_MINIMA
    assert amplitude_ouvindo(0.8) == 0.8


@pytest.mark.parametrize(
    "segundos,esperado",
    [(0, "0:00"), (9.9, "0:09"), (61, "1:01"), (600, "10:00")],
)
def test_formatar_tempo(segundos, esperado):
    assert formatar_tempo(segundos) == esperado


def test_tres_ondas_nas_cores_do_spec():
    assert [cor for cor, _, _ in ONDAS] == ["#7C5CFF", "#36D1FF", "#FF5CB4"]


def test_primeira_linha_pega_so_a_primeira_linha():
    assert first_line("401 Invalid API Key\nstack trace...") == "401 Invalid API Key"


def test_primeira_linha_trunca_com_reticencias():
    longa = "x" * 100
    assert first_line(longa) == "x" * 59 + "…"
    assert len(first_line(longa)) == 60


def test_primeira_linha_curta_fica_intacta():
    assert first_line("curta") == "curta"


def test_primeira_linha_vazia_devolve_vazio():
    assert first_line("") == ""
