"""RED (bug de produção 2026-09-19): AudioRecorder não tem guarda de estado
quando o microfone está indisponível (permissão TCC revogada após reinstalar
o .app).

Log real:
    AttributeError: 'NoneType' object has no attribute 'stop'
    app.py:198 _handle_recording -> audio_recorder.py:44 stop

Contrato fixado aqui (ainda NÃO implementado — próximo passo é o desenvolvedor):

1. stop() chamado sem start() bem-sucedido (_stream is None) NÃO pode vazar o
   AttributeError cru do 'NoneType'; deve levantar um erro de domínio tipado
   (RecordingUnavailableError) e deixar o recorder em estado consistente.
2. start() cujo sd.InputStream(...) (construtor) lança deve deixar _stream em
   None e propagar RecordingUnavailableError em vez da exceção crua do PortAudio.
3. start() cujo _stream.start() interno lança não pode deixar um stream
   nunca-iniciado pendurado: _stream volta a None e propaga
   RecordingUnavailableError.

Nome/local do erro: RecordingUnavailableError em src/audio_recorder.py — segue a
convenção de co-localização do projeto (TranscriptionError vive junto dos
providers que o levantam, em src/core/providers/base.py). Item 1 e item 2/3
compartilham o MESMO tipo: mesma causa-raiz (mic/stream indisponível) e a UI os
trata de forma idêntica.

As asserções checam o tipo pelo nome (type(exc).__name__) de propósito: assim a
coleta do pytest não quebra por ImportError de um símbolo ainda inexistente, e o
RED falha pelo COMPORTAMENTO (exceção errada / estado inconsistente), não por
erro de import.
"""
import pytest
from unittest.mock import MagicMock, patch

DOMAIN_ERROR = "RecordingUnavailableError"


def test_stop_without_successful_start_raises_domain_error_not_attributeerror():
    from src.audio_recorder import AudioRecorder

    recorder = AudioRecorder(sample_rate=16000)  # start() nunca chamado
    assert recorder._stream is None

    with pytest.raises(Exception) as exc_info:
        recorder.stop()

    assert not isinstance(exc_info.value, AttributeError), (
        "stop() vazou o AttributeError cru do 'NoneType' — deve ser erro "
        "de domínio tipado"
    )
    assert type(exc_info.value).__name__ == DOMAIN_ERROR, (
        f"stop() sem start() deve levantar {DOMAIN_ERROR}, veio "
        f"{type(exc_info.value).__name__}"
    )
    assert recorder._stream is None, "stop() com falha deixou stream pendurado"


def test_start_raises_domain_error_when_inputstream_construction_fails():
    from src.audio_recorder import AudioRecorder

    boom = OSError("PortAudioError: mic permission denied (TCC)")
    with patch("sounddevice.InputStream", side_effect=boom):
        recorder = AudioRecorder(sample_rate=16000)
        with pytest.raises(Exception) as exc_info:
            recorder.start()

    assert type(exc_info.value).__name__ == DOMAIN_ERROR, (
        f"start() deve traduzir a falha do construtor do PortAudio em "
        f"{DOMAIN_ERROR}, veio {type(exc_info.value).__name__}"
    )
    assert recorder._stream is None


def test_start_leaves_no_dangling_stream_when_stream_start_fails():
    from src.audio_recorder import AudioRecorder

    mock_stream = MagicMock()
    mock_stream.start.side_effect = OSError("PortAudioError: -9986 start failed")
    with patch("sounddevice.InputStream", return_value=mock_stream):
        recorder = AudioRecorder(sample_rate=16000)
        with pytest.raises(Exception) as exc_info:
            recorder.start()

    assert type(exc_info.value).__name__ == DOMAIN_ERROR, (
        f"start() deve traduzir a falha do _stream.start() em {DOMAIN_ERROR}, "
        f"veio {type(exc_info.value).__name__}"
    )
    assert recorder._stream is None, (
        "_stream.start() falhou mas o stream nunca-iniciado ficou pendurado; "
        "stop() depois tentaria parar um stream inválido"
    )
