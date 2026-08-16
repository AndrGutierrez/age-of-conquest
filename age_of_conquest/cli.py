"""Interfaz de consola (REPL) y modo demo automatico.

Dos modos de uso:
    - Interactivo: el jugador humano dirige su imperio por comandos de
      texto durante las fases de su turno; los demas imperios son IA.
    - Demo: todos los jugadores son IA y la simulacion avanza sola
      (util para validar el motor durante n turnos sin intervencion).

Comandos del humano:
    REFUERZO:  colocar <id> <n> | distribuir | estado | mapa | auto
    ATAQUE:    atacar <origen> <destino> [1|N|total] | reclutar <id> <n>
               construir <id> fort|infra | impuesto <id> <tasa>
               impuestos <tasa> | estado | mapa | fin | auto
    MOVIMIENTO: mover <origen> <destino> <n> | estado | fin | auto
"""

from __future__ import annotations

import random

from . import economia
from .config import CONFIG, Config, TERRENO_NOMBRES
from .estado import (
    NEUTRAL,
    PERFIL_AGRESIVO,
    PERFIL_DEFENSIVO,
    PERFIL_EQUILIBRADO,
    PERFIL_HUMANO,
    GameState,
    Jugador,
    Provincia,
)
from .ia import ControladorIA
from .mapa import CONTINENTE_BONUS_SOLDADOS, CONTINENTE_NOMBRES, MAPA
from .motor import FASE_REFUERZO, PRIO_REFUERZO, ControladorJugador, Motor

#: Perfiles y nombres de los imperios de la partida estandar
IMPERIOS = [
    ("Tu Imperio", PERFIL_HUMANO, True),
    ("Imperio Rojo", PERFIL_AGRESIVO, False),
    ("Imperio Azul", PERFIL_DEFENSIVO, False),
    ("Imperio Verde", PERFIL_EQUILIBRADO, False),
]

#: Imperios de la demo automatica (todos IA)
IMPERIOS_DEMO = [
    ("Imperio Rojo", PERFIL_AGRESIVO, False),
    ("Imperio Azul", PERFIL_DEFENSIVO, False),
    ("Imperio Verde", PERFIL_EQUILIBRADO, False),
    ("Imperio Dorado", PERFIL_EQUILIBRADO, False),
]


class Consola:
    """Abstraccion de entrada/salida (permite tests de la interfaz)."""

    def print(self, texto: str = "") -> None:
        print(texto)

    def input(self, prompt: str) -> str:
        return input(prompt)


def crear_partida(
    seed: int | None = None,
    imperios: list[tuple[str, str, bool]] | None = None,
    config: Config | None = None,
) -> tuple[GameState, Motor]:
    """Prepara el estado y el motor de una partida nueva.

    El reparto de territorios y la programacion del primer REFUERZO la
    realiza Motor.iniciar() / _repartir_mapa(). Aqui solo se crean los
    jugadores y sus controladores.
    """
    estado = GameState(config)
    estado.inicializar_provincias()
    imperios = imperios or IMPERIOS
    controladores: dict[int, ControladorJugador] = {}
    for nombre, perfil, humano in imperios:
        j = estado.crear_jugador(nombre, perfil=perfil, humano=humano)
        if humano:
            controladores[j.id] = ControladorHumano()
        else:
            controladores[j.id] = ControladorIA()
    rng = random.Random(seed)
    motor = Motor(estado, controladores, rng)
    return estado, motor


# ---------------------------------------------------------------------------
# Formateo de estado para la consola
# ---------------------------------------------------------------------------

def formato_tesoro(v: float) -> str:
    return f"{v:,.1f} oro"


def tabla_provincias(estado: GameState, p: int) -> str:
    """Tabla de las provincias del jugador p: id, nombre, ejercitos,
    poblacion, felicidad, impuesto, fortificacion e infraestructura."""
    filas = []
    for i in estado.territorios_de(p):
        prov = estado.provincias[i]
        t = prov.terreno()
        es_frontera = "frontera" if estado.vecinos_enemigos_de(i, p) else "interior"
        filas.append(
            f"  [{i:>2}] {t.nombre:<24} A={prov.ejercitos:>3} "
            f"P={prov.poblacion:>6.0f} H={prov.felicidad:.2f} "
            f"tau={prov.impuesto:.0%} F={prov.fortificacion} I={prov.infraestructura} "
            f"({TERRENO_NOMBRES[t.terreno]} - {es_frontera})"
        )
    return "\n".join(filas)


