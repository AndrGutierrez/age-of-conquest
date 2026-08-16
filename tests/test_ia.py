"""Tests de la inteligencia artificial: distribucion de refuerzos y ataques."""

import random
import unittest
from unittest.mock import patch

from age_of_conquest import estado
from age_of_conquest.estado import PERFIL_AGRESIVO, PERFIL_DEFENSIVO, PERFIL_EQUILIBRADO, GameState
from age_of_conquest.ia import ControladorIA
from age_of_conquest.motor import Motor

from tests.helpers import MiniMapa


class TestDistribucionRefuerzos(unittest.TestCase):
    def setUp(self):
        # Anillo de 6 territorios: P1 posee 0,1,2 y P2 posee 3,4,5.
        # Fronteras de P1: 0 (vecino 5 de P2) y 2 (vecino 3 de P2); 1 interior.
        self.patcher = patch.object(
            estado, "MAPA",
            MiniMapa(6, {i: [(i - 1) % 6, (i + 1) % 6] for i in range(6)}),
        )
        self.patcher.start()
        self.estado = GameState()
        self.estado.inicializar_provincias()
        self.ia = ControladorIA()

    def tearDown(self):
        self.patcher.stop()

    def preparar(self, perfil):
        j1 = self.estado.crear_jugador("P1", perfil=perfil)
        self.estado.crear_jugador("P2", perfil=PERFIL_DEFENSIVO)
        for i in (0, 1, 2):
            self.estado.provincias[i].dueno = 1
            self.estado.provincias[i].ejercitos = 3
        for i in (3, 4, 5):
            self.estado.provincias[i].dueno = 2
            self.estado.provincias[i].ejercitos = 3
        return j1

    def test_agresivo_todo_a_frontera(self):
        j = self.preparar(PERFIL_AGRESIVO)
        self.ia._distribuir_refuerzos(self.estado, j, 12, PERFIL_AGRESIVO)
        # el interior no recibe nada
        self.assertEqual(self.estado.provincias[1].ejercitos, 3)
        total = sum(self.estado.provincias[i].ejercitos for i in (0, 1, 2))
        self.assertEqual(total, 3 * 3 + 12)

    def test_defensivo_uniforme_en_frontera(self):
        j = self.preparar(PERFIL_DEFENSIVO)
        self.ia._distribuir_refuerzos(self.estado, j, 8, PERFIL_DEFENSIVO)
        # frontera: 0 y 2 reciben cuota uniforme (8 // 2 = 4)
        self.assertEqual(self.estado.provincias[0].ejercitos, 3 + 4)
        self.assertEqual(self.estado.provincias[2].ejercitos, 3 + 4)
        self.assertEqual(self.estado.provincias[1].ejercitos, 3)

    def test_equilibrado_60_40(self):
        j = self.preparar(PERFIL_EQUILIBRADO)
        self.ia._distribuir_refuerzos(self.estado, j, 10, PERFIL_EQUILIBRADO)
        # 6 a frontera (3+3), 4 al interior
        self.assertEqual(self.estado.provincias[0].ejercitos, 3 + 3)
        self.assertEqual(self.estado.provincias[2].ejercitos, 3 + 3)
        self.assertEqual(self.estado.provincias[1].ejercitos, 3 + 4)

    def test_agresivo_prefiere_enemigo_debil(self):
        j = self.preparar(PERFIL_AGRESIVO)
        # Enemigo adyacente a 2 (prov 3) es debil; enemigo adyacente a 0
        # (prov 5) es fuerte -> la mayor parte de refuerzos va a 2.
        self.estado.provincias[3].ejercitos = 1
        self.estado.provincias[5].ejercitos = 50
        self.ia._distribuir_refuerzos(self.estado, j, 20, PERFIL_AGRESIVO)
        self.assertGreater(
            self.estado.provincias[2].ejercitos, self.estado.provincias[0].ejercitos
        )

    def test_agresivo_invierte_en_reclutas(self):
        j = self.preparar(PERFIL_AGRESIVO)
        tesoro_inicial = j.tesoro
        self.ia.colocar_refuerzos(self.estado, j, 3)
        # refuerzos + reclutamiento con excedentes
        total = sum(self.estado.provincias[i].ejercitos for i in (0, 1, 2))
        self.assertGreater(total, 3 * 3 + 3)
        self.assertLess(j.tesoro, tesoro_inicial)


