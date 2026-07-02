"""Build do SagmoWhisper.app: .venv/bin/python setup.py py2app."""
import tomllib
from pathlib import Path

from setuptools import setup

_VERSION = tomllib.loads(Path("pyproject.toml").read_text())["project"][
    "version"
]

_PLIST = {
    "CFBundleIdentifier": "com.raulsantana.sagmowhisper",
    "CFBundleName": "SagmoWhisper",
    "CFBundleShortVersionString": _VERSION,
    "LSUIElement": True,
    "NSMicrophoneUsageDescription": (
        "O SagmoWhisper usa o microfone para transcrever sua voz "
        "enquanto você segura a tecla de ditado."
    ),
}

setup(
    app=["SagmoWhisper.py"],
    options={
        "py2app": {
            "plist": _PLIST,
            "iconfile": "assets/SagmoWhisper.icns",
            # pynput e keyring escolhem backend por import dinâmico em runtime;
            # o modulegraph do py2app não os enxerga — sem forçar o pacote
            # inteiro, o .app quebra no launch (pynput.keyboard._darwin) ou ao
            # acessar o Keychain (keyring.backends.macOS).
            "packages": [
                "numpy",
                "sounddevice",
                "soundfile",
                "pynput",
                "keyring",
                "src",
            ],
            "excludes": ["faster_whisper", "pytest", "ruff"],
        }
    },
)
