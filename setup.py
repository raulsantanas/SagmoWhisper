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
            "packages": ["numpy", "sounddevice", "soundfile", "src"],
            "excludes": ["faster_whisper", "pytest", "ruff"],
        }
    },
)
