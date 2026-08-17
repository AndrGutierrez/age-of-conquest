"""Tests unitarios del subsistema economico, demografico y de estabilidad."""

import random
import unittest

from age_of_conquest import economia
from age_of_conquest.config import Config
from age_of_conquest.estado import NEUTRAL

from tests.helpers import MapaParcheadoTestCase


class TestPuertaFiscal(unittest.TestCase):
    def test_h_alta_recauda_completo(self):
        self.assertEqual(economia.puerta_fiscal(0.5), 1.0)

    def test_h_cero_no_recauda(self):
        self.assertEqual(economia.puerta_fiscal(0.0), 0.0)

    def test_h_parcial_es_lineal(self):
        # H_min = 0.25; H = 0.1 -> Omega = 0.4
        self.assertAlmostEqual(economia.puerta_fiscal(0.1), 0.4)


class TestRecaudacion(MapaParcheadoTestCase):
    def test_formula_21(self):
        # R = beta*P*tau*Omega(H)*(1+eta_I*I)
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.poblacion = 1000.0
        prov.impuesto = 0.4
        prov.felicidad = 0.8  # Omega = 1
        prov.infraestructura = 2
        esperado = 0.5 * 1000 * 0.4 * 1.0 * (1 + 0.10 * 2)
        self.assertAlmostEqual(economia.recaudacion_provincia(prov, s.config), esperado)
        self.assertAlmostEqual(economia.recaudacion_total(s, 1), esperado)

    def test_impuesto_cero_no_recauda(self):
        s = self.estado
        s.crear_jugador("P1")
        s.provincias[0].dueno = 1
        s.provincias[0].impuesto = 0.0
        self.assertEqual(economia.recaudacion_total(s, 1), 0.0)

    def test_felicidad_baja_recorta_recaudacion(self):
        # H = 0.1 < H_min -> Omega = 0.4
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.poblacion = 1000.0
        prov.impuesto = 0.4
        prov.felicidad = 0.1
        esperado = 0.5 * 1000 * 0.4 * 0.4
        self.assertAlmostEqual(economia.recaudacion_total(s, 1), esperado)


class TestMantenimiento(MapaParcheadoTestCase):
    def test_militar_e_infra(self):
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.ejercitos = 20
        prov.fortificacion = 2
        prov.infraestructura = 1
        self.assertAlmostEqual(economia.mantenimiento_militar(s, 1), 20 * 0.05)
        self.assertAlmostEqual(
            economia.mantenimiento_infra(s, 1), 2 * 5.0 + 1 * 3.0
        )


class TestLiquidarTesoro(MapaParcheadoTestCase):
    def test_balance_basico(self):
        s = self.estado
        j = s.crear_jugador("P1")
        j.tesoro = 100.0
        prov = s.provincias[0]
        prov.dueno = 1
        prov.poblacion = 500.0
        prov.impuesto = 0.3
        prov.felicidad = 0.8
        prov.ejercitos = 4
        # ingresos = 0.5*500*0.3 = 75; militar = 0.2; infra = 0
        res = economia.liquidar_tesoro(s, 1)
        self.assertAlmostEqual(res.ingresos, 75.0)
        self.assertAlmostEqual(res.gasto_militar, 0.2)
        self.assertAlmostEqual(res.tesoro_final, 100 + 75 - 0.2)
        self.assertFalse(j.bancarrota)

    def test_bancarrota_genera_desercion(self):
        s = self.estado
        j = s.crear_jugador("P1")
        j.tesoro = 0.0
        prov = s.provincias[0]
        prov.dueno = 1
        prov.poblacion = 0.0
        prov.impuesto = 0.0
        prov.ejercitos = 10  # mantenimiento = 0.5 -> deuda de 0.5
        res = economia.liquidar_tesoro(s, 1)
        # la ultima tropa nunca se disuelve: 9 desertan y queda deuda
        self.assertEqual(res.desertados, 9)
        self.assertAlmostEqual(res.tesoro_final, -0.05)
        self.assertEqual(prov.ejercitos, 1)
        self.assertTrue(j.bancarrota)

    def test_reclutamiento_se_cobra(self):
        s = self.estado
        j = s.crear_jugador("P1")
        j.tesoro = 100.0
        prov = s.provincias[0]
        prov.dueno = 1
        prov.poblacion = 0.0
        prov.reclutas_turno = 5  # costo = 5 * 2 = 10
        res = economia.liquidar_tesoro(s, 1)
        self.assertAlmostEqual(res.costo_reclutas, 10.0)
        self.assertAlmostEqual(j.tesoro, 100.0 - 10.0)


