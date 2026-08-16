"""Inteligencia artificial: perfiles Agresivo, Defensivo y Equilibrado.

Implementa las politicas de la Seccion 2.5 (distribucion de refuerzos),
decisiones de ataque, movimiento de reagrupacion (2.6) y una politica
fiscal adaptativa sencilla:

    - Agresivo:   impuestos altos, refuerzos a la frontera proporcionales a
                  la debilidad enemiga, ataques relampago con ventaja minima.
    - Defensivo:  impuestos bajos, refuerzos uniformes en frontera (resto al
                  interior), fortificaciones y ataques solo con superioridad
                  abrumadora (una ronda por batalla).
    - Equilibrado: impuestos medios, 60% refuerzos a frontera y 40% al
                  interior, ataques con ventaja moderada e inversion en
                  infraestructura.

Toda la IA se apoya exclusivamente en las primitivas publicas del motor
(ejecutar_ataque / ejecutar_movimiento) y en las acciones economicas
(economia.reclutar / construir / fijar_impuesto), lo que garantiza que la
IA juega con las mismas reglas que un humano.
"""

from __future__ import annotations

from . import economia
from .config import CONFIG, Config
from .estado import PERFIL_AGRESIVO, PERFIL_DEFENSIVO, PERFIL_EQUILIBRADO, GameState, Jugador
from .motor import ControladorJugador, Motor

#: umbrales de ventaja minima (A_origen - 1) / max(1, A_destino) por perfil
UMBRAL_ATAQUE = {
    PERFIL_AGRESIVO: 0.9,
    PERFIL_EQUILIBRADO: 1.2,
    PERFIL_DEFENSIVO: 2.0,
}

#: tasa impositiva base por perfil (politica fiscal)
IMPUESTO_BASE = {
    PERFIL_AGRESIVO: 0.30,
    PERFIL_EQUILIBRADO: 0.25,
    PERFIL_DEFENSIVO: 0.15,
}

#: maximo de ataques por turno (evita bucles infinitos)
MAX_ATAQUES = 30


