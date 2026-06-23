import numpy as np
from unittest.mock import MagicMock, patch


def test_sample_callback_called_with_float_rms():
    callback = MagicMock()

    with patch("sounddevice.InputStream") as mock_stream_cls:
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000, sample_callback=callback)

        # Simula bloco de áudio chegando
        indata = np.array([[0.3], [0.4], [0.5]], dtype=np.float32)
        recorder._on_audio(indata, 3, None, None)

    assert callback.called
    rms_value = callback.call_args[0][0]
    assert isinstance(rms_value, float)
    assert rms_value > 0.0


def test_no_callback_does_not_raise():
    with patch("sounddevice.InputStream"):
        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000)
        indata = np.array([[0.3]], dtype=np.float32)
        recorder._on_audio(indata, 1, None, None)  # não deve lançar exceção