class TestPoblacion(MapaParcheadoTestCase):
    def test_crecimiento_logistico(self):
        s = self.estado
        prov = s.provincias[0]
        prov.dueno = 1
        prov.poblacion = 500.0
        prov.felicidad = 0.8
        cap = economia.capacidad_carga(prov)  # llano: 1000
        esperado = 500 + 0.02 * 500 * (1 - 500 / cap)
        economia.crecimiento_poblacional(s)
        self.assertAlmostEqual(prov.poblacion, esperado)

    def test_equilibrio_en_capacidad_de_carga(self):
        # Si P = K*sigma_cap el crecimiento logistico es nulo
        s = self.estado
        prov = s.provincias[0]
        prov.poblacion = economia.capacidad_carga(prov)
        economia.crecimiento_poblacional(s)
        self.assertAlmostEqual(prov.poblacion, economia.capacidad_carga(prov))

    def test_sobrepoblacion_decrece(self):
        s = self.estado
        prov = s.provincias[0]
        prov.poblacion = 1500.0
        prov.felicidad = 0.8
        economia.crecimiento_poblacional(s)
        self.assertLess(prov.poblacion, 1500.0)

    def test_poblacion_no_negativa(self):
        s = self.estado
        prov = s.provincias[0]
        prov.poblacion = 0.0
        prov.bajas_combate = 50
        economia.crecimiento_poblacional(s)
        self.assertEqual(prov.poblacion, 0.0)


class TestFelicidad(MapaParcheadoTestCase):
    def test_clip_en_uno(self):
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.felicidad = 0.99
        prov.impuesto = 0.0
        s.jugadores[1].victorias_turno = True  # +0.10
        economia.actualizar_felicidad(s)
        self.assertEqual(prov.felicidad, 1.0)

    def test_clip_en_cero(self):
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.felicidad = 0.05
        prov.impuesto = 0.5
        # Delta H = -0.2 + delta_eq*(h_eq - H) = -0.2 + 0.45*0.70 = 0.115
        economia.actualizar_felicidad(s)
        self.assertAlmostEqual(prov.felicidad, 0.05 + 0.115)

    def test_impuestos_erosionan_felicidad(self):
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.felicidad = 0.8
        prov.impuesto = 0.5
        economia.actualizar_felicidad(s)
        self.assertAlmostEqual(prov.felicidad, 0.8 - 0.40 * 0.5)


class TestRebelion(unittest.TestCase):
    def test_probabilidad_fuera_de_umbral(self):
        self.assertEqual(economia.probabilidad_rebelion(0.3), 0.0)

    def test_probabilidad_h_cero_es_uno(self):
        self.assertEqual(economia.probabilidad_rebelion(0.0), 1.0)

    def test_probabilidad_formula(self):
        # kappa = 0.01, gamma = 2, H = 0.2 -> 0.01/0.04 = 0.25 (ejemplo 2.8)
        self.assertAlmostEqual(economia.probabilidad_rebelion(0.2), 0.25)


class TestRebelionAplicada(MapaParcheadoTestCase):
    def test_rebelion_hace_neutral(self):
        s = self.estado
        s.crear_jugador("P1")
        prov = s.provincias[0]
        prov.dueno = 1
        prov.felicidad = 0.0  # pi = 1 -> rebelion segura
        prov.ejercitos = 9
        rebeldes = economia.comprobar_rebeliones(s, random.Random(1))
        self.assertIn(0, rebeldes)
        self.assertEqual(prov.dueno, NEUTRAL)
        # la milicia conserva parte de los efectivos (tope milicia_max)
        self.assertEqual(prov.ejercitos, s.config.milicia_max)
        self.assertEqual(prov.impuesto, 0.0)

    def test_felicidad_alta_nunca_se_rebela(self):
        s = self.estado
        s.crear_jugador("P1")
        s.provincias[0].dueno = 1
        s.provincias[0].felicidad = 0.9
        rng = random.Random(1)
        for _ in range(100):
            self.assertEqual(economia.comprobar_rebeliones(s, rng), [])

    def test_rebelion_pierde_el_territorio(self):
        s = self.estado
        s.crear_jugador("P1")
        s.provincias[0].dueno = 1
        s.provincias[0].felicidad = 0.0
        economia.comprobar_rebeliones(s, random.Random(1))
        self.assertEqual(s.territorios_de(1), [])
        # el jugador sin territorios sera eliminado por el motor


if __name__ == "__main__":
    unittest.main()
