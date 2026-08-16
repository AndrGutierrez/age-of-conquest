"""Estructuras de estado del sistema (Seccion 1.2 del documento).

Variables de estado que persisten entre turnos:
    Provincia: o(i), A(i), P(i), H(i), tau(i), I(i), F(i), sigma(i)
    Jugador:   E(p), a(p), L(p), C(p), e(p), b(p)
    Globales:  t, fase activa, jugador activo, indicador de simulacion
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import CONFIG, Config
from .mapa import Mapa, Territorio

# ---------------------------------------------------------------------------
# Constantes de jugador
# ---------------------------------------------------------------------------

#: id del "jugador" neutral (provincias rebeldes / independientes)
NEUTRAL = 0

#: Perfiles estrategicos de la IA (parametro fijo e(p))
PERFIL_AGRESIVO = "Agresivo"
PERFIL_DEFENSIVO = "Defensivo"
PERFIL_EQUILIBRADO = "Equilibrado"
PERFIL_HUMANO = "Humano"

# ---------------------------------------------------------------------------
# Fases del turno (Phi(t) en el documento)
# ---------------------------------------------------------------------------

FASE_REFUERZO = "REFUERZO"
FASE_ATAQUE = "ATAQUE"
FASE_MOVIMIENTO = "MOVIMIENTO"
FASE_FIN_TURNO = "FIN_TURNO"
FASE_GLOBAL = "ACTUALIZACION_GLOBAL"


@dataclass
class Provincia:
    """Estado de una provincia i en el instante t (Seccion 1.2.1)."""

    id: int
    dueno: int = NEUTRAL            # o(i): jugador propietario (0 = neutral)
    ejercitos: int = 0              # A(i): efectivos militares estacionados
    poblacion: float = 0.0          # P(i): poblacion civil
    felicidad: float = 1.0          # H(i): felicidad normalizada en [0, 1]
    impuesto: float = 0.20          # tau(i): tasa impositiva en [0, tau_max]
    infraestructura: int = 0        # I(i): nivel de infraestructura
    fortificacion: int = 0          # F(i): nivel de fortificacion
    ocupada_reciente: bool = False  # O_new(i): conquistada en el turno actual

    # --- variables de flujo del turno actual (Seccion 1.3) ---
    reclutas_turno: int = 0         # delta_rec(i): soldados reclutados (y costo)
    bajas_combate: int = 0          # delta_comb(i): dano colateral civil
    hubo_batalla: bool = False      # hubo combate en i este turno

    def terreno(self) -> Territorio:
        return Mapa.territorio(self.id)

    def reiniciar_flujos(self) -> None:
        """Limpia las variables de flujo al cerrar la ronda global."""
        self.reclutas_turno = 0
        self.bajas_combate = 0
        self.hubo_batalla = False


@dataclass
class Jugador:
    """Estado de un imperio p en el instante t (Seccion 1.2.2)."""

    id: int
    nombre: str
    perfil: str = PERFIL_HUMANO   # e(p): Agresivo / Defensivo / Equilibrado / Humano
    humano: bool = False
    tesoro: float = 0.0           # E(p): oro acumulado
    activo: bool = True           # a(p): 1 si sigue en partida, 0 si eliminado
    tecnologia: int = 0           # L(p): nivel tecnologico (estado, sin uso aun)
    conquistas_turno: int = 0     # C(p): conquistas acumuladas en el turno

    # --- indicadores auxiliares del turno (Seccion 2.3) ---
    en_guerra: bool = False       # W(p): en guerra con al menos otro jugador
    victorias_turno: bool = False  # V(p): conquisto al menos 1 territorio

    def reiniciar_turno(self) -> None:
        self.conquistas_turno = 0
        self.en_guerra = False
        self.victorias_turno = False


class GameState:
    """Estado completo del sistema: la configuracion en el instante t."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or CONFIG
        self.mapa = Mapa
        self.turno: int = 0            # t: turno global de la simulacion
        self.provincias: dict[int, Provincia] = {}
        self.jugadores: dict[int, Jugador] = {}
        self.jugador_activo: int = NEUTRAL  # p*(t)
        self.simulacion_activa: bool = True  # sigma_sim(t)
        self.ganador: int | None = None
        self.historial: list[str] = []  # registro de eventos (para el informe)

    # ------------------------------------------------------------------
    # Alta de jugadores y provincias
    # ------------------------------------------------------------------
    def crear_jugador(
        self, nombre: str, perfil: str = PERFIL_HUMANO, humano: bool = False
    ) -> Jugador:
        jid = max(self.jugadores, default=0) + 1
        j = Jugador(
            id=jid,
            nombre=nombre,
            perfil=perfil,
            humano=humano,
            tesoro=self.config.oro_inicial,
        )
        self.jugadores[jid] = j
        return j

    def inicializar_provincias(self) -> None:
        """Crea todas las provincias del mapa con valores iniciales."""
        cfg = self.config
        self.provincias = {
            t.id: Provincia(
                id=t.id,
                dueno=NEUTRAL,
                poblacion=cfg.poblacion_inicial,
                felicidad=cfg.felicidad_inicial,
                impuesto=cfg.tau_max / 2,
            )
            for t in self.mapa.territorios
        }

    def registrar(self, mensaje: str) -> None:
        """Anota un evento en el historial de la simulacion."""
        self.historial.append(f"[T{self.turno}] {mensaje}")

    # ------------------------------------------------------------------
    # Auxiliares derivadas (Seccion 1.4)
    # ------------------------------------------------------------------
    def territorios_de(self, p: int) -> list[int]:
        """Omega(p): provincias controladas por el jugador p."""
        return [i for i, pr in self.provincias.items() if pr.dueno == p]

    def frontera_de(self, p: int) -> list[int]:
        """dOmega(p): provincias propias adyacentes a territorio enemigo."""
        res = []
        for i in self.territorios_de(p):
            for k in self.mapa.vecinos(i):
                if self.provincias[k].dueno != p:
                    res.append(i)
                    break
        return res

    def interior_de(self, p: int) -> list[int]:
        """Omega_barra(p): provincias propias sin vecinos enemigos."""
        frontera = set(self.frontera_de(p))
        return [i for i in self.territorios_de(p) if i not in frontera]

    def cantidad_territorios(self, p: int) -> int:
        """T(p) = |Omega(p)|."""
        return len(self.territorios_de(p))

    def total_ejercitos(self, p: int) -> int:
        """Suma de efectivos del jugador p (para mantenimiento militar)."""
        return sum(self.provincias[i].ejercitos for i in self.territorios_de(p))

    def jugadores_activos(self) -> list[int]:
        """Jugadores vivos, en orden de turno (id creciente)."""
        return [jid for jid, j in self.jugadores.items() if j.activo]

    def dueño_continentes(self, p: int) -> list[int]:
        """Continentes c completamente controlados por p."""
        res = []
        for c, ids in self.mapa.territorios_continente.items():
            if all(self.provincias[i].dueno == p for i in ids):
                res.append(c)
        return res

    def vecinos_enemigos_de(self, i: int, p: int) -> list[int]:
        """Territorios enemigos adyacentes a i (para planificar ataques)."""
        return [
            k
            for k in self.mapa.vecinos(i)
            if self.provincias[k].dueno != p
        ]
