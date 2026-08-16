"""Datos estaticos del mapa: el grafo de adyacencia y los continentes.

Se utiliza el mapa clasico de 42 territorios (estilo Risk), que es el que
sugiere el documento ("Sudamerica = 2, Europa = 5" en la Seccion 1.5.2).
El grafo G = (V, E) es no dirigido: (i, k) in E si i y k comparten frontera.

Cada territorio tiene un tipo de terreno sigma(i) en
{0: Llano, 1: Bosque, 2: Montana, 3: Desierto}; la asignacion por territorio
es una decision de diseno (el documento no la especifica) coherente con la
geografia real: Sahara = Desierto, Ural = Montana, Amazonia = Bosque, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    TERRENO_BOSQUE,
    TERRENO_DESIERTO,
    TERRENO_LLANO,
    TERRENO_MONTANA,
)

# Identificadores de continentes (indices 0..5)
AMERICA_NORTE = 0
AMERICA_SUR = 1
EUROPA = 2
AFRICA = 3
ASIA = 4
OCEANIA = 5

CONTINENTE_NOMBRES = {
    AMERICA_NORTE: "America del Norte",
    AMERICA_SUR: "America del Sur",
    EUROPA: "Europa",
    AFRICA: "Africa",
    ASIA: "Asia",
    OCEANIA: "Oceania",
}

# Bonificaciones clasicas por control total del continente (Seccion 1.5.2).
# b_c = soldados/turno adicionales; b_oro_c = oro/turno (Seccion 2.1.4).
CONTINENTE_BONUS_SOLDADOS = {
    AMERICA_NORTE: 5,
    AMERICA_SUR: 2,
    EUROPA: 5,
    AFRICA: 3,
    ASIA: 7,
    OCEANIA: 2,
}
CONTINENTE_BONUS_ORO = {
    AMERICA_NORTE: 15,
    AMERICA_SUR: 6,
    EUROPA: 15,
    AFRICA: 9,
    ASIA: 21,
    OCEANIA: 6,
}


@dataclass(frozen=True)
class Territorio:
    """Informacion estatica de una provincia del mapa."""

    id: int              # i: indice unico 0..N-1
    nombre: str          # nombre para mostrar
    continente: int      # continente al que pertenece
    terreno: int         # sigma(i): 0 Llano, 1 Bosque, 2 Montana, 3 Desierto


# ---------------------------------------------------------------------------
# Definicion del mapa clasico (42 territorios)
# ---------------------------------------------------------------------------

# Definicion completa y explicita (mas legible que una tabla comprimida).
_PROVINCIAS: list[Territorio] = [
    # America del Norte
    Territorio(0, "Alaska", AMERICA_NORTE, TERRENO_BOSQUE),
    Territorio(1, "Territorio del Noroeste", AMERICA_NORTE, TERRENO_BOSQUE),
    Territorio(2, "Groenlandia", AMERICA_NORTE, TERRENO_MONTANA),
    Territorio(3, "Alberta", AMERICA_NORTE, TERRENO_LLANO),
    Territorio(4, "Ontario", AMERICA_NORTE, TERRENO_BOSQUE),
    Territorio(5, "Quebec", AMERICA_NORTE, TERRENO_BOSQUE),
    Territorio(6, "Oeste de EE.UU.", AMERICA_NORTE, TERRENO_DESIERTO),
    Territorio(7, "Este de EE.UU.", AMERICA_NORTE, TERRENO_LLANO),
    Territorio(8, "America Central", AMERICA_NORTE, TERRENO_BOSQUE),
    # America del Sur (4 territorios, bonus 2)
    Territorio(9, "Venezuela", AMERICA_SUR, TERRENO_BOSQUE),
    Territorio(10, "Peru", AMERICA_SUR, TERRENO_MONTANA),
    Territorio(11, "Brasil", AMERICA_SUR, TERRENO_BOSQUE),
    Territorio(12, "Argentina", AMERICA_SUR, TERRENO_LLANO),
    # Europa (7 territorios, bonus 5)
    Territorio(13, "Islandia", EUROPA, TERRENO_MONTANA),
    Territorio(14, "Gran Bretana", EUROPA, TERRENO_LLANO),
    Territorio(15, "Escandinavia", EUROPA, TERRENO_BOSQUE),
    Territorio(16, "Ucrania", EUROPA, TERRENO_LLANO),
    Territorio(17, "Europa Occidental", EUROPA, TERRENO_LLANO),
    Territorio(18, "Europa Septentrional", EUROPA, TERRENO_LLANO),
    Territorio(19, "Europa Meridional", EUROPA, TERRENO_LLANO),
    # Africa (6 territorios, bonus 3)
    Territorio(20, "Norte de Africa", AFRICA, TERRENO_DESIERTO),
    Territorio(21, "Egipto", AFRICA, TERRENO_DESIERTO),
    Territorio(22, "Africa Oriental", AFRICA, TERRENO_DESIERTO),
    Territorio(23, "Congo", AFRICA, TERRENO_BOSQUE),
    Territorio(24, "Sudafrica", AFRICA, TERRENO_LLANO),
    Territorio(25, "Madagascar", AFRICA, TERRENO_BOSQUE),
    # Asia (12 territorios, bonus 7)
    Territorio(26, "Ural", ASIA, TERRENO_MONTANA),
    Territorio(27, "Siberia", ASIA, TERRENO_BOSQUE),
    Territorio(28, "Yakutsk", ASIA, TERRENO_LLANO),
    Territorio(29, "Kamchatka", ASIA, TERRENO_MONTANA),
    Territorio(30, "Irkutsk", ASIA, TERRENO_BOSQUE),
    Territorio(31, "Mongolia", ASIA, TERRENO_DESIERTO),
    Territorio(32, "Japon", ASIA, TERRENO_MONTANA),
    Territorio(33, "Afganistan", ASIA, TERRENO_MONTANA),
    Territorio(34, "China", ASIA, TERRENO_LLANO),
    Territorio(35, "Oriente Medio", ASIA, TERRENO_DESIERTO),
    Territorio(36, "India", ASIA, TERRENO_BOSQUE),
    Territorio(37, "Siam", ASIA, TERRENO_BOSQUE),
    # Oceania (4 territorios, bonus 2)
    Territorio(38, "Indonesia", OCEANIA, TERRENO_BOSQUE),
    Territorio(39, "Nueva Guinea", OCEANIA, TERRENO_BOSQUE),
    Territorio(40, "Australia Occidental", OCEANIA, TERRENO_DESIERTO),
    Territorio(41, "Australia Oriental", OCEANIA, TERRENO_LLANO),
]

#: Grafo de adyacencia no dirigido: id -> lista de ids vecinos.
ADYACENCIAS: dict[int, list[int]] = {
    0: [1, 3, 29],                       # Alaska
    1: [0, 3, 4, 2],                     # T. del Noroeste
    2: [1, 4, 5, 13],                    # Groenlandia
    3: [0, 1, 4, 6],                     # Alberta
    4: [1, 2, 3, 5, 6, 7],               # Ontario
    5: [2, 4, 7],                        # Quebec
    6: [3, 4, 7, 8],                     # Oeste de EE.UU.
    7: [4, 5, 6, 8],                     # Este de EE.UU.
    8: [6, 7, 9],                        # America Central
    9: [8, 10, 11],                      # Venezuela
    10: [9, 11, 12],                     # Peru
    11: [9, 10, 12, 20],                 # Brasil
    12: [10, 11],                        # Argentina
    13: [2, 14, 15],                     # Islandia
    14: [13, 15, 17, 18],                # Gran Bretana
    15: [13, 14, 16, 18],                # Escandinavia
    16: [15, 18, 19, 26, 33, 35],        # Ucrania
    17: [14, 18, 19, 20],                # Europa Occidental
    18: [14, 15, 16, 17, 19],            # Europa Septentrional
    19: [16, 17, 18, 20, 21, 35],        # Europa Meridional
    20: [11, 17, 19, 21, 22, 23],        # Norte de Africa
    21: [19, 20, 22, 35],                # Egipto
    22: [20, 21, 23, 24, 25, 35],        # Africa Oriental
    23: [20, 22, 24],                    # Congo
    24: [22, 23, 25],                    # Sudafrica
    25: [22, 24],                        # Madagascar
    26: [16, 27, 33, 34, 35],            # Ural
    27: [26, 28, 30, 31, 34],            # Siberia
    28: [27, 29, 30],                    # Yakutsk
    29: [0, 28, 30, 31, 32],             # Kamchatka
    30: [27, 28, 29, 31],                # Irkutsk
    31: [27, 29, 30, 32, 34],            # Mongolia
    32: [29, 31],                        # Japon
    33: [16, 26, 34, 35, 36],            # Afganistan
    34: [26, 27, 31, 33, 36, 37],        # China
    35: [16, 19, 21, 22, 26, 33, 36],    # Oriente Medio
    36: [33, 34, 35, 37],                # India
    37: [34, 36, 38],                    # Siam
    38: [37, 39, 40],                    # Indonesia
    39: [38, 40, 41],                    # Nueva Guinea
    40: [38, 39, 41],                    # Australia Occidental
    41: [39, 40],                        # Australia Oriental
}


class Mapa:
    """Contenedor inmutable de la geografia del escenario."""

    def __init__(self) -> None:
        self.territorios: list[Territorio] = list(_PROVINCIAS)
        self.n = len(self.territorios)
        self.por_nombre = {t.nombre: t for t in self.territorios}
        self.adyacencias: dict[int, list[int]] = {
            k: list(v) for k, v in ADYACENCIAS.items()
        }
        #: territorios de cada continente: continente -> lista de ids
        self.territorios_continente: dict[int, list[int]] = {}
        for t in self.territorios:
            self.territorios_continente.setdefault(t.continente, []).append(t.id)

    def son_adyacentes(self, i: int, k: int) -> bool:
        """Devuelve True si (i, k) es una arista del grafo de adyacencia."""
        return k in self.adyacencias.get(i, [])

    def vecinos(self, i: int) -> list[int]:
        """Lista de territorios que comparten frontera con i."""
        return list(self.adyacencias.get(i, []))

    def territorio(self, i: int) -> Territorio:
        return self.territorios[i]

    def verificar_integridad(self) -> list[str]:
        """Comprueba coherencia del grafo: simetria y conectividad.

        Devuelve una lista de errores (vacia si el mapa es valido).
        """
        errores: list[str] = []
        for i, vecs in self.adyacencias.items():
            if len(set(vecs)) != len(vecs):
                errores.append(f"Territorio {i}: adyacencias duplicadas")
            for k in vecs:
                if i not in self.adyacencias.get(k, []):
                    errores.append(f"Arista asimetrica ({i},{k})")
        if len(self.adyacencias) != self.n:
            errores.append("Hay territorios sin entrada de adyacencia")

        # Conectividad por busqueda en anchura (BFS)
        visitados = {0}
        cola = [0]
        while cola:
            actual = cola.pop(0)
            for vec in self.adyacencias.get(actual, []):
                if vec not in visitados:
                    visitados.add(vec)
                    cola.append(vec)
        if len(visitados) != self.n:
            errores.append("El grafo no es conexo")
        return errores


#: Instancia unica del mapa (compartida por toda la simulacion).
MAPA = Mapa()
