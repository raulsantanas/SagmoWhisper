import queue
import tempfile
import threading
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int,
        sample_callback: Callable | None = None,
        start_grace_timeout: float = 1.0,
    ):
        self._sample_rate = sample_rate
        self._sample_callback = sample_callback
        self._start_grace_timeout = start_grace_timeout
        self._queue: queue.Queue = queue.Queue()
        self._first_block = threading.Event()
        self._stream = None

    def start(self) -> None:
        self._queue = queue.Queue()
        self._first_block = threading.Event()
        self._stream = sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self) -> Path:
        # Pa_StartStream retorna antes de o CoreAudio concluir o start
        # assíncrono; stop() nessa janela deadlocka o PortAudio
        # (AudioOutputUnitStop segura o HALB_Mutex enquanto o IOThread espera
        # o mutex do AudioUnit no startStopCallback) e congela o app. O 1º
        # bloco de áudio prova que o stream está ativo; o timeout evita
        # esperar para sempre com mic mudo/sem permissão.
        self._first_block.wait(self._start_grace_timeout)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        return self._write_wav(self._drain())

    def _on_audio(self, indata, frames, time, status):
        self._first_block.set()
        self._queue.put(indata.copy())
        if self._sample_callback is not None:
            rms = float(np.sqrt(np.mean(indata ** 2)))
            self._sample_callback(rms)

    def _drain(self) -> list:
        blocks = []
        while not self._queue.empty():
            blocks.append(self._queue.get())
        return blocks

    def _write_wav(self, blocks: list) -> Path:
        path = Path(tempfile.gettempdir()) / "voz_recording.wav"
        audio = np.concatenate(blocks) if blocks else np.zeros((1, 1))
        sf.write(path, audio, self._sample_rate)
        return path
