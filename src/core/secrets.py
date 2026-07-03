"""API keys SÓ no cofre do sistema (Keychain no macOS, SecretService no
Linux) via keyring (LEI 9) — nunca em JSON ou log."""
import keyring

SERVICE = "SagmoWhisper"


def get_api_key(provider: str) -> str | None:
    return keyring.get_password(SERVICE, provider)


def set_api_key(provider: str, key: str) -> None:
    keyring.set_password(SERVICE, provider, key)
