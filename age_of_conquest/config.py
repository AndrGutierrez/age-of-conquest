"""Parametros fijos del modelo (Seccion 1.5 del documento).

Todos los escalares globales inmutables durante la simulacion. Son
configurables mediante la dataclass :class:`Config`, pero los valores por
defecto son los sugeridos por el documento de formalizacion.

Nota de calibracion:
    La tabla 1.5.4 indica kappa = 0.10, pero los ejemplos numericos de la
    seccion 2.8 usan kappa = 0.01 (ej.: H = 0.2 -> pi = 0.01 / 0.2^2 = 0.25).
    Se adopta kappa = 0.01 por coherencia con los ejemplos; el valor queda
    configurable para el analisis de sensibilidad del informe.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constantes geograficas (Seccion 1.2.1)
# ---------------------------------------------------------------------------

#: sigma(i): tipo de terreno de una provincia.
#: {0: Llano, 1: Bosque, 2: Montana, 3: Desierto}
TERRENO_LLANO = 0
TERRENO_BOSQUE = 1
TERRENO_MONTANA = 2
TERRENO_DESIERTO = 3

TERRENO_NOMBRES = {
    TERRENO_LLANO: "Llano",
    TERRENO_BOSQUE: "Bosque",
    TERRENO_MONTANA: "Montana",
    TERRENO_DESIERTO: "Desierto",
}


@dataclass
class Config:
    """Contenedor de todos los parametros del modelo (Seccion 1.5)."""

    # ------------------------------------------------------------------
    # 1.5.1 Parametros de combate
    # ------------------------------------------------------------------
    d_caras: int = 6                 # D: caras del dado
    d_atk_max: int = 3               # d_atk_max: maximo de dados del atacante
    d_def_max: int = 2               # d_def_max: maximo de dados del defensor

    # theta_T: multiplicador defensivo por tipo de terreno (indice = terreno)
    theta_terreno: tuple = (1.0, 1.3, 1.5, 0.8)  # Llano, Bosque, Montana, Desierto

    #: bonificacion defensiva por nivel de fortificacion F (valor de diseno:
    #: el documento define F y su costo pero no su efecto en combate).
    fort_factor_por_nivel: float = 0.15

    #: dano colateral civil: fraccion de bajas militares que se pierde de
    #: poblacion en la provincia escenario de la batalla (Seccion 2.2).
    alpha_col: float = 0.10

    # ------------------------------------------------------------------
    # 1.5.2 Parametros de refuerzos y logistica
    # ------------------------------------------------------------------
    r_min: int = 3                   # refuerzo base minimo garantizado
    rho: int = 3                     # divisor: r = max(r_min, floor(T / rho))

    # ------------------------------------------------------------------
    # 1.5.3 Parametros economicos y demograficos
    # ------------------------------------------------------------------
    g: float = 0.02                  # tasa intrinseca de crecimiento poblacional
    k_base: float = 1000.0           # K: capacidad de carga poblacional base
    beta: float = 0.5                # productividad fiscal base por habitante
    tau_max: float = 0.50            # tasa impositiva maxima permitida
    m0: float = 0.05                 # mantenimiento unitario por soldado/turno
    c_recl: float = 2.0              # costo de reclutamiento por soldado

    #: sensibilidad de la recaudacion a la infraestructura: factor
    #: (1 + eta_I * I). Valor de diseno (no tabulado en el documento).
    eta_i: float = 0.10

    #: sensibilidad de la capacidad de carga a la infraestructura:
    #: sigma_cap = sigma_base * (1 + eta_cap * I). Valor de diseno.
    eta_cap: float = 0.15

    #: sigma_base: capacidad de carga por tipo de terreno (Seccion 2.2).
    sigma_cap_base: tuple = (1.0, 0.7, 0.4, 0.3)

    # ------------------------------------------------------------------
    # 1.5.4 Parametros de felicidad y estabilidad
    # ------------------------------------------------------------------
    h_min: float = 0.25              # umbral critico de felicidad
    delta_tau: float = 0.40          # penalizacion por tasa impositiva
    delta_w: float = 0.15            # penalizacion por estado de guerra
    delta_oc: float = 0.25           # penalizacion por ocupacion reciente
    epsilon_vic: float = 0.10        # ganancia de felicidad por victoria militar
    kappa: float = 0.01              # escala del riesgo de rebelion (ver nota)
    gamma: float = 2.0               # exponente del riesgo de rebelion
    delta_banc: float = 0.10         # penalizacion de felicidad por bancarrota

    # ------------------------------------------------------------------
    # 1.5.5 Parametros de infraestructura
    # ------------------------------------------------------------------
    #: costo acumulado de construir/mejorar fortificacion hasta el nivel n
    c_fort: tuple = (0.0, 50.0, 120.0, 250.0)
    #: costo acumulado de construir/mejorar infraestructura hasta el nivel n
    c_infra: tuple = (0.0, 60.0, 140.0, 300.0)
    m_fort: float = 5.0              # mantenimiento por nivel de fortificacion
    m_infra: float = 3.0             # mantenimiento por nivel de infraestructura

    # ------------------------------------------------------------------
    # Estado inicial de la partida
    # ------------------------------------------------------------------
    oro_inicial: float = 60.0        # tesoreria inicial de cada jugador
    poblacion_inicial: float = 500.0  # poblacion inicial de cada provincia
    felicidad_inicial: float = 0.80  # felicidad inicial de cada provincia
    ejercitos_iniciales: int = 3     # tropas por provincia al repartir el mapa
    guarnicion_neutral: int = 2      # milicias de una provincia rebelde/neutral
    costo_bonus_continente: float = 5.0  # oro por turno por continente completo

    #: margen de tropas que una IA deja como guarnicion minima al atacar
    guarnicion_min_ia: int = 2

    #: niveles maximos de construccion (len(c_fort) - 1 y len(c_infra) - 1)
    @property
    def nivel_max_fort(self) -> int:
        return len(self.c_fort) - 1

    @property
    def nivel_max_infra(self) -> int:
        return len(self.c_infra) - 1


#: Configuracion global usada por el motor (puede reemplazarse en tests).
CONFIG = Config()
