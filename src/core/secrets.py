"""API keys ficam SÓ no Keychain do macOS (LEI 9) — nunca em JSON ou log."""
import keyring

SERVICE = "SagmoWhisper"


def get_api_key(provider: str) -> str | None:
    return keyring.get_password(SERVICE, provider)


def set_api_key(provider: str, key: str) -> None:
    keyring.set_password(SERVICE, provider, key)
