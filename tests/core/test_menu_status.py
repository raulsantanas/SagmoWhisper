from src.core.menu_status import COR_DO_ICONE, ESTADOS_ICONE, linha_de_status


def test_linha_de_status_pronta_mostra_tecla():
    assert linha_de_status("Command direito", None) == (
        "● Pronto · segure Command direito",
        "#36D1FF",
    )


def test_linha_de_status_mostra_erro_em_vermelho():
    assert linha_de_status("F8", "401 Invalid API Key") == (
        "Último erro: 401 Invalid API Key",
        "#FF6B81",
    )


def test_linha_de_status_corta_erro_em_80():
    texto, _ = linha_de_status("F8", "x" * 200)
    assert texto == "Último erro: " + "x" * 80


def test_parado_usa_template_e_gravando_vermelho():
    assert ESTADOS_ICONE == ("parado", "gravando", "transcrevendo", "erro")
    assert COR_DO_ICONE["parado"] is None
    assert COR_DO_ICONE["gravando"] == "#FF4D6D"
    assert COR_DO_ICONE["transcrevendo"] == "#F5B942"
