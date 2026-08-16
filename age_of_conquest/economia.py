"""Subsistema economico, demografico y de estabilidad (Secciones 2.1-2.3 y 2.8).

Contiene:
    - Recaudacion fiscal con puerta de felicidad Omega(H).
    - Gastos de mantenimiento militar y de infraestructura.
    - Liquidacion del tesoro al final del turno (2.1), con regla de
      bancarrota: desercion proporcional a la deuda.
    - Crecimiento poblacional logistico (2.2) con dano colateral civil.
    - Actualizacion de felicidad con clip [0,1] (2.3).
    - Riesgo de rebelion y muestreo Monte Carlo (2.8).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import CONFIG, Config
from .estado import NEUTRAL, GameState, Provincia
from .mapa import CONTINENTE_BONUS_ORO


def puerta_fiscal(h: float, config: Config | None = None) -> float:
    """Omega(H): eficiencia recaudatoria (Seccion 2.1.1).

    Vale 1 si H >= H_min; decae linealmente si 0 < H < H_min; 0 si H = 0.
    """
    cfg = config or CONFIG
    if h >= cfg.h_min:
        return 1.0
    if h <= 0.0:
        return 0.0
    return h / cfg.h_min


def lambda_crecimiento(h: float, config: Config | None = None) -> float:
    """lambda(H): multiplicador de crecimiento poblacional (Seccion 2.2).

    Identico en forma a la puerta fiscal.
    """
    return puerta_fiscal(h, config)


# ---------------------------------------------------------------------------
# 2.1 Dinamica economica
# ---------------------------------------------------------------------------

def recaudacion_provincia(prov: Provincia, config: Config | None = None) -> float:
    """R_tax(i) = beta * P * tau * Omega(H) * (1 + eta_I * I)."""
    cfg = config or CONFIG
    return (
        cfg.beta
        * prov.poblacion
        * prov.impuesto
        * puerta_fiscal(prov.felicidad, cfg)
        * (1.0 + cfg.eta_i * prov.infraestructura)
    )


def recaudacion_total(estado: GameState, p: int) -> float:
    """R_tax(p) = suma de la recaudacion de las provincias de p."""
    return sum(
        recaudacion_provincia(estado.provincias[i], estado.config)
        for i in estado.territorios_de(p)
    )


def mantenimiento_militar(estado: GameState, p: int) -> float:
    """G_mil(p) = m0 * suma de ejercitos del jugador p (Seccion 2.1.2)."""
    return estado.config.m0 * estado.total_ejercitos(p)


def mantenimiento_infra(estado: GameState, p: int) -> float:
    """G_infra(p) = suma(m_fort*F + m_infra*I) (Seccion 2.1.3)."""
    cfg = estado.config
    return sum(
        cfg.m_fort * estado.provincias[i].fortificacion
        + cfg.m_infra * estado.provincias[i].infraestructura
        for i in estado.territorios_de(p)
    )


def bonus_continentes_oro(estado: GameState, p: int) -> float:
    """B_cont(p) en oro por control total de continentes (Seccion 2.1.4)."""
    return sum(CONTINENTE_BONUS_ORO.get(c, 0.0) for c in estado.dueño_continentes(p))


def costo_reclutamiento(estado: GameState, p: int) -> float:
    """C_recl(p) = c_recl * soldados reclutados este turno (Seccion 2.1.5)."""
    cfg = estado.config
    return cfg.c_recl * sum(
        estado.provincias[i].reclutas_turno for i in estado.territorios_de(p)
    )


@dataclass
class ResultadoTesoro:
    """Desglose del balance economico de un jugador al cerrar su turno."""

    ingresos: float = 0.0
    gasto_militar: float = 0.0
    gasto_infra: float = 0.0
    bonus_oro: float = 0.0
    costo_reclutas: float = 0.0
    desertados: int = 0
    tesoro_final: float = 0.0


def liquidar_tesoro(estado: GameState, p: int) -> ResultadoTesoro:
    """Actualiza la tesoreria del jugador p (ecuacion 2.1) y resuelve la
    bancarrota si queda negativa.

    Regla de bancarrota (decision de diseno, caso borde del informe):
    si E < 0 tras el balance, se disuelven tropas (cada una ahorra m0 de
    mantenimiento) hasta cubrir la deuda; la desercion se produce primero
    en las provincias con mas efectivos. Si aun asi la deuda persiste, el
    jugador queda en bancarrota (penalizacion de felicidad en 2.3) y el
    tesoro se conserva negativo hasta el proximo turno.
    """
    cfg = estado.config
    res = ResultadoTesoro()
    res.ingresos = recaudacion_total(estado, p)
    res.gasto_militar = mantenimiento_militar(estado, p)
    res.gasto_infra = mantenimiento_infra(estado, p)
    res.bonus_oro = bonus_continentes_oro(estado, p)
    res.costo_reclutas = costo_reclutamiento(estado, p)

    j = estado.jugadores[p]
    j.tesoro += (
        res.ingresos
        - res.gasto_militar
        - res.gasto_infra
        + res.bonus_oro
        - res.costo_reclutas
    )

    # Bancarrota: desercion proporcional a la deuda
    if j.tesoro < 0 and estado.total_ejercitos(p) > 0:
        deuda = -j.tesoro
        necesarios = int(-(-deuda // cfg.m0))  # ceil(deuda / m0)
        provincias = sorted(
            estado.territorios_de(p),
            key=lambda i: -estado.provincias[i].ejercitos,
        )
        for i in provincias:
            prov = estado.provincias[i]
            # No se disuelve la ultima tropa: la provincia siempre
            # conserva 1 ejercito (garantiza defensa minima).
            disolvibles = min(prov.ejercitos - 1, necesarios)
            if disolvibles <= 0:
                continue
            prov.ejercitos -= disolvibles
            res.desertados += disolvibles
            j.tesoro += disolvibles * cfg.m0
            necesarios -= disolvibles
            if necesarios <= 0:
                break

    j.bancarrota = j.tesoro < 0
    res.tesoro_final = j.tesoro
    return res


# ---------------------------------------------------------------------------
# Acciones economicas voluntarias del jugador
# ---------------------------------------------------------------------------

def reclutar(estado: GameState, i: int, n: int) -> tuple[bool, str]:
    """Compra n soldados en la provincia i (Seccion 2.1.5 y 2.2).

    Costo: c_recl de oro por soldado; ademas cada soldado se resta de la
    poblacion civil (delta_rec). No se permite si el oro o la poblacion
    son insuficientes.
    """
    cfg = estado.config
    prov = estado.provincias[i]
    p = prov.dueno
    if p == NEUTRAL:
        return False, "La provincia no tiene dueno"
    j = estado.jugadores[p]
    if n <= 0:
        return False, "Cantidad de reclutas invalida"
    costo = cfg.c_recl * n
    if j.tesoro < costo:
        return False, f"Oro insuficiente (cuesta {costo:.1f}, hay {j.tesoro:.1f})"
    if prov.poblacion < n:
        return False, f"Poblacion insuficiente ({prov.poblacion:.0f} hab.)"
    j.tesoro -= costo
    prov.poblacion -= n
    prov.ejercitos += n
    prov.reclutas_turno += n  # contabilizado en C_recl y en el balance
    return True, f"Reclutados {n} soldados en {estado.mapa.territorio(i).nombre}"


def construir(estado: GameState, i: int, tipo: str) -> tuple[bool, str]:
    """Mejora un nivel la fortificacion o la infraestructura de la provincia.

    Los costos son incrementales: c[nivel+1] - c[nivel] (la tabla 1.5.5 da
    costos acumulados).
    """
    cfg = estado.config
    prov = estado.provincias[i]
    p = prov.dueno
    if p == NEUTRAL:
        return False, "La provincia no tiene dueno"
    j = estado.jugadores[p]

    if tipo == "fort":
        nivel = prov.fortificacion
        tabla, maximo = cfg.c_fort, cfg.nivel_max_fort
        nombre = "fortificacion"
    elif tipo == "infra":
        nivel = prov.infraestructura
        tabla, maximo = cfg.c_infra, cfg.nivel_max_infra
        nombre = "infraestructura"
    else:
        return False, f"Tipo de construccion desconocido: {tipo}"

    if nivel >= maximo:
        return False, f"{nombre.capitalize()} al nivel maximo ({maximo})"
    costo = tabla[nivel + 1] - tabla[nivel]
    if j.tesoro < costo:
        return False, f"Oro insuficiente (cuesta {costo:.1f}, hay {j.tesoro:.1f})"
    j.tesoro -= costo
    if tipo == "fort":
        prov.fortificacion += 1
    else:
        prov.infraestructura += 1
    return True, f"{nombre.capitalize()} de {estado.mapa.territorio(i).nombre} a nivel {nivel + 1}"


def fijar_impuesto(estado: GameState, i: int, tau: float) -> tuple[bool, str]:
    """Asigna la tasa impositiva tau(i) de una provincia (limite tau_max)."""
    cfg = estado.config
    prov = estado.provincias[i]
    if prov.dueno == NEUTRAL:
        return False, "La provincia no tiene dueno"
    if not (0.0 <= tau <= cfg.tau_max):
        return False, f"Tasa fuera de rango [0, {cfg.tau_max}]"
    prov.impuesto = tau
    return True, f"Impuesto de {estado.mapa.territorio(i).nombre} fijado en {tau:.0%}"


# ---------------------------------------------------------------------------
# 2.2 Dinamica poblacional
# ---------------------------------------------------------------------------

def capacidad_carga(prov: Provincia, config: Config | None = None) -> float:
    """K * sigma_cap: capacidad de carga efectiva de la provincia.

    sigma_cap = sigma_base(terreno) * (1 + eta_cap * I).
    """
    cfg = config or CONFIG
    sigma_base = cfg.sigma_cap_base[prov.terreno().terreno]
    return cfg.k_base * sigma_base * (1.0 + cfg.eta_cap * prov.infraestructura)


def suficiencia_alimentaria(prov: Provincia, config: Config | None = None) -> float:
    """S_alim = P / (K * sigma_cap) (Seccion 2.9)."""
    return prov.poblacion / capacidad_carga(prov, config)


def crecimiento_poblacional(estado: GameState) -> None:
    """Aplica la ecuacion logistica (2.2) a todas las provincias.

    P' = P + g*P*(1 - P/(K*sigma_cap))*lambda(H) - delta_rec - delta_comb
    Se ejecuta una vez por ronda global (turno completo).
    """
    cfg = estado.config
    for prov in estado.provincias.values():
        s = suficiencia_alimentaria(prov, cfg)
        crecimiento = cfg.g * prov.poblacion * (1.0 - s) * lambda_crecimiento(prov.felicidad, cfg)
        prov.poblacion = max(
            0.0, prov.poblacion + crecimiento - prov.reclutas_turno - prov.bajas_combate
        )


def aplicar_dano_colateral(prov: Provincia, bajas_militares: int, config: Config | None = None) -> int:
    """delta_comb = alpha_col * (b_atk + b_def) de poblacion civil (2.2)."""
    cfg = config or CONFIG
    dano = round(cfg.alpha_col * bajas_militares)
    prov.bajas_combate += dano
    prov.hubo_batalla = True
    return dano


# ---------------------------------------------------------------------------
# 2.3 Dinamica de felicidad
# ---------------------------------------------------------------------------

def variacion_felicidad(prov: Provincia, estado: GameState, p: int) -> float:
    """Delta H de una provincia (Seccion 2.3).

    Delta H = -delta_tau*tau - delta_w*W_p + epsilon_vic*V_p - delta_oc*O_new
    La penalizacion por bancarrota es una decision de diseno adicional.
    """
    cfg = estado.config
    j = estado.jugadores[p]
    dh = -cfg.delta_tau * prov.impuesto
    if j.en_guerra:
        dh -= cfg.delta_w
    if j.victorias_turno:
        dh += cfg.epsilon_vic
    if prov.ocupada_reciente:
        dh -= cfg.delta_oc
    if j.bancarrota:
        dh -= cfg.delta_banc
    return dh


def actualizar_felicidad(estado: GameState) -> None:
    """Actualiza H de todas las provincias con clip en [0, 1] (2.3)."""
    for i, prov in estado.provincias.items():
        p = prov.dueno
        if p == NEUTRAL:
            continue
        prov.felicidad = max(0.0, min(1.0, prov.felicidad + variacion_felicidad(prov, estado, p)))


# ---------------------------------------------------------------------------
# 2.8 Riesgo de rebelion
# ---------------------------------------------------------------------------

def probabilidad_rebelion(h: float, config: Config | None = None) -> float:
    """pi(H): riesgo de rebelion de una provincia (Seccion 2.8).

    pi = kappa / H^gamma para 0 < H < H_min; pi = 1 si H = 0; 0 si H >= H_min.
    El valor se recorta a [0, 1] por seguridad numerica.
    """
    cfg = config or CONFIG
    if h >= cfg.h_min:
        return 0.0
    if h <= 0.0:
        return 1.0  # caso borde: rebelion inevitable (Seccion 2.8)
    pi = cfg.kappa / (h ** cfg.gamma)
    return max(0.0, min(1.0, pi))


def comprobar_rebeliones(estado: GameState, rng: random.Random) -> list[int]:
    """Muestreo Monte Carlo: cada provincia inestable se rebela si u <= pi.

    Una provincia rebelde se convierte en neutral: pierde a su dueno y queda
    guarnecida por milicias locales (decision de diseno; el documento define
    la rebelion como "territorio neutral o faccion independiente").
    """
    cfg = estado.config
    rebeldes = []
    for i, prov in estado.provincias.items():
        if prov.dueno == NEUTRAL:
            continue
        pi = probabilidad_rebelion(prov.felicidad, cfg)
        if pi > 0.0 and rng.random() <= pi:
            prov.dueno = NEUTRAL
            prov.ejercitos = cfg.guarnicion_neutral
            prov.impuesto = 0.0
            prov.ocupada_reciente = False
            rebeldes.append(i)
    return rebeldes
