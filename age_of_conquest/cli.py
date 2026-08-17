"""Interfaz de consola y modo demo automatico.

Dos modos de uso:
    - Interactivo: el jugador humano dirige su imperio seleccionando los
      territorios por su id (el numero entre corchetes que muestra el
      mapa) y las acciones por su numero de opcion. ENTER confirma y
      0 cancela/vuelve.
    - Demo: todos los jugadores son IA y la simulacion avanza sola
      (util para validar el motor durante n turnos sin intervencion).

Turno del humano (el mapa completo se imprime en cada fase):
    REFUERZO:  elige un territorio por su id y asigna refuerzos;
               0 = distribuir automaticamente en la frontera.
    ATAQUE:    elige un territorio por su id y luego una accion numerada:
               atacar (objetivo por id y modo por numero), reclutar,
               construir, cambiar impuesto. 0 = pasar turno sin movimiento.
    MOVIMIENTO: origen y destino por id, cantidad con numero; 0 = pasar.
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

class Menu:
    """Menu numerado de una sola tecla.

    Muestra opciones numeradas a partir de 1 y una opcion 0 opcional
    (cancelar / volver / pasar). Devuelve el numero elegido (0 = opcion 0).
    La entrada por EOF o vacia selecciona la opcion 0 por defecto, lo que
    permite automatizar flujos con tuberias.
    """

    def __init__(
        self,
        consola: "Consola",
        opciones: list[str],
        titulo: str | None = None,
        opcion_cero: str | None = None,
        prompt: str = "Elige una opcion: ",
    ) -> None:
        self.c = consola
        self.titulo = titulo
        self.opciones = opciones
        self.opcion_cero = opcion_cero
        self.prompt = prompt

    def elegir(self) -> int:
        if self.titulo:
            self.c.print(self.titulo)
        for i, texto in enumerate(self.opciones, 1):
            self.c.print(f"  {i}) {texto}")
        if self.opcion_cero is not None:
            self.c.print(f"  0) {self.opcion_cero}")
        while True:
            valor = _leer(self.c, self.prompt, "0")
            try:
                n = int(valor)
            except ValueError:
                self.c.print("Opcion invalida (escribe solo un numero)")
                continue
            if n == 0 and self.opcion_cero is not None:
                return 0
            if 1 <= n <= len(self.opciones):
                return n
            self.c.print("Opcion invalida (escribe solo un numero)")


def _pedir_entero(
    c: "Consola",
    prompt: str,
    minimo: int,
    maximo: int,
    por_defecto: int,
) -> int:
    """Pide un entero en [minimo, maximo]; ENTER acepta el valor por defecto."""
    while True:
        valor = _leer(c, prompt, str(por_defecto))
        try:
            n = int(valor)
        except ValueError:
            n = por_defecto
        if minimo <= n <= maximo:
            return n
        c.print(f"Valor invalido (escribe un numero entre {minimo} y {maximo})")


class MenuTerritorios:
    """Seleccion de un territorio escribiendo directamente su id del mapa.

    Las opciones se muestran como "[id] descripcion" y se eligen con ese
    id (no con un numero de opcion). La opcion 0 (si se define) cancela /
    vuelve / pasa. EOF o entrada vacia selecciona 0, lo que permite
    automatizar flujos con tuberias.
    """

    def __init__(
        self,
        consola: "Consola",
        pares: list[tuple[int, str]],
        titulo: str | None = None,
        opcion_cero: str | None = None,
        prompt: str = "Elige territorio (id): ",
    ) -> None:
        self.c = consola
        self.pares = pares  # lista de (id, descripcion)
        self.titulo = titulo
        self.opcion_cero = opcion_cero
        self.prompt = prompt
        self.ids = [i for i, _ in pares]

    def elegir(self) -> int:
        if self.titulo:
            self.c.print(self.titulo)
        for i, texto in self.pares:
            self.c.print(f"  [{i:>2}] {texto}")
        if self.opcion_cero is not None:
            self.c.print(f"  [ 0] {self.opcion_cero}")
        while True:
            valor = _leer(self.c, self.prompt, "0")
            try:
                n = int(valor)
            except ValueError:
                self.c.print("Opcion invalida (escribe el id de un territorio)")
                continue
            if n == 0 and self.opcion_cero is not None:
                return 0
            if n in self.ids:
                return n
            self.c.print("Opcion invalida (escribe el id de un territorio)")


def _confirmar(c: "Consola", mensaje: str) -> bool:
    """Confirmacion con ENTER (= si); 0 o 'n' cancela. EOF confirma."""
    try:
        valor = c.input(mensaje).strip().lower()
    except EOFError:
        return True
    return valor not in ("0", "n", "no", "c", "cancelar")


def _pausa(c: "Consola", mensaje: str = "Presiona ENTER para continuar...") -> None:
    try:
        c.input(mensaje)
    except EOFError:
        pass


class ControladorHumano(ControladorJugador):
    """Control del jugador humano seleccionando territorios por su id.

    Los territorios se eligen escribiendo directamente su id del mapa
    (el numero entre corchetes); las acciones y confirmaciones usan
    numeros de opcion con ENTER (= confirmar) y 0 (= cancelar/volver).
    En cada fase se puede elegir un territorio propio para ver sus
    acciones, o pasar de turno con la opcion 0.
    """

    def __init__(self, consola: Consola | None = None) -> None:
        self.consola = consola or Consola()
        self._pasar_turno = False

    # ------------------------------------------------------------------
    # Utilidades de presentacion
    # ------------------------------------------------------------------
    def _lista_provincias(self, estado: GameState, jugador: Jugador) -> list[str]:
        """Lineas de texto de las provincias del jugador (para los menus)."""
        lineas = []
        for i in estado.territorios_de(jugador.id):
            prov = estado.provincias[i]
            t = prov.terreno()
            es = "frontera" if estado.vecinos_enemigos_de(i, jugador.id) else "interior"
            lineas.append(
                f"{t.nombre:<24} A={prov.ejercitos:>3} "
                f"P={prov.poblacion:>6.0f} H={prov.felicidad:.2f} "
                f"tau={prov.impuesto:.0%} ({TERRENO_NOMBRES[t.terreno]} - {es})"
            )
        return lineas

    # ------------------------------------------------------------------
    # Fase REFUERZO
    # ------------------------------------------------------------------
    def colocar_refuerzos(self, estado: GameState, jugador: Jugador, cantidad: int) -> None:
        c = self.consola
        self._pasar_turno = False
        c.print(f"\n=== TURNO {estado.turno} - {jugador.nombre.upper()} - FASE REFUERZO ===")
        c.print(mapa_compacto(estado))
        c.print(f"Recibes {cantidad} refuerzos (max(3, territorios/3) + bonus de continentes).")

        pendientes = cantidad
        while pendientes > 0:
            ids = estado.territorios_de(jugador.id)
            menu = MenuTerritorios(
                c,
                list(zip(ids, self._lista_provincias(estado, jugador))),
                titulo=f"Refuerzos pendientes: {pendientes}",
                opcion_cero="Distribuir automaticamente en la frontera",
                prompt="Elige territorio (id): ",
            )
            n = menu.elegir()
            if n == 0:
                frontera = estado.frontera_de(jugador.id) or ids
                cuota = pendientes // len(frontera)
                for i in frontera:
                    estado.provincias[i].ejercitos += cuota
                pendientes -= cuota * len(frontera)
                for k in range(pendientes):
                    estado.provincias[frontera[k % len(frontera)]].ejercitos += 1
                pendientes = 0
                c.print("Refuerzos distribuidos en la frontera.")
                break
            i = n
            cuantos = _pedir_entero(
                c,
                f"Refuerzos en {estado.mapa.territorio(i).nombre} [1..{pendientes}] "
                f"(ENTER = todos): ",
                1,
                pendientes,
                pendientes,
            )
            estado.provincias[i].ejercitos += cuantos
            pendientes -= cuantos
            c.print(
                f"+{cuantos} en {estado.mapa.territorio(i).nombre} "
                f"(A={estado.provincias[i].ejercitos})"
            )
        _pausa(c, "ENTER para pasar a la fase de ataque... ")

    # ------------------------------------------------------------------
    # Fase ATAQUE
    # ------------------------------------------------------------------
    def fase_ataque(self, motor: Motor, estado: GameState, jugador: Jugador) -> None:
        c = self.consola
        c.print(f"\n--- {jugador.nombre} - FASE ATAQUE ---")
        c.print(mapa_compacto(estado))
        while True:
            ids = estado.territorios_de(jugador.id)
            menu = MenuTerritorios(
                c,
                list(zip(ids, self._lista_provincias(estado, jugador))),
                titulo="Elige un territorio para ver sus acciones:",
                opcion_cero="Pasar turno (sin movimiento)",
                prompt="Territorio (id): ",
            )
            n = menu.elegir()
            if n == 0:
                self._pasar_turno = True
                return
            if self._acciones_provincia(motor, estado, jugador, n):
                return  # terminar ataques: sigue la fase de movimiento

    def _acciones_provincia(self, motor: Motor, estado: GameState, jugador: Jugador, i: int) -> bool:
        """Menu de acciones de una provincia. Devuelve True si el jugador
        eligio terminar los ataques (pasar a la fase de movimiento)."""
        c = self.consola
        while True:
            prov = estado.provincias[i]
            c.print(
                f"\n[{i}] {estado.mapa.territorio(i).nombre} | A={prov.ejercitos} | "
                f"P={prov.poblacion:.0f} | H={prov.felicidad:.2f} | "
                f"tau={prov.impuesto:.0%} | F={prov.fortificacion} | I={prov.infraestructura}"
            )
            acciones = ["Atacar a un territorio enemigo adyacente",
                        "Reclutar tropas (cuesta oro y poblacion)",
                        "Construir fortificacion o infraestructura",
                        "Cambiar impuesto de este territorio",
                        "Terminar ataques (pasar a la fase de movimiento)"]
            menu = Menu(c, acciones, opcion_cero="Volver", prompt="Accion: ")
            a = menu.elegir()
            if a == 0:
                return False
            if a == 1:
                self._menu_ataque(motor, estado, jugador, i)
            elif a == 2:
                self._menu_reclutar(estado, jugador, i)
            elif a == 3:
                self._menu_construir(estado, jugador, i)
            elif a == 4:
                self._menu_impuesto(estado, jugador, i)
            elif a == 5:
                return True  # terminar ataques: seguir con el movimiento

    def _menu_ataque(self, motor: Motor, estado: GameState, jugador: Jugador, origen: int) -> None:
        c = self.consola
        if estado.provincias[origen].ejercitos < 2:
            c.print("No puedes atacar: se necesitan al menos 2 ejercitos.")
            _pausa(c)
            return
        enemigos = estado.vecinos_enemigos_de(origen, jugador.id)
        if not enemigos:
            c.print("No hay enemigos adyacentes a esta provincia.")
            _pausa(c)
            return
        opciones = []
        for k in enemigos:
            d = estado.provincias[k]
            dueno = "Neutral" if d.dueno == NEUTRAL else estado.jugadores[d.dueno].nombre
            opciones.append(
                f"{estado.mapa.territorio(k).nombre} ({dueno}, A={d.ejercitos})"
            )
        menu = MenuTerritorios(
            c,
            list(zip(enemigos, opciones)),
            titulo="Objetivos de ataque:",
            opcion_cero="Cancelar",
            prompt="Objetivo (id): ",
        )
        n = menu.elegir()
        if n == 0:
            return
        destino = n
        modos = Menu(
            c,
            ["Batalla total (hasta conquista o agotamiento)",
             "Una sola ronda",
             "Numero fijo de rondas"],
            opcion_cero="Cancelar",
            prompt="Modo: ",
        )
        m = modos.elegir()
        if m == 0:
            return
        if m == 1:
            max_rondas = None
        elif m == 2:
            max_rondas = 1
        else:
            max_rondas = _pedir_entero(c, "Numero de rondas [1..20] (ENTER = 3): ", 1, 20, 3)
        try:
            res = motor.ejecutar_ataque(origen, destino, max_rondas)
        except ValueError as e:
            c.print(f"Error: {e}")
            _pausa(c)
            return
        c.print(
            f"Resultado: {res.rondas} ronda(s), bajas atacante={res.bajas_atacante}, "
            f"defensor={res.bajas_defensor}. "
            + ("TERRITORIO CONQUISTADO" if res.conquistada else "Defensa resiste")
        )
        c.print(
            f"Ahora: {estado.mapa.territorio(origen).nombre} A={estado.provincias[origen].ejercitos} | "
            f"{estado.mapa.territorio(destino).nombre} A={estado.provincias[destino].ejercitos}"
        )
        _pausa(c)

    def _menu_reclutar(self, estado: GameState, jugador: Jugador, i: int) -> None:
        c = self.consola
        prov = estado.provincias[i]
        maximo = min(int(jugador.tesoro // estado.config.c_recl), int(prov.poblacion))
        if maximo < 1:
            c.print("Sin recursos: oro insuficiente o poblacion baja.")
            _pausa(c)
            return
        n = _pedir_entero(
            c,
            f"Soldados a reclutar en {estado.mapa.territorio(i).nombre} "
            f"[1..{maximo}] (ENTER = {maximo}): ",
            1, maximo, maximo,
        )
        costo = n * estado.config.c_recl
        if not _confirmar(c, f"Reclutar {n} soldados por {costo:.1f} oro? (ENTER=si, 0=no): "):
            c.print("Reclutamiento cancelado.")
            return
        ok, msg = economia.reclutar(estado, i, n)
        c.print(msg if ok else f"Error: {msg}")
        _pausa(c)

    def _menu_construir(self, estado: GameState, jugador: Jugador, i: int) -> None:
        c = self.consola
        prov = estado.provincias[i]
        cfg = estado.config
        opciones = []
        costos: list[float | None] = []
        if prov.fortificacion < cfg.nivel_max_fort:
            costo = cfg.c_fort[prov.fortificacion + 1] - cfg.c_fort[prov.fortificacion]
            opciones.append(
                f"Fortificacion (nivel {prov.fortificacion} -> {prov.fortificacion + 1}, "
                f"cuesta {costo:.0f} oro)"
            )
            costos.append(costo)
        else:
            opciones.append("Fortificacion al nivel maximo")
            costos.append(None)
        if prov.infraestructura < cfg.nivel_max_infra:
            costo = cfg.c_infra[prov.infraestructura + 1] - cfg.c_infra[prov.infraestructura]
            opciones.append(
                f"Infraestructura (nivel {prov.infraestructura} -> {prov.infraestructura + 1}, "
                f"cuesta {costo:.0f} oro)"
            )
            costos.append(costo)
        else:
            opciones.append("Infraestructura al nivel maximo")
            costos.append(None)
        menu = Menu(c, opciones, opcion_cero="Cancelar", prompt="Construccion: ")
        n = menu.elegir()
        if n == 0:
            return
        if costos[n - 1] is None:
            c.print("Ya esta al nivel maximo.")
            _pausa(c)
            return
        if not _confirmar(c, "Construir? (ENTER=si, 0=no): "):
            c.print("Construccion cancelada.")
            return
        tipo = "fort" if n == 1 else "infra"
        ok, msg = economia.construir(estado, i, tipo)
        c.print(msg if ok else f"Error: {msg}")
        _pausa(c)

    def _menu_impuesto(self, estado: GameState, jugador: Jugador, i: int) -> None:
        c = self.consola
        prov = estado.provincias[i]
        tasas = [0.10, 0.20, 0.30, 0.40, 0.50]
        menu = Menu(
            c,
            [f"{int(t * 100)}%" for t in tasas],
            titulo=f"Impuesto actual de {estado.mapa.territorio(i).nombre}: "
                   f"{prov.impuesto:.0%}",
            opcion_cero="Cancelar",
            prompt="Nueva tasa: ",
        )
        n = menu.elegir()
        if n == 0:
            return
        ok, msg = economia.fijar_impuesto(estado, i, tasas[n - 1])
        c.print(msg if ok else f"Error: {msg}")
        _pausa(c)

    # ------------------------------------------------------------------
    # Fase MOVIMIENTO (un unico movimiento)
    # ------------------------------------------------------------------
    def fase_movimiento(self, motor: Motor, estado: GameState, jugador: Jugador) -> None:
        c = self.consola
        if self._pasar_turno:
            # El jugador eligio pasar turno en la fase de ataque
            return
        c.print(f"\n--- {jugador.nombre} - FASE MOVIMIENTO (unico, opcional) ---")
        c.print(mapa_compacto(estado))
        ids = estado.territorios_de(jugador.id)
        lineas = self._lista_provincias(estado, jugador)
        candidatos = [
            (ids[k], lineas[k])
            for k in range(len(ids))
            if estado.provincias[ids[k]].ejercitos >= 2
        ]
        if not candidatos:
            c.print("Ninguna provincia tiene tropas suficientes para mover.")
            _pausa(c)
            return
        menu = MenuTerritorios(
            c,
            candidatos,
            titulo="Origen del movimiento (provincias con tropas disponibles):",
            opcion_cero="Pasar sin mover",
            prompt="Origen (id): ",
        )
        n = menu.elegir()
        if n == 0:
            return
        origen = n
        destinos = [
            k for k in estado.mapa.vecinos(origen)
            if estado.provincias[k].dueno == jugador.id
        ]
        if not destinos:
            c.print("Esa provincia no tiene provincias propias adyacentes.")
            _pausa(c)
            return
        opciones_d = [
            (k, f"{estado.mapa.territorio(k).nombre} (A={estado.provincias[k].ejercitos})")
            for k in destinos
        ]
        menu_d = MenuTerritorios(c, opciones_d, opcion_cero="Cancelar", prompt="Destino (id): ")
        m = menu_d.elegir()
        if m == 0:
            return
        destino = m
        maximo = estado.provincias[origen].ejercitos - 1
        n_tropas = _pedir_entero(
            c,
            f"Cantidad de tropas [1..{maximo}] (ENTER = todas): ",
            1, maximo, maximo,
        )
        if not _confirmar(
            c,
            f"Mover {n_tropas} tropas de {estado.mapa.territorio(origen).nombre} a "
            f"{estado.mapa.territorio(destino).nombre}? (ENTER=si, 0=no): ",
        ):
            c.print("Movimiento cancelado.")
            return
        try:
            motor.ejecutar_movimiento(origen, destino, n_tropas)
            c.print(f"Movidas {n_tropas} tropas.")
        except ValueError as e:
            c.print(f"Error: {e}")
        _pausa(c)




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
    """Menu de inicio: elige escenario, imperio, modo, turnos y semilla."""
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
        c.print(f"  {i}) {esc.nombre}")
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

    # --- Eleccion del imperio con el que se juega ---
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

    # --- Eleccion de modo ---
    c.print("\nModo de juego:")
    c.print("  1) Partida interactiva (tu controlas el imperio elegido)")
    c.print("  2) Demo automatica (todos los imperios con IA)")
    modo = _leer(c, "\nElige modo [1-2] (1): ", "1")
    demo = modo.strip() == "2"

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
