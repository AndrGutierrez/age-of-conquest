"""Tests unitarios del modulo de combate (Seccion 2.4).

Nota de validacion: la tabla de la Seccion 2.4.6 del documento contiene
errores en las filas (2,2) y (2,1); los valores correctos, obtenidos por
enumeracion exhaustiva de todos los resultados equiprobables, son:
    (2,2): E[b_a] = 1.2207, E[b_d] = 0.7793
    (2,1): E[b_a] = 0.4213, E[b_d] = 0.5787
El simulador implementa el modelo definido por las ecuaciones (2.4.2) y
(2.4.3), por lo que produce los valores teoricos correctos. Este hallazgo
se documenta en la seccion de Validacion del informe tecnico.
"""

import random
import unittest
from unittest.mock import patch

from age_of_conquest import estado
from age_of_conquest.combate import (
    ataque_viable,
    batalla,
    esperanza_bajas_teorica,
    numero_dados,
    probabilidad_dado_atacante,
    resolver_ronda,
)
from age_of_conquest.estado import Provincia
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


class MapaStub:
    """Mapa falso con un unico tipo de terreno, para aislar las pruebas."""

    def __init__(self, terreno):
        self.terreno_fijo = terreno

    def territorio(self, i):
        return Territorio(id=i, nombre="X", continente=0, terreno=self.terreno_fijo)


def resolver(atk, defe, terreno=0, fort=0, dados=()):
    """Ejecuta resolver_ronda con mapa stub y dados controlados."""
    with patch.object(estado, "MAPA", MapaStub(terreno)):
        p = Provincia(id=1)
        p.fortificacion = fort
        return resolver_ronda(atk, defe, p, RngStub(dados))


def luchar(atk, defe, terreno=0, fort=0, dados=(), max_rondas=None, seed=None):
    """Ejecuta batalla con mapa stub y dados controlados."""
    with patch.object(estado, "MAPA", MapaStub(terreno)):
        p = Provincia(id=1)
        p.fortificacion = fort
        rng = RngStub(dados) if dados else random.Random(seed or 0)
        return batalla(atk, defe, p, rng, max_rondas=max_rondas)


class TestNumeroDados(unittest.TestCase):
    def test_tipico_3_vs_2(self):
        self.assertEqual(numero_dados(5, 5), (3, 2))

    def test_atacante_pequeno(self):
        # 2 tropas -> 1 dado; 3 tropas -> 2 dados
        self.assertEqual(numero_dados(2, 5), (1, 2))
        self.assertEqual(numero_dados(3, 5), (2, 2))

    def test_defensor_unico(self):
        self.assertEqual(numero_dados(10, 1), (3, 1))

    def test_defensor_sin_tropas(self):
        # Caso borde: A_k = 0 -> n_def = 0, conquista automatica
        self.assertEqual(numero_dados(5, 0), (3, 0))

    def test_atacante_con_una_tropa_no_puede(self):
        self.assertFalse(ataque_viable(1))
        self.assertEqual(numero_dados(1, 5), (0, 2))


class TestResolucionRonda(unittest.TestCase):
    def test_empate_favorece_al_defensor(self):
        r = resolver(2, 1, dados=[3, 3])
        self.assertEqual(r.bajas_atacante, 1)
        self.assertEqual(r.bajas_defensor, 0)

    def test_atacante_superior_gana(self):
        r = resolver(2, 1, dados=[4, 2])
        self.assertEqual(r.bajas_atacante, 0)
        self.assertEqual(r.bajas_defensor, 1)

    def test_multiplicador_de_terreno(self):
        # atk [3] vs def [2]: en llano gana el atacante; en montana
        # (theta=1.5) el dado defensor escala a 3 y el empate favorece
        # al defensor.
        r_llano = resolver(2, 1, terreno=0, dados=[3, 2])
        self.assertEqual(r_llano.bajas_defensor, 1)
        r_montana = resolver(2, 1, terreno=2, dados=[3, 2])
        self.assertEqual(r_montana.bajas_atacante, 1)
        self.assertEqual(r_montana.bajas_defensor, 0)

    def test_fortificacion_escala_dado_defensor(self):
        # fort = 1 -> mult = 1.15; def 2 -> round(2.3) = 2 (sin cambio)
        # fort = 2 -> mult = 1.30; def 2 -> round(2.6) = 3 -> empate
        r1 = resolver(2, 1, fort=1, dados=[3, 2])
        self.assertEqual(r1.bajas_defensor, 1)
        r2 = resolver(2, 1, fort=2, dados=[3, 2])
        self.assertEqual(r2.bajas_atacante, 1)

    def test_dado_escalado_no_supera_las_caras(self):
        # En montana 6*1.5 = 9 -> se limita a 6 (maximo del dado)
        r = resolver(2, 1, terreno=2, dados=[6, 6])
        self.assertEqual(r.dados_defensor[0], 6)


