import json

from src.core.config import DEFAULTS, Config, migrate_env_key_if_needed


def test_load_sem_json_e_sem_env_usa_defaults(tmp_path):
    cfg = Config.load(path=tmp_path / "config.json", env={})
    assert cfg.provider == "groq"
    assert cfg.transcription_model == "whisper-large-v3-turbo"
    assert cfg.cleanup_model == "llama-3.1-8b-instant"
    assert cfg.language == "pt"
    assert cfg.enable_cleanup is True
    assert cfg.hotkey == "f8"
    assert cfg.sample_rate == 16000


def test_load_le_json_existente(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"provider": "openai", "hotkey": "f9"}))
    cfg = Config.load(path=p, env={})
    assert cfg.provider == "openai"
    assert cfg.hotkey == "f9"
    assert cfg.language == "pt"  # campo ausente no JSON cai no default


def test_env_vence_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"provider": "openai"}))
    cfg = Config.load(path=p, env={"PROVIDER": "Local", "SAMPLE_RATE": "8000"})
    assert cfg.provider == "local"  # normalizado para minúsculas
    assert cfg.sample_rate == 8000


def test_enable_cleanup_parseia_false_do_env(tmp_path):
    cfg = Config.load(path=tmp_path / "c.json", env={"ENABLE_CLEANUP": "FALSE"})
    assert cfg.enable_cleanup is False


def test_save_cria_diretorio_e_persiste_sem_keys(tmp_path):
    p = tmp_path / "sub" / "config.json"
    cfg = Config(**DEFAULTS)
    cfg.save(path=p)
    data = json.loads(p.read_text())
    assert data == DEFAULTS
    assert "api_key" not in json.dumps(data).lower()
    assert Config.load(path=p, env={}) == cfg


def test_migracao_primeira_execucao_grava_keychain_e_json(tmp_path):
    p = tmp_path / "config.json"
    chamadas = []
    ok = migrate_env_key_if_needed(
        path=p,
        env={"GROQ_API_KEY": "gsk_migra"},
        set_key=lambda prov, key: chamadas.append((prov, key)),
    )
    assert ok is True
    assert chamadas == [("groq", "gsk_migra")]
    assert json.loads(p.read_text()) == DEFAULTS


def test_migracao_nao_roda_se_json_ja_existe(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{}")
    ok = migrate_env_key_if_needed(
        path=p, env={"GROQ_API_KEY": "x"}, set_key=lambda *_: 1 / 0
    )
    assert ok is False


def test_migracao_nao_roda_sem_key_no_env(tmp_path):
    ok = migrate_env_key_if_needed(
        path=tmp_path / "config.json", env={}, set_key=lambda *_: 1 / 0
    )
    assert ok is False


def test_load_sem_env_explicito_le_o_ambiente_real(monkeypatch, tmp_path):
    """Exercita Config.load() com env=None (linha 67: env = _real_env())"""
    monkeypatch.setenv("HOTKEY", "F9")
    # Limpar vars que podem estar no .env real para evitar flakiness
    monkeypatch.delenv("PROVIDER", raising=False)
    monkeypatch.delenv("TRANSCRIPTION_MODEL", raising=False)
    monkeypatch.delenv("CLEANUP_MODEL", raising=False)
    monkeypatch.delenv("LANGUAGE", raising=False)
    monkeypatch.delenv("ENABLE_CLEANUP", raising=False)
    monkeypatch.delenv("SAMPLE_RATE", raising=False)

    cfg = Config.load(path=tmp_path / "config.json")
    # Valida que o .env foi lido (sem env= explícito)
    # e que a normalização para minúsculas funciona
    assert cfg.hotkey == "f9"


def test_migracao_sem_env_explicito_le_o_ambiente_real(monkeypatch, tmp_path):
    """Exercita migrate_env_key_if_needed() com env=None.

    Testa linha 90: env = _real_env()
    """
    monkeypatch.setenv("GROQ_API_KEY", "gsk_ambiente")
    chamadas = []
    ok = migrate_env_key_if_needed(
        path=tmp_path / "config.json",
        set_key=lambda prov, key: chamadas.append((prov, key)),
    )
    assert ok is True
    assert chamadas == [("groq", "gsk_ambiente")]
