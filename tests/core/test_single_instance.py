import os
import subprocess

import pytest

from src.core import single_instance
from src.core.single_instance import (
    AlreadyRunningError,
    acquire_lock,
    release_lock,
)


def test_acquire_grava_pid_proprio(tmp_path):
    lock = tmp_path / "app.lock"
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_acquire_falha_se_pid_do_lock_e_sagmowhisper_vivo(tmp_path, monkeypatch):
    monkeypatch.setattr(
        single_instance,
        "_pid_command",
        lambda pid: "/Applications/SagmoWhisper.app/Contents/MacOS/SagmoWhisper",
    )
    lock = tmp_path / "app.lock"
    lock.write_text(str(os.getpid()))
    with pytest.raises(AlreadyRunningError):
        acquire_lock(lock)


def test_acquire_assume_lock_de_pid_reciclado_por_outro_processo(tmp_path):
    # Simula reuso de PID após crash/reboot sem release do lock:
    # o PID do lock está vivo, mas pertence a outro processo.
    proc = subprocess.Popen(["sleep", "30"])
    try:
        lock = tmp_path / "app.lock"
        lock.write_text(str(proc.pid))
        acquire_lock(lock)
        assert lock.read_text() == str(os.getpid())
    finally:
        proc.kill()
        proc.wait()


def test_acquire_assume_lock_orfao_de_processo_morto(tmp_path):
    proc = subprocess.Popen(["true"])
    proc.wait()
    lock = tmp_path / "app.lock"
    lock.write_text(str(proc.pid))
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_acquire_assume_lock_com_conteudo_invalido(tmp_path):
    lock = tmp_path / "app.lock"
    lock.write_text("lixo")
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_release_remove_e_e_idempotente(tmp_path):
    lock = tmp_path / "app.lock"
    acquire_lock(lock)
    release_lock(lock)
    assert not lock.exists()
    release_lock(lock)  # não levanta