class TestBatalla(unittest.TestCase):
    def test_conquista_y_transferencia(self):
        # Atacante 10 vs defensor 1: dados [6,6,6] vs [1] -> conquista en
        # la primera ronda; m_oc = max(n_atk=3, 1) = 3 tropas transferidas.
        b = luchar(10, 1, dados=[6, 6, 6, 1])
        self.assertTrue(b.conquistada)
        self.assertEqual(b.bajas_defensor, 1)
        self.assertEqual(b.transferidas, 3)
        self.assertEqual(b.ejercitos_origen, 7)
        self.assertEqual(b.ejercitos_destino, 3)

    def test_atacante_agotado_no_conquista(self):
        # Atacante 2 vs defensor 1: atk [1] vs def [6] -> baja atacante,
        # queda con 1 tropa y no puede seguir.
        b = luchar(2, 1, dados=[1, 6])
        self.assertFalse(b.conquistada)
        self.assertEqual(b.ejercitos_origen, 1)
        self.assertEqual(b.ejercitos_destino, 1)
        self.assertEqual(b.rondas, 1)

    def test_conquista_deja_al_menos_una_tropa_en_origen(self):
        # Atacante 2 vs defensor 0: conquista automatica; m_oc = max(1,1)=1
        # pero el origen debe retener >= 1.
        b = luchar(2, 0, dados=[])
        self.assertTrue(b.conquistada)
        self.assertEqual(b.ejercitos_origen, 1)
        self.assertEqual(b.ejercitos_destino, 1)

    def test_max_rondas_limita_la_batalla(self):
        b = luchar(8, 5, seed=42, max_rondas=1)
        self.assertLessEqual(b.rondas, 1)


class TestProbabilidades(unittest.TestCase):
    def test_probabilidad_un_dado(self):
        # P(atacante gana) = 5/12 con D = 6 (Seccion 2.4.6)
        self.assertAlmostEqual(probabilidad_dado_atacante(), 5 / 12, places=10)

    def test_tabla_esperanzas_teoricas(self):
        # Valores obtenidos por enumeracion exhaustiva (ver nota del modulo).
        # Las filas (3,2), (3,1), (1,2) y (1,1) coinciden con la tabla de la
        # Seccion 2.4.6 del documento.
        tabla = {
            (3, 2): (0.921, 1.079),
            (3, 1): (0.340, 0.660),
            (2, 2): (1.221, 0.779),
            (2, 1): (0.421, 0.579),
            (1, 2): (0.745, 0.255),
            (1, 1): (0.583, 0.417),
        }
        for (na, nd), (ea, ed) in tabla.items():
            ca, cd = esperanza_bajas_teorica(na, nd)
            self.assertAlmostEqual(ca, ea, delta=0.01, msg=f"({na},{nd}) atk")
            self.assertAlmostEqual(cd, ed, delta=0.01, msg=f"({na},{nd}) def")

    def test_montecarlo_1v1(self):
        # La frecuencia empirica del dado 1 vs 1 debe acercarse a 5/12.
        rng = random.Random(7)
        victorias = 0
        n = 20000
        with patch.object(estado, "MAPA", MapaStub(0)):
            p = Provincia(id=1)
            for _ in range(n):
                r = resolver_ronda(2, 1, p, rng)
                if r.bajas_defensor == 1:
                    victorias += 1
        self.assertAlmostEqual(victorias / n, 5 / 12, delta=0.02)


if __name__ == "__main__":
    unittest.main()
