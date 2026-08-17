"""Datos estaticos del mapa: Europa dividida en 42 provincias historicas.

El mapa corresponde al escenario principal del juego (Europa) y esta
particionado en 11 regiones ("continentes") que otorgan bonificaciones por
control total, analogas a los continentes del modelo formal:

    Britania, Galia, Iberia, Italia, Germania, Norte de Africa, Balcanes,
    Grecia, Anatolia, Oriente y Europa del Este.

El grafo G = (V, E) es no dirigido: (i, k) in E si i y k comparten
frontera (terrestre o maritima navegable, como en el juego de referencia).
Cada provincia tiene un tipo de terreno sigma(i) en
{0: Llano, 1: Bosque, 2: Montana, 3: Desierto} asignado segun su geografia.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import (
    TERRENO_BOSQUE,
    TERRENO_DESIERTO,
    TERRENO_LLANO,
    TERRENO_MONTANA,
)

# Identificadores de regiones (indices 0..10)
BRITANIA = 0
GALIA = 1
IBERIA = 2
ITALIA = 3
GERMANIA = 4
NORTE_AFRICA = 5
BALCANES = 6
GRECIA = 7
ANATOLIA = 8
ORIENTE = 9
EUROPA_ESTE = 10

REGION_NOMBRES = {
    BRITANIA: "Britania",
    GALIA: "Galia",
    IBERIA: "Iberia",
    ITALIA: "Italia",
    GERMANIA: "Germania",
    NORTE_AFRICA: "Norte de Africa",
    BALCANES: "Balcanes",
    GRECIA: "Grecia",
    ANATOLIA: "Anatolia",
    ORIENTE: "Oriente",
    EUROPA_ESTE: "Europa del Este",
}

# Bonificaciones por control total de la region.
# b_c = soldados/turno (Seccion 1.5.2); b_oro_c = oro/turno (Seccion 2.1.4).
REGION_BONUS_SOLDADOS = {
    BRITANIA: 2,
    GALIA: 3,
    IBERIA: 3,
    ITALIA: 4,
    GERMANIA: 3,
    NORTE_AFRICA: 3,
    BALCANES: 3,
    GRECIA: 2,
    ANATOLIA: 3,
    ORIENTE: 4,
    EUROPA_ESTE: 2,
}
REGION_BONUS_ORO = {c: 3 * v for c, v in REGION_BONUS_SOLDADOS.items()}

# Aliases con los nombres usados por el resto del codigo
CONTINENTE_NOMBRES = REGION_NOMBRES
CONTINENTE_BONUS_SOLDADOS = REGION_BONUS_SOLDADOS
CONTINENTE_BONUS_ORO = REGION_BONUS_ORO


@dataclass(frozen=True)
class Territorio:
    """Informacion estatica de una provincia del mapa."""

    id: int              # i: indice unico 0..N-1
    nombre: str          # nombre para mostrar
    continente: int      # region a la que pertenece
    terreno: int         # sigma(i): 0 Llano, 1 Bosque, 2 Montana, 3 Desierto


# ---------------------------------------------------------------------------
# Definicion del mapa de Europa (42 provincias, 11 regiones)
# ---------------------------------------------------------------------------

_PROVINCIAS: list[Territorio] = [
    # Britania (3 provincias, bonus 2)
    Territorio(0, "Britania", BRITANIA, TERRENO_LLANO),
    Territorio(1, "Caledonia", BRITANIA, TERRENO_MONTANA),
    Territorio(2, "Hibernia", BRITANIA, TERRENO_BOSQUE),
    # Galia (4 provincias, bonus 3)
    Territorio(3, "Armorica", GALIA, TERRENO_LLANO),
    Territorio(4, "Galia Celtica", GALIA, TERRENO_LLANO),
    Territorio(5, "Galia Belgica", GALIA, TERRENO_BOSQUE),
    Territorio(6, "Narbonense", GALIA, TERRENO_LLANO),
    # Iberia (4 provincias, bonus 3)
    Territorio(7, "Tarraconense", IBERIA, TERRENO_MONTANA),
    Territorio(8, "Lusitania", IBERIA, TERRENO_LLANO),
    Territorio(9, "Betica", IBERIA, TERRENO_LLANO),
    Territorio(10, "Cartaginense", IBERIA, TERRENO_LLANO),
    # Italia (4 provincias, bonus 4)
    Territorio(11, "Galia Cisalpina", ITALIA, TERRENO_LLANO),
    Territorio(12, "Roma", ITALIA, TERRENO_LLANO),
    Territorio(13, "Magna Grecia", ITALIA, TERRENO_LLANO),
    Territorio(14, "Sicilia", ITALIA, TERRENO_MONTANA),
    # Germania (4 provincias, bonus 3)
    Territorio(15, "Germania Inferior", GERMANIA, TERRENO_BOSQUE),
    Territorio(16, "Germania Superior", GERMANIA, TERRENO_BOSQUE),
    Territorio(17, "Retia", GERMANIA, TERRENO_MONTANA),
    Territorio(18, "Noricum", GERMANIA, TERRENO_BOSQUE),
    # Norte de Africa (4 provincias, bonus 3)
    Territorio(19, "Mauritania", NORTE_AFRICA, TERRENO_DESIERTO),
    Territorio(20, "Numidia", NORTE_AFRICA, TERRENO_DESIERTO),
    Territorio(21, "Cartago", NORTE_AFRICA, TERRENO_LLANO),
    Territorio(22, "Cirenaica", NORTE_AFRICA, TERRENO_DESIERTO),
    # Balcanes (4 provincias, bonus 3)
    Territorio(23, "Iliria", BALCANES, TERRENO_BOSQUE),
    Territorio(24, "Dacia", BALCANES, TERRENO_BOSQUE),
    Territorio(25, "Tracia", BALCANES, TERRENO_LLANO),
    Territorio(26, "Macedonia", BALCANES, TERRENO_MONTANA),
    # Grecia (3 provincias, bonus 2)
    Territorio(27, "Epiro", GRECIA, TERRENO_MONTANA),
    Territorio(28, "Grecia", GRECIA, TERRENO_LLANO),
    Territorio(29, "Creta", GRECIA, TERRENO_LLANO),
    # Anatolia (4 provincias, bonus 3)
    Territorio(30, "Bitinia", ANATOLIA, TERRENO_LLANO),
    Territorio(31, "Galacia", ANATOLIA, TERRENO_BOSQUE),
    Territorio(32, "Capadocia", ANATOLIA, TERRENO_MONTANA),
    Territorio(33, "Cilicia", ANATOLIA, TERRENO_LLANO),
    # Oriente (5 provincias, bonus 4)
    Territorio(34, "Siria", ORIENTE, TERRENO_LLANO),
    Territorio(35, "Fenicia", ORIENTE, TERRENO_LLANO),
    Territorio(36, "Mesopotamia", ORIENTE, TERRENO_DESIERTO),
    Territorio(37, "Egipto", ORIENTE, TERRENO_DESIERTO),
    Territorio(38, "Arabia", ORIENTE, TERRENO_DESIERTO),
    # Europa del Este (3 provincias, bonus 2)
    Territorio(39, "Sarmacia", EUROPA_ESTE, TERRENO_LLANO),
    Territorio(40, "Escitia", EUROPA_ESTE, TERRENO_DESIERTO),
    Territorio(41, "Germania Oriental", EUROPA_ESTE, TERRENO_BOSQUE),
]

#: Grafo de adyacencia no dirigido: id -> lista de ids vecinos.
ADYACENCIAS: dict[int, list[int]] = {
    0: [1, 2, 3, 5],                       # Britania
    1: [0],                                # Caledonia
    2: [0],                                # Hibernia
    3: [0, 4],                             # Armorica
    4: [3, 5, 6, 11, 16],                  # Galia Celtica
    5: [0, 4, 15],                         # Galia Belgica
    6: [4, 7, 10, 12, 16],                 # Narbonense
    7: [6, 8, 10],                         # Tarraconense
    8: [7, 9, 10],                         # Lusitania
    9: [8, 10, 19, 21],                    # Betica
    10: [6, 7, 8, 9, 21],                  # Cartaginense
    11: [4, 12, 16, 17, 18],                # Galia Cisalpina
    12: [6, 11, 13, 14],                   # Roma
    13: [12, 14, 23, 26],                  # Magna Grecia
    14: [12, 13, 21],                      # Sicilia
    15: [5, 16, 41],                       # Germania Inferior
    16: [4, 6, 11, 15, 17, 41],            # Germania Superior
    17: [16, 11, 18],                      # Retia
    18: [11, 17, 23, 24],                  # Noricum
    19: [9, 20],                           # Mauritania
    20: [19, 21],                          # Numidia
    21: [9, 10, 14, 20, 22],               # Cartago
    22: [21, 29, 37],                      # Cirenaica
    23: [13, 18, 24, 26, 27],              # Iliria
    24: [18, 23, 25, 39],                  # Dacia
    25: [24, 26, 27, 30],                  # Tracia
    26: [13, 23, 25, 27, 28],              # Macedonia
    27: [23, 25, 26, 28],                  # Epiro
    28: [26, 27, 29, 30],                  # Grecia
    29: [22, 28, 30],                      # Creta
    30: [25, 28, 29, 31, 33, 40],          # Bitinia
    31: [30, 32, 33],                      # Galacia
    32: [31, 33, 34],                      # Capadocia
    33: [30, 31, 32, 34, 35],              # Cilicia
    34: [32, 33, 35, 36],                  # Siria
    35: [33, 34, 36, 37],                  # Fenicia
    36: [34, 35, 38],                      # Mesopotamia
    37: [22, 35, 38],                      # Egipto
    38: [36, 37],                          # Arabia
    39: [24, 40, 41],                      # Sarmacia
    40: [30, 39, 41],                      # Escitia
    41: [15, 16, 39, 40],                  # Germania Oriental
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
        #: territorios de cada region: region -> lista de ids
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
