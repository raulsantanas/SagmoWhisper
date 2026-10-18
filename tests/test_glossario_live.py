"""Fumaça com a API real da Groq — opt-in, fora do CI.

Rodar: GROQ_API_KEY=... .venv/bin/pytest -m groq_live --no-cov -v
Confere que a Groq aceita o glossário no `prompt` (macOS: usa o `say`).
"""
import os
import shutil
import subprocess

import pytest

from src.core.config import DEFAULTS

pytestmark = [
    pytest.mark.groq_live,
    pytest.mark.skipif(
        not os.environ.get("GROQ_API_KEY") or not shutil.which("say"),
        reason="precisa de GROQ_API_KEY e do comando say (macOS)",
    ),
]


def test_groq_aceita_glossario_no_prompt(tmp_path):
    from src.core import glossario
    from src.core.providers.groq_provider import GroqTranscriber, make_client

    audio = tmp_path / "fala.wav"
    subprocess.run(
        ["say", "-v", "Luciana", "-o", str(audio),
         "--data-format=LEI16@16000", "abre o Claude Code e lê o README"],
        check=True,
    )
    transcriber = GroqTranscriber(
        make_client(os.environ["GROQ_API_KEY"]),
        DEFAULTS["transcription_model"],
        "pt",
        prompt=glossario.montar_prompt(glossario.GLOSSARIO_INICIAL),
    )

    texto = transcriber.transcribe(audio)

    assert "Claude" in texto