def resumen_imperio(estado: GameState, j: Jugador) -> str:
    """Resumen economico y militar de un jugador."""
    p = j.id
    n = estado.cantidad_territorios(p)
    eje = estado.total_ejercitos(p)
    ingresos = economia.recaudacion_total(estado, p)
    gasto = economia.mantenimiento_militar(estado, p) + economia.mantenimiento_infra(estado, p)
    return (
        f"J{j.id} {j.nombre:<20} ({j.perfil}) | territorios: {n:>2} | "
        f"ejercitos: {eje:>4} | tesoro: {formato_tesoro(j.tesoro)} | "
        f"ingresos: {ingresos:>7.1f} | gastos: {gasto:>6.1f}"
    )


def tabla_general(estado: GameState) -> str:
    """Estado general de la partida: jugadores y su resumen."""
    lineas = [f"--- Turno {estado.turno} ---"]
    for j in estado.jugadores.values():
        if j.activo:
            lineas.append(resumen_imperio(estado, j))
        else:
            lineas.append(f"J{j.id} {j.nombre:<20} ELIMINADO")
    return "\n".join(lineas)


def mapa_compacto(estado: GameState) -> str:
    """Mapa completo agrupado por continentes (42 territorios)."""
    lineas = []
    for c, ids in MAPA.territorios_continente.items():
        lineas.append(f"{CONTINENTE_NOMBRES[c]} (bonus {CONTINENTE_BONUS_SOLDADOS[c]}):")
        for i in ids:
            prov = estado.provincias[i]
            dueno = prov.dueno
            nombre = (
                estado.jugadores[dueno].nombre if dueno != NEUTRAL else "Neutral"
            )
            lineas.append(f"  [{i:>2}] {MAPA.territorio(i).nombre:<24} {nombre:<16} A={prov.ejercitos:>3}")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Controlador humano interactivo
# ---------------------------------------------------------------------------

