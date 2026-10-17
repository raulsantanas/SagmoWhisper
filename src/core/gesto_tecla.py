"""Gesto da tecla de gravação: segurar sozinha grava, soltar conclui (DEC-PV-009).

A gravação começa no instante em que a tecla desce; quem decide se ela vale é o
soltar. Por isso toque curto e combinação com outra tecla *cancelam* (o
gravador já foi ligado e precisa ser descartado) em vez de simplesmente não
iniciar.
"""
import time

TOQUE_MINIMO_S = 0.3


class GestoTecla:
    def __init__(self, tecla, ao_iniciar, ao_concluir, ao_cancelar,
                 relogio=time.monotonic):
        self._tecla = tecla
        self._ao_iniciar = ao_iniciar
        self._ao_concluir = ao_concluir
        self._ao_cancelar = ao_cancelar
        self._relogio = relogio
        self._inicio = None
        self._combinada = False

    @property
    def _gravando(self):
        return self._inicio is not None

    def pressionar(self, tecla):
        if tecla == self._tecla:
            self._iniciar()
        elif self._gravando:
            self._combinada = True

    def soltar(self, tecla):
        if tecla != self._tecla or not self._gravando:
            return
        duracao = self._relogio() - self._inicio
        self._inicio = None
        if self._combinada or duracao < TOQUE_MINIMO_S:
            self._ao_cancelar()
        else:
            self._ao_concluir()

    def abandonar(self):
        """Esquece a gravação em curso sem avisar ninguém (o gravador falhou)."""
        self._inicio = None

    def _iniciar(self):
        if self._gravando:
            return
        self._inicio = self._relogio()
        self._combinada = False
        self._ao_iniciar()