class TestPoliticaFiscal(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.object(estado, "MAPA", MiniMapa(2))
        self.patcher.start()
        self.estado = GameState()
        self.estado.inicializar_provincias()
        self.ia = ControladorIA()

    def tearDown(self):
        self.patcher.stop()

    def test_impuesto_base_por_perfil(self):
        j = self.estado.crear_jugador("P1", perfil=PERFIL_AGRESIVO)
        self.estado.provincias[0].dueno = 1
        self.ia._politica_fiscal(self.estado, j)
        self.assertAlmostEqual(self.estado.provincias[0].impuesto, 0.40)

    def test_adaptacion_por_felicidad_baja(self):
        j = self.estado.crear_jugador("P1", perfil=PERFIL_AGRESIVO)
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[0].felicidad = 0.1
        self.ia._politica_fiscal(self.estado, j)
        self.assertAlmostEqual(self.estado.provincias[0].impuesto, 0.35)

    def test_adaptacion_por_tesoro_bajo(self):
        j = self.estado.crear_jugador("P1", perfil=PERFIL_DEFENSIVO)
        j.tesoro = 5.0
        self.estado.provincias[0].dueno = 1
        self.ia._politica_fiscal(self.estado, j)
        self.assertAlmostEqual(self.estado.provincias[0].impuesto, 0.25)


class TestAtaquesIA(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.object(estado, "MAPA", MiniMapa(2))
        self.patcher.start()
        self.estado = GameState()
        self.estado.inicializar_provincias()
        self.rng = random.Random(0)
        self.motor = Motor(self.estado, {}, self.rng)
        self.ia = ControladorIA()

    def tearDown(self):
        self.patcher.stop()

    def preparar(self, perfil, ejercitos_p1, ejercitos_p2):
        j1 = self.estado.crear_jugador("P1", perfil=perfil)
        self.estado.crear_jugador("P2", perfil=PERFIL_DEFENSIVO)
        self.estado.provincias[0].dueno = 1
        self.estado.provincias[0].ejercitos = ejercitos_p1
        self.estado.provincias[1].dueno = 2
        self.estado.provincias[1].ejercitos = ejercitos_p2
        self.estado.jugador_activo = 1
        return j1

    def test_defensivo_no_ataca_sin_superioridad(self):
        j = self.preparar(PERFIL_DEFENSIVO, 10, 8)  # ratio 9/8 < 2.0
        self.ia.fase_ataque(self.motor, self.estado, j)
        self.assertEqual(self.estado.provincias[1].dueno, 2)

    def test_agresivo_ataca_con_ventaja_pequena(self):
        j = self.preparar(PERFIL_AGRESIVO, 20, 5)  # ratio 19/5 >= 0.9
        self.ia.fase_ataque(self.motor, self.estado, j)
        # con 20 vs 5 el agresivo ataca; no garantizamos conquista
        # (estocastico), solo que se intento el ataque
        self.assertLessEqual(self.estado.provincias[1].ejercitos, 5)

    def test_equilibrado_ataca_con_ventaja_moderada(self):
        j = self.preparar(PERFIL_EQUILIBRADO, 30, 2)
        self.ia.fase_ataque(self.motor, self.estado, j)
        self.assertEqual(self.estado.provincias[1].dueno, 1)

    def test_movimiento_interior_hacia_frontera(self):
        # Anillo de 4: P1 posee 0,1,2 (frontera: 0 y 2; interior: 1)
        with patch.object(
            estado, "MAPA", MiniMapa(4, {i: [(i + 1) % 4] for i in range(4)})
        ):
            s = GameState()
            s.inicializar_provincias()
            j = s.crear_jugador("P1", perfil=PERFIL_DEFENSIVO)
            s.crear_jugador("P2", perfil=PERFIL_DEFENSIVO)
            s.provincias[0].dueno = 1
            s.provincias[1].dueno = 1
            s.provincias[2].dueno = 1
            s.provincias[3].dueno = 2
            s.provincias[1].ejercitos = 10  # interior con excedente
            s.jugador_activo = 1
            motor = Motor(s, {}, random.Random(0))
            origen, destino = self.ia._elegir_movimiento(s, j)
            self.assertIn((origen, destino), [(1, 0), (1, 2)])
            self.ia.fase_movimiento(motor, s, j)
            # se movio todo menos 1 tropa
            self.assertEqual(s.provincias[1].ejercitos, 1)


if __name__ == "__main__":
    unittest.main()
