"""Tests de los escenarios historicos: imperios fijos y mapa de Europa."""

import unittest

from age_of_conquest.config import Config
from age_of_conquest.escenarios import (
    BONUS_CAPITAL,
    ESCENARIOS,
    aplicar_escenario,
    validar_escenario,
)
from age_of_conquest.estado import NEUTRAL, GameState
from age_of_conquest.mapa import MAPA


class TestMapaEuropa(unittest.TestCase):
    def test_integridad_del_grafo(self):
        self.assertEqual(MAPA.verificar_integridad(), [])
        self.assertEqual(MAPA.n, 42)

    def test_region_principal_del_juego(self):
        # La region de Italia existe y tiene bonus propio
        self.assertIn(3, MAPA.territorios_continente)
        self.assertEqual(len(MAPA.territorios_continente[3]), 4)
        self.assertTrue(any(t.nombre == "Roma" for t in MAPA.territorios))


class TestEscenarios(unittest.TestCase):
    def test_escenarios_definidos(self):
        self.assertSetEqual(set(ESCENARIOS), {"roma", "caida", "medieval"})

    def test_validacion_de_escenarios(self):
        for nombre, esc in ESCENARIOS.items():
            errores = validar_escenario(esc, MAPA)
            self.assertEqual(errores, [], msg=f"{nombre}: {errores}")

    def test_ascenso_de_roma_imperios(self):
        esc = ESCENARIOS["roma"]
        nombres = [i.nombre for i in esc.imperios]
        self.assertEqual(
            nombres,
            ["Republica Romana", "Cartago", "Egipto Ptolemaico", "Macedonia"],
        )
        # Roma es el imperio humano y controla Italia
        roma = esc.imperios[0]
        self.assertTrue(roma.humano)
        self.assertEqual(roma.territorios, [11, 12, 13, 14])
        self.assertEqual(roma.capital, 12)

    def test_edades_medias_incluye_al_andalus(self):
        nombres = [i.nombre for i in ESCENARIOS["medieval"].imperios]
        self.assertIn("Al-Andalus", nombres)
        self.assertIn("Sacro Imperio Romano Germanico", nombres)


class TestAplicarEscenario(unittest.TestCase):
    def preparar(self, nombre="roma", todos_ia=False):
        estado = GameState()
        estado.inicializar_provincias()
        aplicar_escenario(estado, ESCENARIOS[nombre], todos_ia=todos_ia)
        return estado

    def test_asignacion_fija_sin_aleatoriedad(self):
        s1 = self.preparar()
        s2 = self.preparar()
        duenos1 = {i: p.dueno for i, p in s1.provincias.items()}
        duenos2 = {i: p.dueno for i, p in s2.provincias.items()}
        self.assertEqual(duenos1, duenos2)

    def test_todos_los_territorios_asignados(self):
        s = self.preparar()
        duenos = {p.dueno for p in s.provincias.values()}
        # 4 imperios + neutrales
        self.assertEqual(len(s.jugadores), 4)
        self.assertIn(NEUTRAL, duenos)
        for p in s.provincias.values():
            if p.dueno == NEUTRAL:
                self.assertEqual(p.ejercitos, s.config.guarnicion_neutral)
            else:
                self.assertGreaterEqual(p.ejercitos, s.config.ejercitos_iniciales)

    def test_capital_con_bonus(self):
        s = self.preparar()
        roma = ESCENARIOS["roma"].imperios[0]
        capital = s.provincias[roma.capital]
        self.assertEqual(
            capital.ejercitos, s.config.ejercitos_iniciales + BONUS_CAPITAL
        )

    def test_territorios_iniciales_de_cada_imperio(self):
        s = self.preparar("caida")
        bizantino = next(
            j for j in s.jugadores.values() if j.nombre == "Imperio Bizantino"
        )
        esperados = {28, 29, 30, 33, 34, 37}
        self.assertEqual(set(s.territorios_de(bizantino.id)), esperados)

    def test_modo_todos_ia(self):
        s = self.preparar(todos_ia=True)
        self.assertFalse(any(j.humano for j in s.jugadores.values()))

    def test_modo_interactivo_un_humano(self):
        s = self.preparar(todos_ia=False)
        humanos = [j for j in s.jugadores.values() if j.humano]
        self.assertEqual(len(humanos), 1)
        self.assertEqual(humanos[0].nombre, "Republica Romana")


if __name__ == "__main__":
    unittest.main()
