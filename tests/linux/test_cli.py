from src.linux import cli


def test_no_macos_recusa_e_aponta_o_app_nativo(capsys):
    code = cli.main(["setup"], platform="darwin")
    assert code == 1
    assert "app nativo" in capsys.readouterr().out


def test_setup_chama_o_wizard(monkeypatch):
    calls = []
    monkeypatch.setattr(cli.setup_wizard, "run_setup", lambda: calls.append(1))
    assert cli.main(["setup"], platform="linux") == 0
    assert calls == [1]


def test_login_on_ativa_o_servico(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli.login_service, "enable", lambda: calls.append(1))
    assert cli.main(["login", "on"], platform="linux") == 0
    assert calls == [1]
    assert "ativado" in capsys.readouterr().out


def test_login_off_desativa_o_servico(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli.login_service, "disable", lambda: calls.append(1))
    assert cli.main(["login", "off"], platform="linux") == 0
    assert calls == [1]
    assert "desativado" in capsys.readouterr().out


def test_login_status_reporta_estado(monkeypatch, capsys):
    monkeypatch.setattr(cli.login_service, "is_enabled", lambda: True)
    assert cli.main(["login", "status"], platform="linux") == 0
    assert "ativado" in capsys.readouterr().out


def test_run_com_sessao_invalida_imprime_erro_e_sai_1(monkeypatch, capsys):
    monkeypatch.setattr(
        cli.session_check, "check_session", lambda: "erro da sessão"
    )
    assert cli.main(["run"], platform="linux") == 1
    assert "erro da sessão" in capsys.readouterr().out
