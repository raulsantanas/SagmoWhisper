import os
import subprocess

import pytest

from src.core.single_instance import (
    AlreadyRunningError,
    acquire_lock,
    release_lock,
)


def test_acquire_grava_pid_proprio(tmp_path):
    lock = tmp_path / "app.lock"
    acquire_lock(lock)
    assert lock.read_text() == str(os.getpid())


def test_acquire_falha_se_pid_do_lock_esta_vivo(tmp_path):
    lock = tmp_path / "app.lock"
    lock.write_text(str(os.getpid()))
    with pytest.raises(AlreadyRunningError):
        acquire_lock(lock)


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
