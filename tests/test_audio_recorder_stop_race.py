import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np


def _block():
    return np.zeros((4, 1), dtype=np.float32)


def test_stop_waits_for_first_audio_block_before_stopping_stream():
    """Regressão (2026-07-10): stop() durante o start assíncrono do CoreAudio
    deadlocka o PortAudio (AudioOutputUnitStop × startStopCallback) e congela
    o app. stop() deve esperar o primeiro bloco de áudio — prova de que o
    stream está ativo — antes de parar o stream."""
    events = []
    with patch("sounddevice.InputStream") as mock_stream_cls:
        mock_stream = MagicMock()
        mock_stream.stop.side_effect = lambda: events.append("stream_stop")
        mock_stream_cls.return_value = mock_stream

        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000)
        recorder.start()

        def feed_first_block_after_delay():
            time.sleep(0.2)
            events.append("first_block")
            recorder._on_audio(_block(), 4, None, None)

        feeder = threading.Thread(target=feed_first_block_after_delay)
        feeder.start()
        recorder.stop()
        feeder.join()

    assert events == ["first_block", "stream_stop"]


def test_stop_without_audio_proceeds_after_grace_timeout():
    """Mic sem permissão/mudo nunca entrega bloco — stop() não pode esperar
    para sempre; após o grace timeout ele para e fecha o stream mesmo assim."""
    with patch("sounddevice.InputStream") as mock_stream_cls:
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000, start_grace_timeout=0.05)
        recorder.start()
        path = recorder.stop()

    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()
    assert path.exists()
