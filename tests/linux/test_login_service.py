from types import SimpleNamespace

from src.linux import login_service


class _SpyRun:
    def __init__(self, returncode=0):
        self.calls = []
        self._returncode = returncode

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        return SimpleNamespace(returncode=self._returncode)


def test_unit_usa_caminho_absoluto_e_default_target():
    text = login_service.unit_text()
    assert "ExecStart=%h/.local/bin/sagmowhisper run" in text
    assert "WantedBy=default.target" in text


def test_enable_escreve_unit_e_ativa_no_systemd(tmp_path):
    unit = tmp_path / "sagmowhisper.service"
    run = _SpyRun()

    login_service.enable(path=unit, run=run)

    assert unit.read_text() == login_service.unit_text()
    assert ["systemctl", "--user", "daemon-reload"] in run.calls
    assert [
        "systemctl", "--user", "enable", "sagmowhisper.service"
    ] in run.calls


def test_disable_remove_unit_e_desativa(tmp_path):
    unit = tmp_path / "sagmowhisper.service"
    unit.write_text("x")
    run = _SpyRun()

    login_service.disable(path=unit, run=run)

    assert not unit.exists()
    assert [
        "systemctl", "--user", "disable", "sagmowhisper.service"
    ] in run.calls


def test_disable_sem_unit_existente_nao_explode(tmp_path):
    login_service.disable(path=tmp_path / "nada.service", run=_SpyRun())


def test_is_enabled_espelha_o_returncode_do_systemctl():
    assert login_service.is_enabled(run=_SpyRun(returncode=0)) is True
    assert login_service.is_enabled(run=_SpyRun(returncode=1)) is False
