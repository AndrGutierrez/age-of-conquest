"""Tests unitarios del motor de simulacion (LEF, fases, victoria)."""

import random
import unittest
from unittest.mock import patch

from age_of_conquest import estado
from age_of_conquest.config import Config
from age_of_conquest.estado import GameState
from age_of_conquest.motor import FASE_REFUERZO, PRIO_REFUERZO, ControladorJugador, Motor

from tests.helpers import MiniMapa


class ColocadorFijo(ControladorJugador):
    """Coloca todos los refuerzos en el primer territorio del jugador."""

    def colocar_refuerzos(self, estado, jugador, cantidad):
        destino = estado.territorios_de(jugador.id)[0]
        estado.provincias[destino].ejercitos += cantidad

    def fase_ataque(self, motor, estado, jugador):
        pass

    def fase_movimiento(self, motor, estado, jugador):
        pass


class Atacante(ControladorJugador):
    """Ataca (origen, destino) una vez en su fase de ataque, si es posible."""

    def __init__(self, origen, destino, max_rondas=None):
        self.origen = origen
        self.destino = destino
        self.max_rondas = max_rondas

    def colocar_refuerzos(self, estado, jugador, cantidad):
        estado.provincias[self.origen].ejercitos += cantidad

    def fase_ataque(self, motor, estado, jugador):
        motor.ejecutar_ataque(self.origen, self.destino, self.max_rondas)

    def fase_movimiento(self, motor, estado, jugador):
        pass


class MotorTestCase(unittest.TestCase):
    """Base: estado sobre un mini mapa de 4 territorios en anillo."""

    def setUp(self):
        self.patcher = patch.object(estado, "MAPA", MiniMapa(4))
        self.patcher.start()
        self.estado = GameState()
        self.estado.inicializar_provincias()
        self.rng = random.Random(42)
        self.motor = Motor(self.estado, {}, self.rng)

    def tearDown(self):
        self.patcher.stop()

    def programar_ronda(self, p=1):
        self.motor._programar(FASE_REFUERZO, p, PRIO_REFUERZO)


class TestReparto(MotorTestCase):
    def test_reparto_cubre_todo_el_mapa(self):
        self.estado.crear_jugador("P1")
        self.estado.crear_jugador("P2")
        self.motor._repartir_mapa()
        duenos = {prov.dueno for prov in self.estado.provincias.values()}
        self.assertEqual(duenos, {1, 2})
        for prov in self.estado.provincias.values():
            self.assertEqual(prov.ejercitos, self.estado.config.ejercitos_iniciales)


class TestRefuerzos(MotorTestCase):
    def test_formula_base(self):
        # r = max(r_min, floor(T/rho)); con 2 territorios: max(3, 0) = 3
        self.estado.crear_jugador("P1")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[1].dueno = 1
        self.assertEqual(self.motor.refuerzos_totales(1), 3)
        # 9 territorios -> 9//3 = 3; 12 territorios -> 4
        self.estado.provincias[2].dueno = 1
        self.estado.provincias[3].dueno = 1  # 4 territorios -> 4//3 = 1 -> 3

    def test_formula_bonus_continente(self):
        # En el mapa real: poseer toda Oceania (4 territorios) suma b_c = 2
        from age_of_conquest.mapa import MAPA as MAPA_REAL

        with patch.object(estado, "MAPA", MAPA_REAL):
            s = GameState()
            s.inicializar_provincias()
            s.crear_jugador("P1")
            for i in MAPA_REAL.territorios_continente[5]:  # Oceania
                s.provincias[i].dueno = 1
            m = Motor(s, {}, self.rng)
            self.assertEqual(m.refuerzos_totales(1), 3 + 2)


class TestCicloDeRondas(MotorTestCase):
    def test_tres_rondas_sin_combate(self):
        self.estado.crear_jugador("P1")
        self.estado.crear_jugador("P2")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[1].dueno = 1
        self.estado.provincias[2].dueno = 2
        self.estado.provincias[3].dueno = 2
        self.motor.controladores = {
            1: ColocadorFijo(),
            2: ColocadorFijo(),
        }
        self.programar_ronda(1)
        self.motor.ejecutar(max_turnos=3)
        self.assertEqual(self.estado.turno, 3)
        self.assertEqual(self.estado.jugadores_activos(), [1, 2])
        # La economia liquido tesoros en cada FIN_TURNO
        self.assertGreater(self.estado.jugadores[1].tesoro, 0.0)
        self.assertGreater(self.estado.jugadores[2].tesoro, 0.0)
        # El crecimiento logistico y la felicidad se actualizaron
        self.assertGreater(self.estado.provincias[0].poblacion, 500.0)
        self.assertLess(self.estado.provincias[0].felicidad, 0.80)

    def test_turnos_alternados(self):
        # El jugador 1 juega primero; verifica el orden de FIN_TURNO
        orden = []
        self.estado.crear_jugador("P1")
        self.estado.crear_jugador("P2")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[1].dueno = 1
        self.estado.provincias[2].dueno = 2
        self.estado.provincias[3].dueno = 2
        motor = self.motor
        original = motor._fin_turno

        def fin_turno_registrado(p):
            orden.append(p)
            original(p)

        motor._fin_turno = fin_turno_registrado
        motor.controladores = {1: ColocadorFijo(), 2: ColocadorFijo()}
        self.programar_ronda(1)
        motor.ejecutar(max_turnos=2)
        self.assertEqual(orden, [1, 2, 1, 2])