class ControladorHumano(ControladorJugador):
    """Toma las decisiones del jugador humano via comandos de consola."""

    def __init__(self, consola: Consola | None = None) -> None:
        self.consola = consola or Consola()
        self.ia_respaldo = ControladorIA()  # para el comando 'auto'

    # ------------------------------------------------------------------
    # Fase REFUERZO
    # ------------------------------------------------------------------
    def colocar_refuerzos(self, estado: GameState, jugador: Jugador, cantidad: int) -> None:
        c = self.consola
        c.print(f"\n=== TURNO {estado.turno} - {jugador.nombre.upper()} - FASE REFUERZO ===")
        c.print(f"Recibes {cantidad} refuerzos (max(3, territorios/3) + bonus de continentes).")
        c.print(tabla_provincias(estado, jugador.id))

        pendientes = cantidad
        while pendientes > 0:
            cmd = c.input(f"[refuerzo: {pendientes} por colocar] > ").strip()
            if not cmd:
                continue
            partes = cmd.split()
            orden = partes[0].lower()
            if orden in ("colocar", "col"):
                if len(partes) != 3:
                    c.print("Uso: colocar <id> <n>")
                    continue
                try:
                    i, n = int(partes[1]), int(partes[2])
                except ValueError:
                    c.print("Numero invalido")
                    continue
                if i not in estado.territorios_de(jugador.id):
                    c.print("Esa provincia no es tuya")
                    continue
                if not (1 <= n <= pendientes):
                    c.print(f"Cantidad invalida (1..{pendientes})")
                    continue
                estado.provincias[i].ejercitos += n
                pendientes -= n
                c.print(f"+{n} en {estado.mapa.territorio(i).nombre} "
                        f"(A={estado.provincias[i].ejercitos})")
            elif orden == "distribuir":
                # Reparto uniforme en la frontera (como la IA defensiva)
                frontera = estado.frontera_de(jugador.id) or estado.territorios_de(jugador.id)
                cuota = pendientes // len(frontera)
                for i in frontera:
                    estado.provincias[i].ejercitos += cuota
                pendientes -= cuota * len(frontera)
                for k in range(pendientes):
                    estado.provincias[frontera[k % len(frontera)]].ejercitos += 1
                pendientes = 0
                c.print("Refuerzos distribuidos en la frontera.")
            elif orden == "estado":
                c.print(tabla_provincias(estado, jugador.id))
            elif orden == "mapa":
                c.print(mapa_compacto(estado))
            elif orden == "auto":
                self.ia_respaldo.colocar_refuerzos(estado, jugador, pendientes)
                pendientes = 0
                c.print("IA: refuerzos colocados automaticamente.")
            else:
                c.print("Comandos: colocar <id> <n> | distribuir | estado | mapa | auto")

    # ------------------------------------------------------------------
    # Fase ATAQUE
    # ------------------------------------------------------------------
    def fase_ataque(self, motor: Motor, estado: GameState, jugador: Jugador) -> None:
        c = self.consola
        c.print(f"\n--- {jugador.nombre} - FASE ATAQUE (0 o mas ataques) ---")
        while True:
            cmd = c.input("[ataque] > ").strip().lower()
            if not cmd:
                continue
            partes = cmd.split()
            orden = partes[0]
            if orden == "fin":
                break
            elif orden == "auto":
                self.ia_respaldo.fase_ataque(motor, estado, jugador)
                break
            elif orden == "atacar":
                if len(partes) < 3:
                    c.print("Uso: atacar <origen> <destino> [1|N|total]")
                    continue
                try:
                    origen, destino = int(partes[1]), int(partes[2])
                except ValueError:
                    c.print("Numeros invalidos")
                    continue
                if origen not in estado.provincias or destino not in estado.provincias:
                    c.print("Id de provincia fuera de rango")
                    continue
                modo = partes[3] if len(partes) > 3 else "total"
                if modo not in ("total", "todo"):
                    try:
                        max_rondas = int(modo)
                    except ValueError:
                        c.print("Modo invalido: usa 1, N o total")
                        continue
                    if max_rondas < 1:
                        c.print("Numero de rondas invalido")
                        continue
                else:
                    max_rondas = None
                try:
                    res = motor.ejecutar_ataque(origen, destino, max_rondas)
                except ValueError as e:
                    c.print(f"Error: {e}")
                    continue
                c.print(
                    f"Resultado: {res.rondas} ronda(s), bajas atacante={res.bajas_atacante}, "
                    f"defensor={res.bajas_defensor}. "
                    + ("TERRITORIO CONQUISTADO" if res.conquistada else "Defensa resiste")
                )
                c.print(
                    f"Ahora: {estado.mapa.territorio(origen).nombre} A={estado.provincias[origen].ejercitos} | "
                    f"{estado.mapa.territorio(destino).nombre} A={estado.provincias[destino].ejercitos}"
                )
            elif orden == "reclutar":
                if len(partes) != 3:
                    c.print("Uso: reclutar <id> <n>")
                    continue
                try:
                    i, n = int(partes[1]), int(partes[2])
                except ValueError:
                    c.print("Numeros invalidos")
                    continue
                if i not in estado.provincias:
                    c.print("Id de provincia fuera de rango")
                    continue
                ok, msg = economia.reclutar(estado, i, n)
                c.print(msg if ok else f"Error: {msg}")
            elif orden == "construir":
                if len(partes) != 3:
                    c.print("Uso: construir <id> fort|infra")
                    continue
                try:
                    i = int(partes[1])
                except ValueError:
                    c.print("Numero invalido")
                    continue
                if i not in estado.provincias:
                    c.print("Id de provincia fuera de rango")
                    continue
                ok, msg = economia.construir(estado, i, partes[2])
                c.print(msg if ok else f"Error: {msg}")
            elif orden == "impuesto":
                if len(partes) != 3:
                    c.print("Uso: impuesto <id> <tasa 0..0.5>")
                    continue
                try:
                    i, tau = int(partes[1]), float(partes[2])
                except ValueError:
                    c.print("Valores invalidos")
                    continue
                if i not in estado.provincias:
                    c.print("Id de provincia fuera de rango")
                    continue
                ok, msg = economia.fijar_impuesto(estado, i, tau)
                c.print(msg if ok else f"Error: {msg}")
            elif orden == "impuestos":
                if len(partes) != 2:
                    c.print("Uso: impuestos <tasa 0..0.5>")
                    continue
                try:
                    tau = float(partes[1])
                except ValueError:
                    c.print("Tasa invalida")
                    continue
                for i in estado.territorios_de(jugador.id):
                    economia.fijar_impuesto(estado, i, tau)
                c.print(f"Impuestos fijados en {tau:.0%} en todas tus provincias.")
            elif orden == "estado":
                c.print(tabla_provincias(estado, jugador.id))
            elif orden == "mapa":
                c.print(mapa_compacto(estado))
            elif orden == "ayuda":
                c.print("Comandos: atacar <o> <d> [1|N|total] | reclutar <id> <n> | "
                        "construir <id> fort|infra | impuesto <id> <tasa> | "
                        "impuestos <tasa> | estado | mapa | auto | fin")
            else:
                c.print("Comando desconocido (ayuda)")

    # ------------------------------------------------------------------
    # Fase MOVIMIENTO (un unico movimiento)
    # ------------------------------------------------------------------
    def fase_movimiento(self, motor: Motor, estado: GameState, jugador: Jugador) -> None:
        c = self.consola
        c.print(f"\n--- {jugador.nombre} - FASE MOVIMIENTO (un unico movimiento) ---")
        while True:
            cmd = c.input("[movimiento] > ").strip().lower()
            if not cmd:
                continue
            partes = cmd.split()
            if partes[0] == "fin":
                break
            if partes[0] == "auto":
                self.ia_respaldo.fase_movimiento(motor, estado, jugador)
                break
            if partes[0] == "estado":
                c.print(tabla_provincias(estado, jugador.id))
                continue
            if partes[0] in ("mover", "mov") and len(partes) == 4:
                try:
                    origen, destino, n = int(partes[1]), int(partes[2]), int(partes[3])
                except ValueError:
                    c.print("Numeros invalidos")
                    continue
                if origen not in estado.provincias or destino not in estado.provincias:
                    c.print("Id de provincia fuera de rango")
                    continue
                try:
                    motor.ejecutar_movimiento(origen, destino, n)
                    c.print(f"Movidas {n} tropas de {estado.mapa.territorio(origen).nombre} "
                            f"a {estado.mapa.territorio(destino).nombre}.")
                    break  # el movimiento es unico (Seccion 2.6)
                except ValueError as e:
                    c.print(f"Error: {e}")
            else:
                c.print("Comandos: mover <origen> <destino> <n> | estado | auto | fin")


