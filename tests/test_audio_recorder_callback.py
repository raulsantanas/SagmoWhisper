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

    # DESIGN-001: Math correctness assertion
    # For input [[0.3], [0.4], [0.5]], RMS = sqrt(mean([0.09, 0.16, 0.25])) = sqrt(0.1667) ≈ 0.4082
    expected_rms = float(np.sqrt(np.mean(np.array([[0.3], [0.4], [0.5]], dtype=np.float32) ** 2)))
    assert abs(rms_value - expected_rms) < 0.001, f"RMS mismatch: got {rms_value}, expected ≈ {expected_rms}"


def test_no_callback_does_not_raise():
    """Verify that _on_audio succeeds silently when no callback is provided."""
    with patch("sounddevice.InputStream"):
        from src.audio_recorder import AudioRecorder
        recorder = AudioRecorder(sample_rate=16000)
        # Explicitly verify no callback path
        assert recorder._sample_callback is None

        indata = np.array([[0.3]], dtype=np.float32)
        # Should not raise any exception
        try:
            recorder._on_audio(indata, 1, None, None)
            callback_path_success = True
        except Exception as e:
            callback_path_success = False
            raise AssertionError(f"No-callback path raised exception: {e}")

        assert callback_path_success
