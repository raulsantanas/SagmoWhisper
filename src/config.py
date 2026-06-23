import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    groq_api_key: str
    transcription_model: str
    cleanup_model: str
    language: str
    enable_cleanup: bool
    hotkey: str
    sample_rate: int

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY ausente. Defina no .env ou no ambiente "
                "(copie .env.example para .env e cole sua chave)."
            )
        return cls(
            groq_api_key=api_key,
            transcription_model=os.getenv(
                "TRANSCRIPTION_MODEL", "whisper-large-v3-turbo"
            ),
            cleanup_model=os.getenv("CLEANUP_MODEL", "llama-3.1-8b-instant"),
            language=os.getenv("LANGUAGE", "pt"),
            enable_cleanup=os.getenv("ENABLE_CLEANUP", "true").lower() == "true",
            hotkey=os.getenv("HOTKEY", "f8"),
            sample_rate=int(os.getenv("SAMPLE_RATE", "16000")),
        )
