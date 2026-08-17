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
from .config import Config, TERRENO_NOMBRES
from .escenarios import ESCENARIOS, aplicar_escenario, crear_controladores
from .estado import NEUTRAL, GameState, Jugador
from .ia import ControladorIA
from .mapa import CONTINENTE_BONUS_SOLDADOS, CONTINENTE_NOMBRES, MAPA
from .motor import FASE_REFUERZO, PRIO_REFUERZO, ControladorJugador, Motor


class Consola:
    """Abstraccion de entrada/salida (permite tests de la interfaz)."""

    def print(self, texto: str = "") -> None:
        print(texto)

    def input(self, prompt: str) -> str:
        return input(prompt)


def crear_partida(
    seed: int | None = None,
    escenario: str = "roma",
    todos_ia: bool = False,
    imperio_humano: str | None = None,
    config: Config | None = None,
) -> tuple[GameState, Motor, str]:
    """Prepara el estado y el motor de una partida nueva.

    Aplica el escenario historico indicado (imperios y territorios
    iniciales fijos, sin reparto aleatorio) y devuelve (estado, motor,
    nombre del escenario). El humano controla imperio_humano (por
    defecto, el imperio principal del escenario). Si todos_ia es True,
    todos los imperios son controlados por la IA (modo demo).
    """
    esc = ESCENARIOS[escenario]
    if imperio_humano is not None and not any(
        imp.nombre == imperio_humano for imp in esc.imperios
    ):
        nombres = ", ".join(imp.nombre for imp in esc.imperios)
        raise ValueError(
            f"El escenario '{esc.nombre}' no tiene el imperio "
            f"'{imperio_humano}'. Disponibles: {nombres}."
        )
    estado = GameState(config)
    estado.inicializar_provincias()
    aplicar_escenario(
        estado, esc, todos_ia=todos_ia, humano_nombre=imperio_humano
    )
    controladores = crear_controladores(estado, ControladorIA, ControladorHumano)
    rng = random.Random(seed)
    motor = Motor(estado, controladores, rng)
    return estado, motor, esc.nombre


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
# Menu principal interactivo
# ---------------------------------------------------------------------------

def _leer(c: "Consola", prompt: str, por_defecto: str = "") -> str:
    """Lee una linea del usuario; devuelve el valor por defecto si la
    entrada esta vacia o llega EOF (permite automatizar con tuberias)."""
    try:
        valor = c.input(prompt).strip()
    except EOFError:
        return por_defecto
    return valor if valor else por_defecto


def menu_principal(consola: "Consola | None" = None) -> None:
    """Menu de inicio: elige escenario, modo de juego, turnos y semilla."""
    c = consola or Consola()
    c.print()
    c.print("=" * 70)
    c.print("  AGE OF CONQUEST - MOTOR DE SIMULACION (proyecto SIMUSIST)")
    c.print("=" * 70)

    # --- Eleccion de escenario ---
    c.print("\nEscenarios disponibles:")
    claves = list(ESCENARIOS)
    for i, clave in enumerate(claves, 1):
        esc = ESCENARIOS[clave]
        imperios = ", ".join(imp.nombre for imp in esc.imperios)
        c.print(f"  {i}) {esc.nombre} ({esc.epoca})")
        c.print(f"     Imperios: {imperios}")
    eleccion = _leer(c, f"\nElige escenario [1-{len(claves)}] (1): ", "1")
    try:
        indice = int(eleccion) - 1
        if not (0 <= indice < len(claves)):
            indice = 0
    except ValueError:
        indice = 0
    escenario = claves[indice]
    esc = ESCENARIOS[escenario]

    # --- Eleccion de modo ---
    c.print("\nModo de juego:")
    c.print("  1) Partida interactiva (tu contra la IA)")
    c.print("  2) Demo automatica (todos los imperios con IA)")
    modo = _leer(c, "\nElige modo [1-2] (1): ", "1")
    demo = modo.strip() == "2"

    # --- Eleccion del imperio del humano (solo modo interactivo) ---
    imperio_humano: str | None = None
    if not demo:
        c.print("\nImperios del escenario:")
        for i, imp in enumerate(esc.imperios, 1):
            c.print(f"  {i}) {imp.nombre}")
        eleccion = _leer(
            c,
            f"\nElige imperio [1-{len(esc.imperios)}] (1): ",
            "1",
        )
        try:
            indice = int(eleccion) - 1
            if not (0 <= indice < len(esc.imperios)):
                indice = 0
        except ValueError:
            indice = 0
        imperio_humano = esc.imperios[indice].nombre

    # --- Parametros ---
    if demo:
        turnos = _leer(c, "Turnos de la demo (5): ", "5")
        try:
            max_turnos = max(1, int(turnos))
        except ValueError:
            max_turnos = 5
    else:
        turnos = _leer(c, "Limite de turnos [Enter = sin limite]: ", "")
        try:
            max_turnos = int(turnos) if turnos else None
        except ValueError:
            max_turnos = None

    semilla = _leer(c, "Semilla aleatoria [Enter = al azar]: ", "")
    try:
        seed = int(semilla) if semilla else None
    except ValueError:
        seed = None

    if demo:
        partida_demo(seed=seed, max_turnos=max_turnos, escenario=escenario, consola=c)
    else:
        partida_interactiva(
            seed=seed,
            max_turnos=max_turnos,
            escenario=escenario,
            imperio_humano=imperio_humano,
            consola=c,
        )


# ---------------------------------------------------------------------------
# Bucles de partida
# ---------------------------------------------------------------------------

def partida_interactiva(
    seed: int | None = None,
    max_turnos: int | None = None,
    escenario: str = "roma",
    imperio_humano: str | None = None,
    consola: Consola | None = None,
) -> None:
    """Partida estandar: el humano controla imperio_humano (por defecto el
    imperio principal del escenario) contra los demas imperios (IA)."""
    c = consola or Consola()
    estado, motor, nombre_esc = crear_partida(
        seed=seed, escenario=escenario, imperio_humano=imperio_humano
    )
    # La distribucion de territorios es fija (escenario); solo se programa
    # el primer REFUERZO de la LEF.
    motor._programar(FASE_REFUERZO, estado.jugadores_activos()[0], PRIO_REFUERZO)

    c.print("=" * 70)
    c.print("  AGE OF CONQUEST - MOTOR DE SIMULACION (proyecto SIMUSIST)")
    c.print(f"  Escenario: {nombre_esc} ({ESCENARIOS[escenario].epoca})")
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


def partida_demo(
    seed: int | None = None,
    max_turnos: int = 5,
    escenario: str = "roma",
    consola: Consola | None = None,
) -> None:
    """Demo automatica: todos los imperios del escenario son IA."""
    c = consola or Consola()
    estado, motor, nombre_esc = crear_partida(
        seed=seed, escenario=escenario, todos_ia=True
    )
    motor._programar(FASE_REFUERZO, estado.jugadores_activos()[0], PRIO_REFUERZO)

    c.print("=" * 70)
    c.print("  AGE OF CONQUEST - DEMO AUTOMATICA (todos los imperios son IA)")
    c.print(f"  Escenario: {nombre_esc} ({ESCENARIOS[escenario].epoca})")
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
