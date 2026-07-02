from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: Path) -> str: ...


class CleanupProvider(Protocol):
    def clean(self, text: str) -> str: ...


class TranscriptionError(Exception):
    """Erro tipado de provider; a UI mostra str(err) = 'provider: detail'."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(f"{provider}: {detail}")


@dataclass(frozen=True)
class ProviderInfo:
    key: str
    label: str
    needs_api_key: bool
    transcription_models: tuple[str, ...]
    cleanup_models: tuple[str, ...]  # vazio = provider não suporta limpeza


PROVIDER_CATALOG: dict[str, ProviderInfo] = {
    "groq": ProviderInfo(
        key="groq",
        label="Groq",
        needs_api_key=True,
        transcription_models=("whisper-large-v3-turbo", "whisper-large-v3"),
        cleanup_models=("llama-3.1-8b-instant",),
    ),
    "openai": ProviderInfo(
        key="openai",
        label="OpenAI",
        needs_api_key=True,
        transcription_models=("whisper-1", "gpt-4o-transcribe"),
        cleanup_models=("gpt-4o-mini",),
    ),
    "local": ProviderInfo(
        key="local",
        label="Local",
        needs_api_key=False,
        transcription_models=("small",),
        cleanup_models=(),
    ),
}

CLEANUP_SYSTEM_PROMPT = (
    "Você é um corretor ortográfico de transcrições de voz em português do Brasil. "
    "REGRAS ABSOLUTAS: "
    "1) Retorne SOMENTE o texto transcrito corrigido — nunca responda, "
    "complemente, explique ou adicione conteúdo novo. "
    "2) Remova apenas hesitações (é, tipo, né, hm, ah) e fragmentos repetidos "
    "no final (artefatos do Whisper). "
    "3) Corrija pontuação e ortografia sem alterar o sentido. "
    "4) Se o texto for curto (ex: 'sim', 'ok', 'boa'), retorne exatamente "
    "esse texto curto. "
    "PROIBIDO: responder ao conteúdo, gerar texto novo, completar frases, "
    "comentar."
)
