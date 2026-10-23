import threading
from pathlib import Path

from src.core.voz import VOZ_PADRAO, VozEdge


class _Player:
    """Processo de áudio falso: wait() só volta quando o som 'acaba'."""

    def __init__(self, caminho: Path, tocados: list):
        tocados.append(caminho.read_text(encoding="utf-8"))
        self.acabou = threading.Event()
        self.interrompido = False

    def wait(self):
        self.acabou.wait(timeout=5)

    def terminate(self):
        self.interrompido = True
        self.acabou.set()


class _Falso:
    def __init__(self, segurar=False):
        self.tocados = []
        self.players = []
        self.vozes = []
        self.tocando = threading.Event()
        self._segurar = segurar

    def sintetizar(self, texto: str, voz: str, destino: Path) -> None:
        if texto == "sem internet":
            raise OSError("sem internet")
        self.vozes.append(voz)
        destino.write_text(texto, encoding="utf-8")

    def tocar(self, caminho: Path):
        player = _Player(caminho, self.tocados)
        self.players.append(player)
        if not self._segurar:
            player.acabou.set()
        self.tocando.set()
        return player


def _voz(falso: _Falso) -> VozEdge:
    return VozEdge(sintetizar=falso.sintetizar, tocar=falso.tocar)


def test_fala_as_frases_em_ordem_com_a_francisca():
    falso = _Falso()
    voz = _voz(falso)

    voz.falar("primeira")
    voz.falar("segunda")
    voz.esperar()

    assert falso.tocados == ["primeira", "segunda"]
    assert falso.vozes == [VOZ_PADRAO, VOZ_PADRAO]
    assert VOZ_PADRAO == "pt-BR-FranciscaNeural"


def test_falar_nao_bloqueia_quem_chama():
    falso = _Falso(segurar=True)
    voz = _voz(falso)

    voz.falar("frase longa")

    assert falso.tocando.wait(timeout=2)
    assert not falso.players[0].acabou.is_set()
    voz.interromper()


def test_interromper_corta_a_fala_atual_e_descarta_a_fila():
    falso = _Falso(segurar=True)
    voz = _voz(falso)
    voz.falar("atual")
    falso.tocando.wait(timeout=2)
    voz.falar("pendente")

    voz.interromper()
    voz.esperar()

    assert falso.players[0].interrompido
    assert falso.tocados == ["atual"]


def test_depois_de_interromper_volta_a_falar():
    falso = _Falso(segurar=True)
    voz = _voz(falso)
    voz.falar("atual")
    falso.tocando.wait(timeout=2)
    voz.interromper()

    falso._segurar = False
    voz.falar("nova")
    voz.esperar()

    assert falso.tocados == ["atual", "nova"]


def test_interromper_sem_nada_tocando_nao_quebra():
    voz = _voz(_Falso())

    voz.interromper()


def test_falha_na_sintese_loga_e_segue_para_a_proxima(caplog):
    falso = _Falso()
    voz = _voz(falso)

    voz.falar("sem internet")
    voz.falar("depois")
    voz.esperar()

    assert falso.tocados == ["depois"]
    assert "sem internet" in caplog.text


def test_texto_vazio_nao_vira_fala():
    falso = _Falso()
    voz = _voz(falso)

    voz.falar("   ")
    voz.esperar()

    assert falso.tocados == []


def test_arquivo_de_audio_temporario_e_apagado(tmp_path):
    falso = _Falso()
    caminhos = []

    def tocar(caminho):
        caminhos.append(caminho)
        return falso.tocar(caminho)

    voz = VozEdge(sintetizar=falso.sintetizar, tocar=tocar)
    voz.falar("oi")
    voz.esperar()

    assert not caminhos[0].exists()
