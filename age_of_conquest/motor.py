"""Motor de simulacion con Lista de Eventos Futuros (LEF).

Orquesta la evaluacion secuencial de las ecuaciones del modelo. Cada turno
de jugador consta de tres fases (Seccion 0 del documento):

    REFUERZO -> ATAQUE (multiple) -> MOVIMIENTO (unico) -> FIN_TURNO

y al completarse la ronda de todos los jugadores activos se ejecuta la
ACTUALIZACION_GLOBAL (poblacion, felicidad, rebeliones) antes de iniciar
la siguiente ronda. La LEF es una cola de eventos con prioridad (los
eventos GLOBAL se intercalan con mayor prioridad que los REFUERZO).

El motor delega las decisiones de cada jugador en un ControladorJugador:
    - ControladorIA: perfiles Agresivo / Defensivo / Equilibrado.
    - ControladorHumano: interaccion por consola (modulo cli).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import economia
from .combate import ResultadoBatalla, ataque_viable, batalla
from .config import CONFIG, Config
from .estado import (
    FASE_ATAQUE,
    FASE_FIN_TURNO,
    FASE_GLOBAL,
    FASE_MOVIMIENTO,
    FASE_REFUERZO,
    NEUTRAL,
    GameState,
    Jugador,
)
from .mapa import CONTINENTE_BONUS_SOLDADOS

# Prioridades de la LEF: menor numero = se procesa antes
PRIO_GLOBAL = 0
PRIO_REFUERZO = 1
PRIO_FASES = 2


@dataclass(order=True)
class Evento:
    """Entrada de la LEF: un suceso programado en la simulacion."""

    prioridad: int
    secuencia: int
    tipo: str = field(compare=False)
    jugador: int = field(default=NEUTRAL, compare=False)


class ControladorJugador:
    """Interfaz de decisiones de un jugador (IA o humano).

    El motor llama a estos metodos cuando el evento de fase corresponde
    al jugador p. Cada controlador recibe el motor para ejecutar ataques
    y movimientos con sus primitivas.
    """

    def colocar_refuerzos(self, estado: GameState, jugador: Jugador, cantidad: int) -> None:
        raise NotImplementedError

    def fase_ataque(self, motor: "Motor", estado: GameState, jugador: Jugador) -> None:
        raise NotImplementedError

    def fase_movimiento(self, motor: "Motor", estado: GameState, jugador: Jugador) -> None:
        raise NotImplementedError


class Motor:
    """Nucleo de la simulacion: procesa la LEF hasta el fin de la partida."""

    def __init__(
        self,
        estado: GameState,
        controladores: dict[int, ControladorJugador],
        rng: random.Random | None = None,
    ) -> None:
        self.estado = estado
        self.controladores = controladores
        self.rng = rng or random.Random()
        self.lef: list[Evento] = []
        self._secuencia = 0
        self.max_turnos: int | None = None  # limite opcional para demos

    # ------------------------------------------------------------------
    # LEF: programacion y ciclo principal
    # ------------------------------------------------------------------
    def _programar(self, tipo: str, jugador: int = NEUTRAL, prioridad: int = PRIO_FASES) -> None:
        self.lef.append(Evento(prioridad, self._secuencia, tipo, jugador))
        self._secuencia += 1
        self.lef.sort()

    def _siguiente_jugador(self, p: int) -> int:
        """Siguiente jugador activo despues de p (orden circular por id)."""
        activos = self.estado.jugadores_activos()
        if not activos:
            return NEUTRAL
        siguientes = [j for j in activos if j > p]
        return siguientes[0] if siguientes else activos[0]

    def _siguiente_fase(self, p: int) -> None:
        """Programa REFUERZO del siguiente jugador, o GLOBAL si p cierra ronda."""
        activos = self.estado.jugadores_activos()
        if not activos:
            self._programar(FASE_GLOBAL, NEUTRAL, PRIO_GLOBAL)
            return
        if p == activos[-1]:
            self._programar(FASE_GLOBAL, NEUTRAL, PRIO_GLOBAL)
        else:
            self._programar(FASE_REFUERZO, self._siguiente_jugador(p), PRIO_REFUERZO)

    def iniciar(self, max_turnos: int | None = None) -> None:
        """Reparte el mapa, programa el primer REFUERZO y ejecuta la LEF."""
        self._repartir_mapa()
        self._programar(FASE_REFUERZO, self.estado.jugadores_activos()[0], PRIO_REFUERZO)
        self.ejecutar(max_turnos)

    def ejecutar(self, max_turnos: int | None = None) -> None:
        """Bucle principal: procesa eventos de la LEF hasta el fin.

        El parametro max_turnos limita la simulacion a n rondas globales
        (util para demos y tests).
        """
        self.max_turnos = max_turnos
        while self.lef and self.estado.simulacion_activa:
            if self.max_turnos is not None and self.estado.turno >= self.max_turnos:
                self.estado.simulacion_activa = False
                break
            self.procesar_siguiente()

    def procesar_siguiente(self) -> Evento | None:
        """Procesa un unico evento de la LEF y lo devuelve (o None).

        Permite a la interfaz de consola ejecutar la simulacion paso a
        paso e imprimir los eventos registrados.
        """
        if not self.lef or not self.estado.simulacion_activa:
            return None
        ev = self.lef.pop(0)
        self._procesar(ev)
        return ev

    def _repartir_mapa(self) -> None:
        """Distribucion inicial aleatoria de territorios entre los jugadores.

        El documento no especifica el reparto inicial; se usa reparto
        circular uniforme sobre los territorios barajados (decision de
        diseno).
        """
        estado = self.estado
        jugadores = list(estado.jugadores.keys())
        ids = list(estado.provincias.keys())
        self.rng.shuffle(ids)
        for idx, i in enumerate(ids):
            prov = estado.provincias[i]
            prov.dueno = jugadores[idx % len(jugadores)]
            prov.ejercitos = estado.config.ejercitos_iniciales
        estado.registrar("Mapa repartido entre los jugadores")

    def _procesar(self, ev: Evento) -> None:
        estado = self.estado
        estado.fase_actual = ev.tipo  # Phi(t): fase activa del turno
        if ev.tipo in (FASE_REFUERZO, FASE_ATAQUE, FASE_MOVIMIENTO, FASE_FIN_TURNO):
            estado.jugador_activo = ev.jugador
        if ev.tipo == FASE_REFUERZO:
            self._fase_refuerzo(ev.jugador)
        elif ev.tipo == FASE_ATAQUE:
            self._fase_ataque(ev.jugador)
        elif ev.tipo == FASE_MOVIMIENTO:
            self._fase_movimiento(ev.jugador)
        elif ev.tipo == FASE_FIN_TURNO:
            self._fin_turno(ev.jugador)
        elif ev.tipo == FASE_GLOBAL:
            self._actualizacion_global()

    # ------------------------------------------------------------------
    # Fases del turno
    # ------------------------------------------------------------------
    def _fase_refuerzo(self, p: int) -> None:
        estado = self.estado
        if not estado.jugadores[p].activo or not estado.territorios_de(p):
            # Jugador eliminado mientras su REFUERZO esperaba en la LEF
            self._siguiente_fase(p)
            return
        base, bonus = self.refuerzos_desglose(p)
        # b(p,t): bonificacion por continentes se almacena como estado
        estado.jugadores[p].bonus_continente = bonus
        estado.registrar(
            f"Jugador {p} recibe {base + bonus} refuerzos "
            f"(base {base} + continentes {bonus})"
        )
        self.controladores[p].colocar_refuerzos(estado, estado.jugadores[p], base + bonus)
        self._programar(FASE_ATAQUE, p)

    def _fase_ataque(self, p: int) -> None:
        estado = self.estado
        if not estado.jugadores[p].activo or not estado.territorios_de(p):
            self._siguiente_fase(p)
            return
        self.controladores[p].fase_ataque(self, estado, estado.jugadores[p])
        self._programar(FASE_MOVIMIENTO, p)

    def _fase_movimiento(self, p: int) -> None:
        estado = self.estado
        if estado.jugadores[p].activo and estado.territorios_de(p):
            self.controladores[p].fase_movimiento(self, estado, estado.jugadores[p])
        self._programar(FASE_FIN_TURNO, p)

    def _fin_turno(self, p: int) -> None:
        estado = self.estado
        # 2.1: liquidacion del tesoro del jugador que termina su turno
        if estado.jugadores[p].activo and estado.territorios_de(p):
            res = economia.liquidar_tesoro(estado, p)
            estado.registrar(
                f"FIN_TURNO {p}: +{res.ingresos:.1f} impuestos "
                f"-{res.gasto_militar:.1f} militar -{res.gasto_infra:.1f} infra "
                f"+{res.bonus_oro:.1f} continentes -{res.costo_reclutas:.1f} reclutas "
                f"-> tesoro {res.tesoro_final:.1f}"
            )
            if res.desertados:
                estado.registrar(f"Bancarrota de {p}: {res.desertados} soldados desertan")
        self._siguiente_fase(p)

    def _actualizacion_global(self) -> None:
        estado = self.estado
        cfg = estado.config

        # 2.2: crecimiento poblacional logistico de todas las provincias
        economia.crecimiento_poblacional(estado)
        # 2.3: felicidad con clip [0,1]
        economia.actualizar_felicidad(estado)
        # 2.8: muestreo Monte Carlo del riesgo de rebelion
        rebeldes = economia.comprobar_rebeliones(estado, self.rng)
        for i in rebeldes:
            estado.registrar(
                f"Rebelion: {estado.mapa.territorio(i).nombre} se independiza"
            )

        # 2.7.1: eliminacion de jugadores sin territorios
        for jid, j in list(estado.jugadores.items()):
            if j.activo and not estado.territorios_de(jid):
                j.activo = False
                estado.registrar(f"Jugador {jid} ({j.nombre}) eliminado")

        # 2.7.2: condicion de victoria: sigma_sim = 0 <=> N_a = 1
        activos = estado.jugadores_activos()
        if estado.numero_activos() == 1:
            estado.ganador = activos[0]
            estado.simulacion_activa = False
            estado.registrar(f"VICTORIA del jugador {activos[0]}")
            return
        if not activos:
            # Caso borde: todos los jugadores eliminados por rebeliones
            estado.simulacion_activa = False
            estado.registrar("Sin jugadores activos: la partida termina")
            return

        # Reinicio de indicadores de turno para la siguiente ronda
        for j in estado.jugadores.values():
            j.reiniciar_turno()
        for prov in estado.provincias.values():
            prov.ocupada_reciente = False
            prov.reiniciar_flujos()
        estado.turno += 1

        if self.max_turnos is not None and estado.turno >= self.max_turnos:
            estado.simulacion_activa = False
            return
        self._programar(FASE_REFUERZO, activos[0], PRIO_REFUERZO)

    # ------------------------------------------------------------------
    # Primitivas usadas por los controladores
    # ------------------------------------------------------------------
    def refuerzos_totales(self, p: int) -> int:
        """r(p) = max(r_min, floor(T/rho)) + suma b_c (Seccion 2.5)."""
        base, bonus = self.refuerzos_desglose(p)
        return base + bonus

    def refuerzos_desglose(self, p: int) -> tuple[int, int]:
        """Devuelve (base, bonus) de la ecuacion de refuerzos (Seccion 2.5).

        base  = max(r_min, floor(T / rho))
        bonus = suma de b_c de los continentes controlados por completo
        """
        cfg = self.estado.config
        t = self.estado.cantidad_territorios(p)
        base = max(cfg.r_min, t // cfg.rho)
        bonus = sum(
            CONTINENTE_BONUS_SOLDADOS.get(c, 0)
            for c in self.estado.dueño_continentes(p)
        )
        return base, bonus

    def colocar_refuerzos(self, p: int, asignacion: dict[int, int]) -> None:
        """Aplica un vector de refuerzos r_i a las provincias de p."""
        estado = self.estado
        for i, n in asignacion.items():
            if n <= 0:
                continue
            prov = estado.provincias[i]
            if prov.dueno != p:
                raise ValueError(f"La provincia {i} no pertenece al jugador {p}")
            prov.ejercitos += n

    def ejecutar_ataque(self, origen: int, destino: int, max_rondas: int | None = None) -> ResultadoBatalla:
        """Resuelve un ataque origen -> destino (Secciones 2.4 y 2.7).

        Valida viabilidad (adyacencia, pertenencia, A >= 2) y aplica las
        consecuencias: bajas, conquista con transferencia m_oc, dano
        colateral civil, indicadores de guerra y eliminacion del defensor
        si perdio su ultimo territorio.
        """
        estado = self.estado
        p = estado.jugador_activo
        cfg = estado.config

        prov_o = estado.provincias[origen]
        prov_d = estado.provincias[destino]
        if prov_o.dueno != p:
            raise ValueError("La provincia origen no pertenece al jugador activo")
        if prov_d.dueno == p:
            raise ValueError("No se puede atacar un territorio propio")
        if not estado.mapa.son_adyacentes(origen, destino):
            raise ValueError("Las provincias no son adyacentes")
        if not ataque_viable(prov_o.ejercitos):
            raise ValueError("Se necesitan al menos 2 ejercitos para atacar")

        q = prov_d.dueno
        res = batalla(
            prov_o.ejercitos,
            prov_d.ejercitos,
            prov_d,
            self.rng,
            cfg,
            max_rondas=max_rondas,
        )

        # Aplicacion de bajas (2.4.4)
        prov_o.ejercitos = res.ejercitos_origen
        prov_d.ejercitos = res.ejercitos_destino

        # Dano colateral sobre la poblacion civil (2.2)
        dano = economia.aplicar_dano_colateral(
            prov_d, res.bajas_atacante + res.bajas_defensor, cfg
        )
        estado.registrar(
            f"Ataque {origen}->{destino}: {res.rondas} rondas, "
            f"bajas atk={res.bajas_atacante} def={res.bajas_defensor}, "
            f"civiles perdidos={dano}"
        )

        # Indicadores de guerra (W_p y W_q de la Seccion 2.3)
        estado.jugadores[p].en_guerra = True
        if q != NEUTRAL:
            estado.jugadores[q].en_guerra = True

        # Conquista y ocupacion (2.4.5)
        if res.conquistada:
            prov_d.dueno = p
            prov_d.ocupada_reciente = True
            estado.jugadores[p].conquistas_turno += 1
            estado.jugadores[p].victorias_turno = True
            estado.registrar(
                f"CONQUISTA: {estado.mapa.territorio(destino).nombre} "
                f"cae en manos del jugador {p} ({res.transferidas} tropas transferidas)"
            )
            # 2.7.1: si el defensor perdio su ultimo territorio, eliminado
            if q != NEUTRAL and estado.jugadores[q].activo and not estado.territorios_de(q):
                estado.jugadores[q].activo = False
                estado.registrar(f"Jugador {q} ({estado.jugadores[q].nombre}) eliminado")
        return res

    def ejecutar_movimiento(self, origen: int, destino: int, cantidad: int) -> bool:
        """Movimiento unico de reagrupacion (Seccion 2.6).

        Condiciones: mismo dueno (jugador activo), adyacentes y
        1 <= cantidad < A(origen).
        """
        estado = self.estado
        p = estado.jugador_activo
        prov_o = estado.provincias[origen]
        prov_d = estado.provincias[destino]
        if prov_o.dueno != p or prov_d.dueno != p:
            raise ValueError("Ambas provincias deben pertenecer al jugador activo")
        if not estado.mapa.son_adyacentes(origen, destino):
            raise ValueError("Las provincias no son adyacentes")
        if not (1 <= cantidad < prov_o.ejercitos):
            raise ValueError("Cantidad invalida: 1 <= n < ejercitos del origen")
        prov_o.ejercitos -= cantidad
        prov_d.ejercitos += cantidad
        estado.registrar(
            f"Movimiento {origen}->{destino}: {cantidad} tropas reagrupadas"
        )
        return True
