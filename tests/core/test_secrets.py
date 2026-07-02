from src.core import secrets


def test_get_api_key_le_do_keychain(monkeypatch):
    def fake_get(service, account):
        assert (service, account) == ("SagmoWhisper", "groq")
        return "gsk_teste"

    monkeypatch.setattr(secrets.keyring, "get_password", fake_get)
    assert secrets.get_api_key("groq") == "gsk_teste"


def test_get_api_key_retorna_none_quando_ausente(monkeypatch):
    monkeypatch.setattr(
        secrets.keyring, "get_password", lambda service, account: None
    )
    assert secrets.get_api_key("openai") is None


def test_set_api_key_grava_no_keychain(monkeypatch):
    gravado = {}
    monkeypatch.setattr(
        secrets.keyring,
        "set_password",
        lambda service, account, password: gravado.update(
            {(service, account): password}
        ),
    )
    secrets.set_api_key("openai", "sk-abc")
    assert gravado == {("SagmoWhisper", "openai"): "sk-abc"}
