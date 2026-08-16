"""Utilidades compartidas por los tests (no descubierto por unittest)."""

import random
import unittest
from unittest.mock import patch

from age_of_conquest import estado
from age_of_conquest.estado import GameState
from age_of_conquest.mapa import Territorio


class RngStub(random.Random):
    """Generador determinista que devuelve la secuencia indicada."""

    def __init__(self, valores):
        super().__init__(0)
        self.valores = list(valores)
        self.i = 0

    def randint(self, a, b):
        v = self.valores[self.i % len(self.valores)]
        self.i += 1
        return v

    def random(self):
        # consume el siguiente valor como fraccion [0,1) para tests de
        # muestreo Monte Carlo (rebelion).
        if self.i < len(self.valores):
            v = self.valores[self.i]
            self.i += 1
            return min(max(v, 0.0), 0.999999)
        return super().random()


class MapaStub:
    """Mapa falso con un unico territorio y terreno fijo configurable."""

    def __init__(self, terreno=0):
        self.terreno_fijo = terreno
        # Continente 99: no existe en CONTINENTE_BONUS_* (sin bonus)
        self.territorios = [
            Territorio(id=0, nombre="X", continente=99, terreno=terreno)
        ]
        self.territorios_continente = {99: [0]}
        self.adyacencias = {0: []}

    def territorio(self, i):
        return self.territorios[0]

    def vecinos(self, i):
        return []

    def son_adyacentes(self, i, k):
        return False


def nuevo_estado(terreno=0):
    """GameState minimo con un jugador y una provincia (id=0)."""
    with patch.object(estado, "MAPA", MapaStub(terreno)):
        s = GameState()
        s.inicializar_provincias()
    return s


class MapaParcheadoTestCase(unittest.TestCase):
    """TestCase que mantiene el mapa stub activo durante toda la prueba."""

    def setUp(self):
        self.patcher = patch.object(estado, "MAPA", MapaStub(0))
        self.patcher.start()
        self.estado = GameState()
        self.estado.inicializar_provincias()

    def tearDown(self):
        self.patcher.stop()
