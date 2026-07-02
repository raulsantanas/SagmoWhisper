"""Testes do login_item (LaunchAgent que implementa "Abrir no login")."""
import plistlib
from pathlib import Path

from src.core.login_item import (
    AGENT_LABEL,
    _cli,
    app_installed,
    disable,
    enable,
    is_enabled,
    plist_xml,
)


def test_plist_xml_gera_launchagent_valido():
    xml = plist_xml(Path("/Applications/X.app/Contents/MacOS/X"))
    data = plistlib.loads(xml.encode())
    assert data["Label"] == AGENT_LABEL
    assert data["ProgramArguments"] == [
        "/Applications/X.app/Contents/MacOS/X"
    ]
    assert data["RunAtLoad"] is True


def test_enable_cria_plist_e_liga_o_estado(tmp_path):
    agent = tmp_path / "LaunchAgents" / "com.test.plist"
    assert is_enabled(agent) is False
    enable(agent, Path("/tmp/binario"))
    assert is_enabled(agent) is True
    data = plistlib.loads(agent.read_bytes())
    assert data["ProgramArguments"] == ["/tmp/binario"]


def test_disable_remove_plist_e_e_silencioso_se_ausente(tmp_path):
    agent = tmp_path / "a.plist"
    disable(agent)  # arquivo ausente: não levanta erro
    agent.write_text("qualquer coisa")
    disable(agent)
    assert not agent.exists()


def test_app_installed_reflete_existencia_do_binario(tmp_path):
    assert app_installed(tmp_path / "nao-existe") is False
    binario = tmp_path / "SagmoWhisper"
    binario.write_text("")
    assert app_installed(binario) is True


def test_cli_enable_e_status(tmp_path, capsys):
    agent = tmp_path / "a.plist"
    assert _cli(["enable"], agent, Path("/tmp/binario")) == 0
    assert agent.exists()
    assert _cli(["status"], agent, Path("/tmp/binario")) == 0
    assert capsys.readouterr().out.strip() == "enabled"


def test_cli_disable_e_status(tmp_path, capsys):
    agent = tmp_path / "a.plist"
    enable(agent, Path("/tmp/binario"))
    assert _cli(["disable"], agent, Path("/tmp/binario")) == 0
    assert not agent.exists()
    assert _cli(["status"], agent, Path("/tmp/binario")) == 0
    assert capsys.readouterr().out.strip() == "disabled"


def test_cli_comando_invalido_retorna_2(tmp_path, capsys):
    assert _cli(["xyz"], tmp_path / "a.plist", Path("/tmp/b")) == 2
    assert "uso:" in capsys.readouterr().out