# ---------------------------------------------------------------------------
# Bucles de partida
# ---------------------------------------------------------------------------

def partida_interactiva(
    seed: int | None = None,
    max_turnos: int | None = None,
    consola: Consola | None = None,
) -> None:
    """Partida estandar: 1 humano contra 3 imperios IA."""
    c = consola or Consola()
    estado, motor = crear_partida(seed=seed)
    # Reparto manual: se reparte antes de iniciar la LEF para que el
    # humano vea su imperio desde el primer REFUERZO.
    motor._repartir_mapa()
    motor._programar(FASE_REFUERZO, estado.jugadores_activos()[0], PRIO_REFUERZO)

    c.print("=" * 70)
    c.print("  AGE OF CONQUEST - MOTOR DE SIMULACION (proyecto SIMUSIST)")
    c.print("=" * 70)
    c.print(tabla_general(estado))
    c.print("Comandos durante tu turno: consulta 'ayuda' en la fase de ataque.")

    ultimos = 0
    turno_anterior = estado.turno
    while motor.lef and estado.simulacion_activa:
        if max_turnos is not None and estado.turno >= max_turnos:
            estado.simulacion_activa = False
            break
        motor.procesar_siguiente()
        # Imprimir los eventos generados por el motor desde la ultima vez
        nuevos = estado.historial[ultimos:]
        ultimos = len(estado.historial)
        for linea in nuevos:
            c.print(f"  * {linea}")
        # Resumen al cierre de cada ronda global
        if estado.turno != turno_anterior:
            turno_anterior = estado.turno
            c.print("\n" + tabla_general(estado) + "\n")

    c.print("\n" + "=" * 70)
    c.print("FIN DE LA PARTIDA")
    c.print("=" * 70)
    c.print(tabla_general(estado))
    if estado.ganador is not None:
        c.print(f"\nGANADOR: {estado.jugadores[estado.ganador].nombre}")
    else:
        c.print(f"\nPartida detenida en el turno {estado.turno} (limite alcanzado).")


def partida_demo(seed: int | None = None, max_turnos: int = 5, consola: Consola | None = None) -> None:
    """Demo automatica: todos los jugadores son IA durante n turnos."""
    c = consola or Consola()
    estado, motor = crear_partida(seed=seed, imperios=IMPERIOS_DEMO)
    motor._repartir_mapa()
    motor._programar(FASE_REFUERZO, estado.jugadores_activos()[0], PRIO_REFUERZO)

    c.print("=" * 70)
    c.print("  AGE OF CONQUEST - DEMO AUTOMATICA (todos los imperios son IA)")
    c.print("=" * 70)
    c.print(tabla_general(estado))
    c.print(f"\nEjecutando {max_turnos} turnos con IA...\n")

    ultimos = 0
    turno_anterior = estado.turno
    while motor.lef and estado.simulacion_activa:
        if estado.turno >= max_turnos:
            break
        motor.procesar_siguiente()
        nuevos = estado.historial[ultimos:]
        ultimos = len(estado.historial)
        for linea in nuevos:
            c.print(f"  * {linea}")
        if estado.turno != turno_anterior:
            turno_anterior = estado.turno
            c.print("\n" + tabla_general(estado) + "\n")

    c.print("\n" + "=" * 70)
    c.print("FIN DE LA DEMO")
    c.print("=" * 70)
    c.print(tabla_general(estado))
    c.print(mapa_compacto(estado))
    if estado.ganador is not None:
        c.print(f"\nGANADOR: {estado.jugadores[estado.ganador].nombre}")
