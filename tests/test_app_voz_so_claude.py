"""A voz só fala a saída do Claude Code (Raul, 2026-10-23, DEC-PV-013).

Uma pergunta ditada não pode ser respondida em voz: ela é colada como
qualquer ditado, mesmo que o Groq a classificasse como dúvida."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("objc")

import src.app as app_module  # noqa: E402
from src.core.config import DEFAULTS, Config  # noqa: E402
from src.core.providers import factory  # noqa: E402


class _GroqQueSempreAcharDuvida:
    def __init__(self):
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        conteudo = json.dumps({"tipo": "duvida", "confianca": 0.99})
        if "response_format" not in kwargs:
            conteudo = "Turbo Stream atualiza partes da página."
        mensagem = SimpleNamespace(content=conteudo)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensagem)])


def test_pergunta_ditada_e_colada_e_a_voz_fica_calada(monkeypatch):
    transcriber = MagicMock()
    transcriber.transcribe.return_value = "O que é Turbo Stream?"
    injector = MagicMock()
    monkeypatch.setattr(factory, "build_components", lambda c: (transcriber, None))
    monkeypatch.setattr(factory, "resolve_api_key", lambda p: "gsk_x")
    monkeypatch.setattr(
        factory.groq_provider, "make_client", lambda k: _GroqQueSempreAcharDuvida()
    )
    monkeypatch.setattr(app_module, "TextInjector", lambda: injector)
    app = app_module.VozMenuBar.__new__(app_module.VozMenuBar)
    app._config = Config(**{**DEFAULTS, "provider": "groq"})
    app._voz = MagicMock()

    app._rebuild_pipeline()
    app._pipeline.run("a.wav")

    injector.inject.assert_called_once_with("O que é Turbo Stream?")
    app._voz.falar.assert_not_called()
