"""Escenarios historicos: imperios fijos con territorios iniciales definidos.

Cada escenario corresponde a una epoca del juego de referencia y define:
    - los imperios participantes (nombre, perfil estrategico, si es humano);
    - sus territorios iniciales (distribucion FIJA, sin reparto aleatorio);
    - su capital (que recibe un refuerzo inicial extra de tropas).

Las provincias no asignadas a ningun imperio quedan neutrales (tribus y
pueblos independientes de la epoca) con la guarnicion de milicias definida
en la configuracion.

Escenarios disponibles:
    "roma"      -> Ascenso de Roma (264 a.C.)
    "caida"     -> Caida de Roma (452 d.C.)
    "medieval"  -> Edad Media (1066 d.C.)
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .estado import (
    NEUTRAL,
    PERFIL_AGRESIVO,
    PERFIL_DEFENSIVO,
    PERFIL_EQUILIBRADO,
    PERFIL_HUMANO,
    GameState,
)

#: tropas adicionales de la capital al inicio del escenario
BONUS_CAPITAL = 4


@dataclass
class ImperioEscenario:
    """Definicion fija de un imperio dentro de un escenario."""

    nombre: str
    perfil: str
    humano: bool
    territorios: list[int]   # provincias iniciales (ids del mapa)
    capital: int             # capital: recibe tropas adicionales


@dataclass
class Escenario:
    """Epoca historica jugable con imperios predeterminados."""

    nombre: str
    epoca: str
    imperios: list[ImperioEscenario]


# ---------------------------------------------------------------------------
# Definicion de los escenarios
# ---------------------------------------------------------------------------

ESCENARIOS: dict[str, Escenario] = {
    "roma": Escenario(
        nombre="Ascenso de Roma",
        epoca="264 a.C.",
        imperios=[
            ImperioEscenario("Republica Romana", PERFIL_HUMANO, True,
                             [11, 12, 13, 14], capital=12),
            ImperioEscenario("Cartago", PERFIL_EQUILIBRADO, False,
                             [19, 20, 21, 9, 10], capital=21),
            ImperioEscenario("Egipto Ptolemaico", PERFIL_DEFENSIVO, False,
                             [37, 22, 35], capital=37),
            ImperioEscenario("Macedonia", PERFIL_AGRESIVO, False,
                             [26, 27, 28, 25], capital=26),
        ],
    ),
    "caida": Escenario(
        nombre="Caida de Roma",
        epoca="452 d.C.",
        imperios=[
            ImperioEscenario("Imperio Romano de Occidente", PERFIL_HUMANO, True,
                             [11, 12, 13, 14, 6, 4], capital=12),
            ImperioEscenario("Imperio Bizantino", PERFIL_EQUILIBRADO, False,
                             [28, 29, 30, 33, 34, 37], capital=30),
            ImperioEscenario("Hunos", PERFIL_AGRESIVO, False,
                             [39, 40, 41], capital=39),
            ImperioEscenario("Reino Visigodo", PERFIL_AGRESIVO, False,
                             [7, 8, 9, 10], capital=7),
        ],
    ),
    "medieval": Escenario(
        nombre="Edad Media",
        epoca="1066 d.C.",
        imperios=[
            ImperioEscenario("Reino de Inglaterra", PERFIL_HUMANO, True,
                             [0, 2], capital=0),
            ImperioEscenario("Reino de Francia", PERFIL_DEFENSIVO, False,
                             [3, 4, 5, 6], capital=4),
            ImperioEscenario("Sacro Imperio Romano Germanico", PERFIL_AGRESIVO, False,
                             [15, 16, 17, 18, 11], capital=16),
            ImperioEscenario("Imperio Bizantino", PERFIL_DEFENSIVO, False,
                             [25, 28, 29, 30, 31, 33], capital=30),
            ImperioEscenario("Al-Andalus", PERFIL_EQUILIBRADO, False,
                             [8, 9, 10], capital=9),
        ],
    ),
}


def validar_escenario(esc: Escenario, mapa) -> list[str]:
    """Comprueba la coherencia de un escenario contra el mapa.

    Devuelve una lista de errores (vacia si es valido): territorios
    duplicados entre imperios, ids fuera de rango y capitales fuera de
    los territorios de su imperio.
    """
    errores: list[str] = []
    vistos: set[int] = set()
    for imp in esc.imperios:
        for tid in imp.territorios:
            if not (0 <= tid < mapa.n):
                errores.append(f"{imp.nombre}: territorio {tid} fuera de rango")
            if tid in vistos:
                errores.append(f"Territorio {tid} asignado a mas de un imperio")
            vistos.add(tid)
        if imp.capital not in imp.territorios:
            errores.append(f"{imp.nombre}: la capital {imp.capital} no le pertenece")
    return errores


def aplicar_escenario(
    estado: GameState,
    esc: Escenario,
    config: Config | None = None,
    todos_ia: bool = False,
) -> None:
    """Prepara el estado con los imperios y territorios fijos del escenario.

    Los territorios de cada imperio reciben los ejercitos iniciales de la
    configuracion y la capital recibe BONUS_CAPITAL adicionales. Las
    provincias restantes quedan neutrales con su guarnicion de milicias.
    Si todos_ia es True, se ignora el indicador humano del escenario
    (usado por el modo demo).
    """
    cfg = config or estado.config
    for imp in esc.imperios:
        humano = imp.humano and not todos_ia
        perfil = imp.perfil
        if not humano and perfil == PERFIL_HUMANO:
            # En modo demo el imperio principal juega con IA equilibrada
            perfil = PERFIL_EQUILIBRADO
        j = estado.crear_jugador(
            imp.nombre,
            perfil=perfil,
            humano=humano,
        )
        for tid in imp.territorios:
            prov = estado.provincias[tid]
            prov.dueno = j.id
            prov.ejercitos = cfg.ejercitos_iniciales
        # La capital concentra tropas adicionales
        estado.provincias[imp.capital].ejercitos += BONUS_CAPITAL
    for prov in estado.provincias.values():
        if prov.dueno == NEUTRAL:
            prov.ejercitos = cfg.guarnicion_neutral
    estado.registrar(
        f"Escenario '{esc.nombre}' ({esc.epoca}): {len(esc.imperios)} imperios "
        f"con territorios fijos"
    )


def crear_controladores(
    estado: GameState,
    controlador_ia_cls,
    controlador_humano_cls,
) -> dict[int, object]:
    """Crea los controladores (IA o humano) para los jugadores del estado."""
    controladores = {}
    for j in estado.jugadores.values():
        if j.humano:
            controladores[j.id] = controlador_humano_cls()
        else:
            controladores[j.id] = controlador_ia_cls()
    return controladores