class TestAtaqueYEliminacion(MotorTestCase):
    def test_eliminacion_por_conquista_y_victoria(self):
        # Mapa de 2 territorios (0 adyacente a 1): P1 arrasa a P2
        with patch.object(estado, "MAPA", MiniMapa(2)):
            self.estado = GameState()
            self.estado.inicializar_provincias()
            self.estado.crear_jugador("P1")
            self.estado.crear_jugador("P2")
            self.estado.provincias[0].dueno = 1
            self.estado.provincias[0].ejercitos = 20
            self.estado.provincias[1].dueno = 2
            self.estado.provincias[1].ejercitos = 1
            self.motor = Motor(
                self.estado,
                {1: Atacante(0, 1), 2: ColocadorFijo()},
                random.Random(1),
            )
            self.programar_ronda(1)
            self.motor.ejecutar()
            self.assertFalse(self.estado.jugadores[2].activo)
            self.assertEqual(self.estado.ganador, 1)
            self.assertFalse(self.estado.simulacion_activa)
            self.assertEqual(self.estado.provincias[1].dueno, 1)
            # la conquista transfiere al menos 1 tropa
            self.assertGreaterEqual(self.estado.provincias[1].ejercitos, 1)

    def test_ataques_invalidos(self):
        self.estado.crear_jugador("P1")
        self.estado.crear_jugador("P2")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[0].ejercitos = 5
        self.estado.provincias[1].dueno = 2
        self.estado.jugador_activo = 1
        with self.assertRaises(ValueError):
            self.motor.ejecutar_ataque(2, 1)  # no es territorio propio
        with self.assertRaises(ValueError):
            self.motor.ejecutar_ataque(0, 2)  # no adyacentes (0-2 en anillo)
        with self.assertRaises(ValueError):
            self.motor.ejecutar_ataque(1, 2)  # territorio enemigo como origen
        self.estado.provincias[3].dueno = 1
        self.estado.provincias[3].ejercitos = 1
        with self.assertRaises(ValueError):
            self.motor.ejecutar_ataque(3, 2)  # A < 2: ataque no viable


class TestMovimiento(MotorTestCase):
    def test_movimiento_valido(self):
        self.estado.crear_jugador("P1")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[0].ejercitos = 10
        self.estado.provincias[1].dueno = 1
        self.estado.provincias[1].ejercitos = 2
        self.estado.jugador_activo = 1
        self.assertTrue(self.motor.ejecutar_movimiento(0, 1, 5))
        self.assertEqual(self.estado.provincias[0].ejercitos, 5)
        self.assertEqual(self.estado.provincias[1].ejercitos, 7)

    def test_movimientos_invalidos(self):
        self.estado.crear_jugador("P1")
        self.estado.crear_jugador("P2")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[0].ejercitos = 10
        self.estado.provincias[1].dueno = 2
        self.estado.jugador_activo = 1
        with self.assertRaises(ValueError):
            self.motor.ejecutar_movimiento(0, 1, 3)  # destino enemigo
        with self.assertRaises(ValueError):
            self.motor.ejecutar_movimiento(0, 0, 3)  # mismo territorio
        with self.assertRaises(ValueError):
            self.motor.ejecutar_movimiento(0, 2, 3)  # no adyacentes (anillo)
        self.estado.provincias[3].dueno = 1
        with self.assertRaises(ValueError):
            self.motor.ejecutar_movimiento(0, 3, 10)  # n >= A(origen)
        with self.assertRaises(ValueError):
            self.motor.ejecutar_movimiento(0, 3, 0)  # n < 1


class TestEliminacionPorRebelion(MotorTestCase):
    def test_jugador_pierde_su_ultimo_territorio_por_rebelion(self):
        # Config literal del documento (sin termino de calibracion) para
        # probar el caso borde de la Seccion 2.8: H = 0 -> pi = 1.
        self.estado = GameState(Config(delta_eq=0.0))
        self.estado.inicializar_provincias()
        self.motor = Motor(self.estado, {}, self.rng)
        self.estado.crear_jugador("P1")
        self.estado.crear_jugador("P2")
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[0].felicidad = 0.0  # rebelion segura
        self.estado.provincias[1].dueno = 2
        self.estado.provincias[1].felicidad = 0.9
        self.motor.controladores = {1: ColocadorFijo(), 2: ColocadorFijo()}
        self.programar_ronda(1)
        self.motor.ejecutar(max_turnos=1)
        self.assertFalse(self.estado.jugadores[1].activo)
        self.assertTrue(self.estado.jugadores[2].activo)
        # 2.7.2: al quedar un solo jugador activo, es declarado ganador
        self.assertEqual(self.estado.ganador, 2)
        self.assertFalse(self.estado.simulacion_activa)


if __name__ == "__main__":
    unittest.main()