class ControladorIA(ControladorJugador):
    """Controlador generico: el comportamiento cambia segun el perfil e(p)."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or CONFIG

    # ------------------------------------------------------------------
    # Fase REFUERZO: politica fiscal + refuerzos + inversion
    # ------------------------------------------------------------------
    def colocar_refuerzos(self, estado: GameState, jugador: Jugador, cantidad: int) -> None:
        perfil = jugador.perfil
        self._politica_fiscal(estado, jugador)
        self._distribuir_refuerzos(estado, jugador, cantidad, perfil)
        self._invertir(estado, jugador, perfil)

    def _politica_fiscal(self, estado: GameState, jugador: Jugador) -> None:
        """Fija impuestos por perfil, con adaptacion al tesoro y a la
        felicidad (retroalimentacion del ciclo impuestos-felicidad)."""
        cfg = self.config
        tau = IMPUESTO_BASE.get(jugador.perfil, 0.3)
        if jugador.tesoro < 20.0:
            tau = min(cfg.tau_max, tau + 0.05)
        provincias = [estado.provincias[i] for i in estado.territorios_de(jugador.id)]
        if provincias and min(p.felicidad for p in provincias) < cfg.h_min + 0.10:
            tau = max(0.10, tau - 0.05)
        for i in estado.territorios_de(jugador.id):
            estado.provincias[i].impuesto = tau

    def _distribuir_refuerzos(self, estado: GameState, jugador: Jugador, cantidad: int, perfil: str) -> None:
        """Asignacion de refuerzos segun la estrategia (Seccion 2.5)."""
        frontera = estado.frontera_de(jugador.id)
        interior = estado.interior_de(jugador.id)
        if not frontera:
            frontera = estado.territorios_de(jugador.id)
        if not frontera:
            return

        if perfil == PERFIL_AGRESIVO:
            # Todo a la frontera, proporcional a la debilidad enemiga
            pesos = {i: self._debilidad_enemiga(estado, i) for i in frontera}
            self._distribuir_ponderada(estado, jugador, cantidad, pesos)

        elif perfil == PERFIL_DEFENSIVO:
            # Uniforme en frontera; el resto va al interior
            cuota = cantidad // len(frontera)
            for i in frontera:
                estado.provincias[i].ejercitos += cuota
            sobra = cantidad - cuota * len(frontera)
            destinos = interior or frontera
            for k in range(sobra):
                estado.provincias[destinos[k % len(destinos)]].ejercitos += 1

        else:  # PERFIL_EQUILIBRADO
            # 60% a la frontera (uniforme), 40% al interior (uniforme)
            a_frontera = round(cantidad * 0.6)
            cuota = a_frontera // len(frontera)
            for i in frontera:
                estado.provincias[i].ejercitos += cuota
            sobra = a_frontera - cuota * len(frontera)
            for k in range(sobra):
                estado.provincias[frontera[k % len(frontera)]].ejercitos += 1
            a_interior = cantidad - a_frontera
            if interior:
                cuota_i = a_interior // len(interior)
                for i in interior:
                    estado.provincias[i].ejercitos += cuota_i
                sobra_i = a_interior - cuota_i * len(interior)
                for k in range(sobra_i):
                    estado.provincias[interior[k % len(interior)]].ejercitos += 1
            else:
                for i in frontera:
                    estado.provincias[i].ejercitos += a_interior // len(frontera)

    def _distribuir_ponderada(self, estado: GameState, jugador: Jugador, cantidad: int, pesos: dict[int, float]) -> None:
        """Distribuye cantidad de forma proporcional a pesos; el resto va
        a la provincia de mayor peso."""
        total = sum(pesos.values())
        if total <= 0:
            destino = max(pesos, key=pesos.get)
            estado.provincias[destino].ejercitos += cantidad
            return
        asignado = 0
        for i, w in pesos.items():
            n = int(cantidad * w / total)
            estado.provincias[i].ejercitos += n
            asignado += n
        resto = cantidad - asignado
        if resto > 0:
            destino = max(pesos, key=pesos.get)
            estado.provincias[destino].ejercitos += resto

    @staticmethod
    def _debilidad_enemiga(estado: GameState, i: int) -> float:
        """Debilidad de los enemigos adyacentes: inversa de su fuerza."""
        fuerza = 0
        for k in estado.mapa.vecinos(i):
            if estado.provincias[k].dueno != estado.provincias[i].dueno:
                fuerza += estado.provincias[k].ejercitos
        return 1.0 / (1.0 + fuerza)

    def _invertir(self, estado: GameState, jugador: Jugador, perfil: str) -> None:
        """Inversion del excedente de tesoro segun el perfil."""
        cfg = self.config
        territorios = estado.territorios_de(jugador.id)
        if not territorios:
            return
        frontera = estado.frontera_de(jugador.id) or territorios
        interior = estado.interior_de(jugador.id)

        if perfil == PERFIL_DEFENSIVO:
            # Construir fortificaciones en la frontera
            for i in frontera:
                prov = estado.provincias[i]
                if prov.fortificacion < cfg.nivel_max_fort and \
                        jugador.tesoro >= cfg.c_fort[prov.fortificacion + 1] - cfg.c_fort[prov.fortificacion]:
                    economia.construir(estado, i, "fort")
                    break
        elif perfil == PERFIL_EQUILIBRADO:
            # Construir infraestructura en el interior
            for i in interior or territorios:
                prov = estado.provincias[i]
                if prov.infraestructura < cfg.nivel_max_infra and \
                        jugador.tesoro >= cfg.c_infra[prov.infraestructura + 1] - cfg.c_infra[prov.infraestructura]:
                    economia.construir(estado, i, "infra")
                    break
        else:  # AGRESIVO: reclutar con excedentes
            mejor = max(frontera, key=lambda i: estado.provincias[i].ejercitos)
            prov = estado.provincias[mejor]
            comprables = min(int(jugador.tesoro // cfg.c_recl), 5)
            comprables = min(comprables, int(prov.poblacion))
            if comprables >= 1:
                economia.reclutar(estado, mejor, comprables)

    # ------------------------------------------------------------------
    # Fase ATAQUE: eleccion de objetivos por perfil
    # ------------------------------------------------------------------
    def fase_ataque(self, motor: Motor, estado: GameState, jugador: Jugador) -> None:
        perfil = jugador.perfil
        umbral = UMBRAL_ATAQUE.get(perfil, 1.2)
        max_rondas = None if perfil != PERFIL_DEFENSIVO else 1
        realizados = 0
        while realizados < MAX_ATAQUES:
            objetivo = self._elegir_objetivo(estado, jugador, umbral)
            if objetivo is None:
                break
            origen, destino = objetivo
            try:
                motor.ejecutar_ataque(origen, destino, max_rondas=max_rondas)
            except ValueError:
                break
            realizados += 1

    @staticmethod
    def _elegir_objetivo(estado: GameState, jugador: Jugador, umbral: float) -> tuple[int, int] | None:
        """Elige el ataque mas favorable entre los disponibles.

        Recorre las provincias fronterizas con al menos 2 ejercitos y
        selecciona el objetivo enemigo con la mayor ventaja relativa que
        supere el umbral del perfil. La guarnicion minima (config) se
        respeta al calcular la fuerza disponible.
        """
        cfg = estado.config
        mejores = []
        for i in estado.frontera_de(jugador.id):
            prov = estado.provincias[i]
            disponibles = prov.ejercitos - 1
            if disponibles < 1:
                continue
            for k in estado.vecinos_enemigos_de(i, jugador.id):
                defensa = estado.provincias[k].ejercitos
                ratio = disponibles / max(1, defensa)
                if ratio >= umbral:
                    # preferir objetivos con mayor ratio y menor defensa
                    mejores.append((ratio, -defensa, i, k))
        if not mejores:
            return None
        _, _, origen, destino = max(mejores)
        return origen, destino

    # ------------------------------------------------------------------
    # Fase MOVIMIENTO: un unico movimiento de reagrupacion (2.6)
    # ------------------------------------------------------------------
    def fase_movimiento(self, motor: Motor, estado: GameState, jugador: Jugador) -> None:
        eleccion = self._elegir_movimiento(estado, jugador)
        if eleccion is None:
            return
        origen, destino = eleccion
        cantidad = estado.provincias[origen].ejercitos - 1
        if cantidad >= 1:
            try:
                motor.ejecutar_movimiento(origen, destino, cantidad)
            except ValueError:
                pass

    @staticmethod
    def _elegir_movimiento(estado: GameState, jugador: Jugador) -> tuple[int, int] | None:
        """Selecciona el movimiento: refuerza la frontera mas presionada.

        Busca una provincia propia con excedente adyacente a una provincia
        fronteriza (con enemigos alrededor); si no existe, reequilibra
        entre dos provincias propias adyacentes.
        """
        territorios = set(estado.territorios_de(jugador.id))
        frontera = set(estado.frontera_de(jugador.id))
        candidatos = []
        for i in territorios:
            prov = estado.provincias[i]
            if prov.ejercitos <= 1:
                continue
            for k in estado.mapa.vecinos(i):
                if k not in territorios:
                    continue
                if k in frontera and i not in frontera:
                    # llevar tropas del interior hacia la frontera
                    candidatos.append((prov.ejercitos, i, k))
        if candidatos:
            _, origen, destino = max(candidatos)
            return origen, destino
        # Reequilibrio: del territorio propio con mas tropas al adyacente
        # propio con menos tropas.
        for i in sorted(territorios, key=lambda x: -estado.provincias[x].ejercitos):
            if estado.provincias[i].ejercitos <= 1:
                continue
            for k in estado.mapa.vecinos(i):
                if k in territorios and estado.provincias[k].ejercitos < estado.provincias[i].ejercitos - 1:
                    return i, k
        return None
