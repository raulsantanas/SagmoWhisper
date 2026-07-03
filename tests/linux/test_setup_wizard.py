import json

from src.linux.setup_wizard import run_setup


class _FakeLogin:
    def __init__(self):
        self.calls = []

    def enable(self):
        self.calls.append("enable")

    def disable(self):
        self.calls.append("disable")


def _script(answers):
    respostas = iter(answers)
    return lambda prompt: next(respostas)


def _run(tmp_path, answers, secret="sk-123", login=None):
    saved_keys = {}
    echoed = []
    run_setup(
        ask=_script(answers),
        ask_secret=lambda prompt: secret,
        echo=echoed.append,
        set_key=lambda provider, key: saved_keys.update({provider: key}),
        config_path=tmp_path / "config.json",
        login=login or _FakeLogin(),
    )
    return saved_keys, echoed


def test_fluxo_groq_completo_salva_chave_config_e_login(tmp_path):
    login = _FakeLogin()
    saved_keys, echoed = _run(
        tmp_path, answers=["groq", "s", "s"], login=login
    )

    config = json.loads((tmp_path / "config.json").read_text())
    assert saved_keys == {"groq": "sk-123"}
    assert config["provider"] == "groq"
    assert config["enable_cleanup"] is True
    assert login.calls == ["enable"]
    assert any("sagmowhisper run" in m for m in echoed)


def test_enter_vazio_assume_groq(tmp_path):
    saved_keys, _ = _run(tmp_path, answers=["", "s", "n"])
    assert "groq" in saved_keys


def test_provider_invalido_pergunta_de_novo(tmp_path):
    saved_keys, _ = _run(tmp_path, answers=["banana", "groq", "s", "n"])
    assert "groq" in saved_keys


def test_provider_local_nao_pede_chave_nem_limpeza(tmp_path):
    login = _FakeLogin()
    saved_keys, _ = _run(tmp_path, answers=["local", "n"], login=login)

    config = json.loads((tmp_path / "config.json").read_text())
    assert saved_keys == {}
    assert config["provider"] == "local"
    assert config["enable_cleanup"] is False
    assert login.calls == ["disable"]


def test_recusar_limpeza_desliga_no_config(tmp_path):
    _, _ = _run(tmp_path, answers=["groq", "n", "n"])
    config = json.loads((tmp_path / "config.json").read_text())
    assert config["enable_cleanup"] is False


def test_chave_vazia_avisa_mas_nao_salva_chave(tmp_path):
    saved_keys, echoed = _run(
        tmp_path, answers=["groq", "s", "n"], secret="  "
    )
    assert saved_keys == {}
    assert any("sem chave" in m.lower() for m in echoed)
