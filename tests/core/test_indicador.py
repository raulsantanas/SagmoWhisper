import pytest

from src.core.indicador import (
    AMPLITUDE_MINIMA,
    ESTILOS_ESCUTA,
    EscutaComCarencia,
    NivelDaVoz,
    PicoEntreQuadros,
    ONDAS,
    amplitude_ouvindo,
    first_line,
    formatar_tempo,
    pontos_da_onda,
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


SILENCIO = 1e-5
VOZ = 0.05
GRITO = 0.9


def _escuta():
    t = [0.0]
    return EscutaComCarencia(relogio=lambda: t[0]), t


def test_silencio_na_carencia_e_ok():
    escuta, t = _escuta()
    t[0] = 1.0
    assert escuta.classificar(SILENCIO) == "ok"


def test_mudo_desde_o_inicio_avisa_apos_carencia():
    escuta, t = _escuta()
    for instante in (0.0, 0.5, 1.0, 1.6):
        t[0] = instante
        resultado = escuta.classificar(SILENCIO)
    assert resultado == "mudo"


def test_voz_depois_da_carencia_e_ok():
    escuta, t = _escuta()
    t[0] = 2.0
    assert escuta.classificar(VOZ) == "ok"


def test_volume_alto_ignora_carencia():
    escuta, t = _escuta()
    t[0] = 0.1
    assert escuta.classificar(GRITO) == "alto"


def test_reiniciar_zera_carencia_e_historico():
    escuta, t = _escuta()
    t[0] = 3.0
    assert escuta.classificar(SILENCIO) == "mudo"
    escuta.reiniciar()
    t[0] = 3.5
    assert escuta.classificar(SILENCIO) == "ok"


def test_estilos_tem_os_textos_do_spec():
    assert ESTILOS_ESCUTA["ok"] == ("Ouvindo…", "#E6E7EE")
    assert ESTILOS_ESCUTA["mudo"] == (
        "Não estou ouvindo nada — microfone mudo?",
        "#FFB4B4",
    )
    assert ESTILOS_ESCUTA["alto"] == ("Volume alto", "#F5B942")


def _rms(db):
    return 10 ** (db / 20)


def _alimentar(nivel, db, quadros):
    for _ in range(quadros):
        resultado = nivel.avancar(_rms(db))
    return resultado


def test_ruido_constante_fica_perto_do_piso():
    assert _alimentar(NivelDaVoz(), -42, 90) < 0.1


def test_fala_acima_do_ruido_chega_perto_do_topo_rapido():
    nivel = NivelDaVoz()
    _alimentar(nivel, -48, 60)
    assert _alimentar(nivel, -28, 3) > 0.8


def test_pico_sobe_rapido_e_desce_devagar():
    nivel = NivelDaVoz()
    _alimentar(nivel, -48, 60)
    _alimentar(nivel, -28, 3)
    assert nivel.avancar(_rms(-48)) > 0.5


def test_fala_continua_nao_vira_ruido_de_fundo():
    nivel = NivelDaVoz()
    _alimentar(nivel, -48, 60)
    assert _alimentar(nivel, -28, 90) > 0.6


def test_silencio_digital_nao_derruba_o_piso_abaixo_de_60db():
    nivel = NivelDaVoz()
    _alimentar(nivel, -120, 30)
    assert _alimentar(nivel, -50, 3) < 0.5


def test_pico_entre_quadros_guarda_o_maior_e_zera_ao_consumir():
    pico = PicoEntreQuadros()
    for rms in (0.01, 0.2, 0.05):
        pico.registrar(rms)
    assert pico.consumir() == 0.2
    assert pico.consumir() == 0.0
