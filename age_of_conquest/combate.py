"""Resolucion estocastica de combate con dados (Seccion 2.4 del documento).

Modelo de dados del Risk clasico:
    1. El atacante lanza n_a = min(d_atk_max, A_i - 1) dados.
    2. El defensor lanza n_d = min(d_def_max, A_k) dados.
    3. Ambos vectores se ordenan descendentemente y se comparan por pares.
    4. En cada par: empate o dado menor -> baja del atacante; dado mayor
       del atacante -> baja del defensor.
    5. Si el defensor queda en 0, hay conquista y el atacante transfiere
       m_oc = max(n_a, 1) tropas.

El multiplicador de terreno theta_T y la fortificacion F (definidos en el
documento pero sin ecuacion explicita en 2.4) se aplican escalando el valor
de cada dado del defensor:
        d_def' = min(D, round(d_def * theta_T(sigma) * (1 + 0.15 * F)))
Esta es una decision de diseno documentada en el README.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field

from .config import CONFIG, Config
from .estado import Provincia


@dataclass
class ResultadoRonda:
    """Resultado de una ronda individual de combate."""

    dados_atacante: list[int] = field(default_factory=list)   # ordenados desc
    dados_defensor: list[int] = field(default_factory=list)   # ordenados desc
    bajas_atacante: int = 0
    bajas_defensor: int = 0


@dataclass
class ResultadoBatalla:
    """Resultado completo de una batalla (una o varias rondas)."""

    conquistada: bool = False
    bajas_atacante: int = 0
    bajas_defensor: int = 0
    rondas: int = 0
    ejercitos_origen: int = 0      # tropas que quedan en la provincia origen
    ejercitos_destino: int = 0     # tropas en la provincia destino al final
    transferidas: int = 0          # m_oc: tropas movidas al territorio conquistado


def ataque_viable(a_atacante: int) -> bool:
    """Condicion de ataque viable (Seccion 2.4.1): A_i >= 2."""
    return a_atacante >= 2


def numero_dados(a_atacante: int, a_defensor: int, config: Config | None = None) -> tuple[int, int]:
    """Devuelve (n_atk, n_def) segun la Seccion 2.4.1.

    n_atk = min(d_atk_max, A_i - 1)
    n_def = min(d_def_max, A_k)
    """
    cfg = config or CONFIG
    if a_defensor < 0 or a_atacante < 0:
        raise ValueError("Ejercitos negativos")
    n_atk = min(cfg.d_atk_max, max(0, a_atacante - 1))
    n_def = min(cfg.d_def_max, max(0, a_defensor))
    return n_atk, n_def


def _multiplicador_defensor(provincia: Provincia, config: Config) -> float:
    """theta_T(sigma) * (1 + fort_factor * F): escala del dado defensor."""
    theta = config.theta_terreno[provincia.terreno().terreno]
    fort = 1.0 + config.fort_factor_por_nivel * provincia.fortificacion
    return theta * fort


def resolver_ronda(
    a_atacante: int,
    a_defensor: int,
    provincia_defensora: Provincia,
    rng: random.Random,
    config: Config | None = None,
) -> ResultadoRonda:
    """Resuelve una ronda de combate (Secciones 2.4.2 y 2.4.3).

    El atacante usa como maximo d_atk_max dados; el defensor d_def_max.
    Se ordenan descendentemente y se comparan los min(n_a, n_d) pares.
    """
    cfg = config or CONFIG
    n_atk, n_def = numero_dados(a_atacante, a_defensor, cfg)
    if n_atk == 0:
        raise ValueError("No se puede atacar: el atacante no tiene tropas")

    # 2.4.2: generacion de variables aleatorias uniformes discretas {1..D}
    dados_a = sorted((rng.randint(1, cfg.d_caras) for _ in range(n_atk)), reverse=True)
    dados_d = sorted((rng.randint(1, cfg.d_caras) for _ in range(n_def)), reverse=True)

    # Aplicacion del multiplicador defensivo (terreno + fortificacion)
    mult = _multiplicador_defensor(provincia_defensora, cfg)
    dados_d_efectivos = [
        min(cfg.d_caras, round(d * mult)) for d in dados_d
    ]
    # Reordenar tras la escala para mantener la propiedad desc
    dados_d_efectivos.sort(reverse=True)

    # 2.4.3: comparacion por pares; empate favorece al defensor
    bajas_a = bajas_d = 0
    for da, dd in zip(dados_a, dados_d_efectivos):
        if da > dd:
            bajas_d += 1
        else:
            bajas_a += 1

    return ResultadoRonda(
        dados_atacante=dados_a,
        dados_defensor=dados_d_efectivos,
        bajas_atacante=bajas_a,
        bajas_defensor=bajas_d,
    )


def batalla(
    a_atacante: int,
    a_defensor: int,
    provincia_defensora: Provincia,
    rng: random.Random,
    config: Config | None = None,
    max_rondas: int | None = None,
) -> ResultadoBatalla:
    """Ejecuta una batalla completa hasta conquista o agotamiento.

    Se repiten rondas hasta que el defensor queda sin tropas (conquista) o
    el atacante queda con 1 solo ejercito (ya no puede atacar). La conquista
    implica transferir m_oc = max(n_atk, 1) tropas al territorio tomado
    (Seccion 2.4.5).

    Parametros:
        a_atacante: tropas iniciales en la provincia origen.
        a_defensor: tropas iniciales en la provincia destino.
        provincia_defensora: provincia atacada (por su terreno/fortificacion).
        rng: generador de numeros aleatorios (inyectado para tests).
        max_rondas: limite opcional de rondas (None = hasta resolucion).
    """
    cfg = config or CONFIG
    res = ResultadoBatalla(ejercitos_origen=a_atacante, ejercitos_destino=a_defensor)

    atk = a_atacante
    defe = a_defensor
    n_atk_ultima = 0

    while True:
        n_atk, _ = numero_dados(atk, defe, cfg)
        if n_atk == 0:
            # El atacante quedo con 1 solo ejercito: no puede continuar
            break
        ronda = resolver_ronda(atk, defe, provincia_defensora, rng, cfg)
        res.bajas_atacante += ronda.bajas_atacante
        res.bajas_defensor += ronda.bajas_defensor
        res.rondas += 1
        atk -= ronda.bajas_atacante
        defe -= ronda.bajas_defensor
        n_atk_ultima = n_atk

        if defe <= 0:
            # 2.4.5: conquista y transferencia minima obligatoria
            res.conquistada = True
            m_oc = max(n_atk_ultima, 1)
            m_oc = min(m_oc, atk - 1)  # el origen siempre retiene >= 1
            res.transferidas = m_oc
            atk -= m_oc
            defe = m_oc
            break
        if atk <= 1:
            break  # sin tropas suficientes para una nueva ronda
        if max_rondas is not None and res.rondas >= max_rondas:
            break

    res.ejercitos_origen = atk
    res.ejercitos_destino = defe
    return res


# ---------------------------------------------------------------------------
# Analisis probabilistico por enumeracion exhaustiva (Seccion 2.4.6)
# ---------------------------------------------------------------------------

def esperanza_bajas_teorica(
    n_atk: int, n_def: int, config: Config | None = None
) -> tuple[float, float]:
    """E[b_atk] y E[b_def] por enumeracion de los D^(n_atk + n_def) resultados.

    Cada combinacion de dados es equiprobable; se suman las bajas de todas
    las combinaciones y se dividen por el total. Sirve para validar la tabla
    de la Seccion 2.4.6 y calibrar el simulador.
    """
    cfg = config or CONFIG
    caras = range(1, cfg.d_caras + 1)
    total = 0.0
    bajas_a = 0.0
    bajas_d = 0.0
    for dados in itertools.product(caras, repeat=n_atk + n_def):
        da = sorted(dados[:n_atk], reverse=True)
        dd = sorted(dados[n_atk:], reverse=True)
        for x, y in zip(da, dd):
            if x > y:
                bajas_d += 1.0
            else:
                bajas_a += 1.0
        total += 1.0
    return bajas_a / total, bajas_d / total


def probabilidad_dado_atacante(config: Config | None = None) -> float:
    """P(X_a > X_d) para un dado contra un dado (Seccion 2.4.6).

    Valor teorico: (D - 1) / (2D); para D = 6 es 5/12 ~= 0.4167.
    """
    cfg = config or CONFIG
    return (cfg.d_caras - 1) / (2 * cfg.d_caras)
