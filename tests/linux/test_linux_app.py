from pathlib import Path

from src.linux.app import LinuxApp

HOTKEY = object()
OUTRA_TECLA = object()


class _SpyRecorder:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")
        return Path("rec.wav")


class _SpyPipeline:
    def __init__(self, result="texto colado", error=None):
        self.calls = []
        self._result = result
        self._error = error

    def run(self, audio_path):
        self.calls.append(audio_path)
        if self._error:
            raise self._error
        return self._result


class _RelogioQueAvanca:
    """Cada leitura avança 1 s: segurar e soltar sempre passa do toque mínimo."""

    def __init__(self, passo=1.0):
        self._agora = 0.0
        self._passo = passo

    def __call__(self):
        self._agora += self._passo
        return self._agora


def _app(pipeline=None, relogio=None):
    recorder = _SpyRecorder()
    echoed = []
    app = LinuxApp(
        recorder=recorder,
        pipeline=pipeline or _SpyPipeline(),
        hotkey=HOTKEY,
        echo=echoed.append,
        relogio=relogio or _RelogioQueAvanca(),
    )
    return app, recorder, echoed


def test_segurar_f8_inicia_gravacao_uma_vez_so():
    app, recorder, _ = _app()
    app.on_press(HOTKEY)
    app.on_press(HOTKEY)  # auto-repeat do X11 não reinicia
    assert recorder.calls == ["start"]


def test_outra_tecla_nao_grava():
    app, recorder, _ = _app()
    app.on_press(OUTRA_TECLA)
    assert recorder.calls == []


def test_soltar_f8_para_transcreve_e_anuncia():
    pipeline = _SpyPipeline(result="olá mundo")
    app, recorder, echoed = _app(pipeline)
    app.on_press(HOTKEY)
    app.on_release(HOTKEY)
    assert recorder.calls == ["start", "stop"]
    assert pipeline.calls == [Path("rec.wav")]
    assert any("olá mundo" in m for m in echoed)


def test_soltar_tecla_diferente_durante_gravacao_nao_interrompe():
    pipeline = _SpyPipeline()
    app, recorder, _ = _app(pipeline)
    app.on_press(HOTKEY)
    app.on_release(OUTRA_TECLA)
    assert recorder.calls == ["start"]
    assert pipeline.calls == []


def test_soltar_sem_ter_gravado_nao_faz_nada():
    pipeline = _SpyPipeline()
    app, recorder, _ = _app(pipeline)
    app.on_release(HOTKEY)
    assert recorder.calls == []
    assert pipeline.calls == []


def test_erro_na_transcricao_vira_mensagem_e_nao_derruba():
    pipeline = _SpyPipeline(error=RuntimeError("groq: sem rede"))
    app, _, echoed = _app(pipeline)
    app.on_press(HOTKEY)
    app.on_release(HOTKEY)
    assert any("sem rede" in m for m in echoed)


def test_gravacao_vazia_avisa_que_nada_foi_colado():
    pipeline = _SpyPipeline(result="")
    app, _, echoed = _app(pipeline)
    app.on_press(HOTKEY)
    app.on_release(HOTKEY)
    assert any("vazia" in m for m in echoed)


def test_combinacao_durante_gravacao_descarta_sem_transcrever():
    pipeline = _SpyPipeline()
    app, recorder, _ = _app(pipeline)
    app.on_press(HOTKEY)
    app.on_press(OUTRA_TECLA)
    app.on_release(HOTKEY)
    assert recorder.calls == ["start", "stop"]
    assert pipeline.calls == []


def test_toque_curto_descarta_sem_transcrever():
    pipeline = _SpyPipeline()
    app, recorder, _ = _app(pipeline, relogio=_RelogioQueAvanca(passo=0.0))
    app.on_press(HOTKEY)
    app.on_release(HOTKEY)
    assert recorder.calls == ["start", "stop"]
    assert pipeline.calls == []
