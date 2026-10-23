import json

import pytest

import src.core.config as config_module
from src.core.config import (
    DEFAULTS,
    HOTKEYS_SUPORTADAS,
    Config,
    hotkey_do_rotulo,
    rotulo_hotkey,
    migrate_env_key_if_needed,
)


def test_load_sem_json_e_sem_env_usa_defaults(tmp_path):
    cfg = Config.load(path=tmp_path / "config.json", env={})
    assert cfg.provider == "groq"
    assert cfg.transcription_model == "whisper-large-v3-turbo"
    assert cfg.cleanup_model == "openai/gpt-oss-120b"
    assert cfg.language == "pt"
    assert cfg.enable_cleanup is True
    assert cfg.hotkey == "ctrl_r"
    assert cfg.sample_rate == 16000
    assert cfg.voice_port == 47821


def test_voice_port_vem_do_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"voice_port": 50123}))

    assert Config.load(path=p, env={}).voice_port == 50123


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


def test_caminho_padrao_no_mac_fica_em_application_support():
    from src.core.config import default_config_path

    path = default_config_path(platform="darwin")
    assert "Library/Application Support/SagmoWhisper" in str(path)
    assert path.name == "config.json"


def test_caminho_padrao_no_linux_segue_xdg_default():
    from src.core.config import default_config_path

    path = default_config_path(platform="linux", env={})
    assert str(path).endswith(".config/sagmowhisper/config.json")


def test_caminho_no_linux_respeita_xdg_config_home():
    from src.core.config import default_config_path

    path = default_config_path(
        platform="linux", env={"XDG_CONFIG_HOME": "/tmp/xdg"}
    )
    assert str(path) == "/tmp/xdg/sagmowhisper/config.json"


# 19/09/2026: Groq removeu llama-3.3-70b-versatile (404 model_not_found) e
# mantém bloqueados (403 model_permission_blocked_org) os chat models legados.
# whisper-large-v3 também está bloqueado (403). Config salva com qualquer um
# deles — via JSON ou env var — migra para o default vigente no load.
# 17/10/2026: os Llamas sumiram da Groq (llama-4-scout também dá 404) e o
# Raul liberou só openai/gpt-oss-120b na org — ele volta a ser o default.
_NOVO_DEFAULT_CLEANUP = "openai/gpt-oss-120b"
_DEFAULT_TRANSCRICAO = "whisper-large-v3-turbo"

_MODELOS_LIMPEZA_BLOQUEADOS = [
    "openai/gpt-oss-20b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]

_MODELOS_TRANSCRICAO_BLOQUEADOS = ["whisper-large-v3"]


@pytest.mark.parametrize("bloqueado", _MODELOS_LIMPEZA_BLOQUEADOS)
def test_modelo_de_limpeza_bloqueado_no_json_migra_para_o_default(
    tmp_path, bloqueado
):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"cleanup_model": bloqueado}))
    cfg = Config.load(path=p, env={})
    assert cfg.cleanup_model == _NOVO_DEFAULT_CLEANUP


@pytest.mark.parametrize("bloqueado", _MODELOS_LIMPEZA_BLOQUEADOS)
def test_modelo_de_limpeza_bloqueado_no_env_tambem_migra(tmp_path, bloqueado):
    cfg = Config.load(
        path=tmp_path / "c.json",
        env={"CLEANUP_MODEL": bloqueado},
    )
    assert cfg.cleanup_model == _NOVO_DEFAULT_CLEANUP


@pytest.mark.parametrize("bloqueado", _MODELOS_TRANSCRICAO_BLOQUEADOS)
def test_modelo_de_transcricao_bloqueado_no_json_migra_para_o_default(
    tmp_path, bloqueado
):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"transcription_model": bloqueado}))
    cfg = Config.load(path=p, env={})
    assert cfg.transcription_model == _DEFAULT_TRANSCRICAO


@pytest.mark.parametrize("bloqueado", _MODELOS_TRANSCRICAO_BLOQUEADOS)
def test_modelo_de_transcricao_bloqueado_no_env_tambem_migra(
    tmp_path, bloqueado
):
    # Vetor real do crash de 19/09: TRANSCRIPTION_MODEL vinha via env var.
    cfg = Config.load(
        path=tmp_path / "c.json",
        env={"TRANSCRIPTION_MODEL": bloqueado},
    )
    assert cfg.transcription_model == _DEFAULT_TRANSCRICAO


def test_valores_validos_de_modelo_passam_intactos(tmp_path):
    # Regressão: os defaults vigentes não podem ser migrados por engano.
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps(
            {
                "transcription_model": _DEFAULT_TRANSCRICAO,
                "cleanup_model": _NOVO_DEFAULT_CLEANUP,
            }
        )
    )
    cfg = Config.load(path=p, env={})
    assert cfg.transcription_model == _DEFAULT_TRANSCRICAO
    assert cfg.cleanup_model == _NOVO_DEFAULT_CLEANUP


def test_modelo_de_limpeza_fora_do_conjunto_e_preservado(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"cleanup_model": "gpt-4o-mini"}))
    cfg = Config.load(path=p, env={})
    assert cfg.cleanup_model == "gpt-4o-mini"


def test_defaults_nunca_sao_modelos_depreciados():
    # Guarda anti-causa-raiz: o crash de 19/09 foi um default que virou modelo
    # morto sem ninguém atualizar. Esta invariante trava toda futura
    # depreciação que esqueça de mover o default para um modelo vivo.
    assert (
        config_module.DEFAULTS["cleanup_model"]
        not in config_module._DEPRECATED_CLEANUP_MODELS
    )
    assert (
        config_module.DEFAULTS["transcription_model"]
        not in config_module._DEPRECATED_TRANSCRIPTION_MODELS
    )


def test_control_direito_e_f8_estao_entre_as_teclas_suportadas():
    assert "ctrl_r" in HOTKEYS_SUPORTADAS
    assert "f8" in HOTKEYS_SUPORTADAS


def test_config_com_f8_continua_aceito(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"hotkey": "f8"}))
    cfg = Config.load(path=p, env={})
    assert cfg.hotkey == "f8"


def test_rotulo_do_control_direito_e_legivel_na_janela():
    assert rotulo_hotkey("ctrl_r") == "Control direito"
    assert rotulo_hotkey("f8") == "F8"


def test_rotulo_escolhido_na_janela_volta_ao_nome_do_config():
    assert hotkey_do_rotulo("Control direito") == "ctrl_r"
    assert hotkey_do_rotulo("F8") == "f8"


def test_command_direito_e_suportado_para_teclado_de_pc_remapeado():
    # Teclado de PC com Control↔Command trocado no macOS: o "Ctrl" físico da
    # direita chega como cmd_r.
    assert "cmd_r" in HOTKEYS_SUPORTADAS
    assert rotulo_hotkey("cmd_r") == "Command direito"
    assert hotkey_do_rotulo("Command direito") == "cmd_r"
