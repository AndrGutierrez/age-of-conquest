"""Modulo de estilos, colores ANSI y utilidades de consola para Age of Conquest.

Proporciona soporte de colores multiplataforma con auto-deteccion de colorama
(si esta disponible) o secuencias de escape ANSI nativas, garantizando maxima
compatibilidad en terminales Windows (cp1252/UTF-8), Linux y macOS.
"""

from __future__ import annotations

import os
import sys

# Configurar encoding seguro en Windows para evitar UnicodeEncodeError en cp1252
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Intentar inicializar colorama si esta instalado
_COLORAMA_DISPONIBLE = False
try:
    import colorama
    colorama.init(autoreset=True)
    _COLORAMA_DISPONIBLE = True
except ImportError:
    pass

# Codigos ANSI estandar
RESET = "\033[0m"
NEGRITA = "\033[1m"
DIM = "\033[2m"
SUBRAYADO = "\033[4m"

# Colores de texto (Foreground)
NEGRO = "\033[30m"
ROJO = "\033[31m"
VERDE = "\033[32m"
AMARILLO = "\033[33m"
AZUL = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
BLANCO = "\033[37m"

# Colores brillantes
ROJO_B = "\033[91m"
VERDE_B = "\033[92m"
AMARILLO_B = "\033[93m"
AZUL_B = "\033[94m"
MAGENTA_B = "\033[95m"
CYAN_B = "\033[96m"
BLANCO_B = "\033[97m"
GRIS = "\033[90m"
NARANJA = "\033[38;5;208m"
NARANJA_B = "\033[38;5;214m"

# Fondos (Background)
BG_ROJO = "\033[41m"
BG_VERDE = "\033[42m"
BG_AMARILLO = "\033[43m"
BG_AZUL = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"


def colorear(texto: str, codigo: str) -> str:
    """Envuelve el texto en el codigo de color y lo reinicia."""
    return f"{codigo}{texto}{RESET}"


def c_rojo(texto: str) -> str:
    return colorear(texto, ROJO_B)


def c_verde(texto: str) -> str:
    return colorear(texto, VERDE_B)


def c_amarillo(texto: str) -> str:
    return colorear(texto, AMARILLO_B)


def c_naranja(texto: str) -> str:
    return colorear(texto, NARANJA_B)


def c_azul(texto: str) -> str:
    return colorear(texto, AZUL_B)


def c_magenta(texto: str) -> str:
    return colorear(texto, MAGENTA_B)


def c_cyan(texto: str) -> str:
    return colorear(texto, CYAN_B)


def c_blanco(texto: str) -> str:
    return colorear(texto, BLANCO_B)


def c_gris(texto: str) -> str:
    return colorear(texto, GRIS)


def c_negrita(texto: str) -> str:
    return colorear(texto, NEGRITA)


# ---------------------------------------------------------------------------
# Helpers semanticos para la simulacion
# ---------------------------------------------------------------------------

def estilo_jugador(nombre: str, es_humano: bool, es_neutral: bool = False) -> str:
    """Formatea el nombre del imperio segun su rol."""
    if es_neutral:
        return colorear(nombre, GRIS)
    if es_humano:
        return colorear(nombre, f"{NEGRITA}{CYAN_B}")
    return colorear(nombre, f"{NEGRITA}{BLANCO_B}")


def estilo_felicidad(h: float) -> str:
    """Colorea el porcentaje de felicidad segun su nivel de estabilidad."""
    txt = f"{h * 100:>5.1f}%"
    if h >= 0.60:
        return c_verde(txt)
    elif h >= 0.25:
        return c_amarillo(txt)
    else:
        return colorear(f"{txt} [! RIESGO REBELION]", f"{NEGRITA}{ROJO_B}")


def estilo_tesoro(monto: float) -> str:
    """Formatea y colorea la tesoreria imperial."""
    txt = f"{monto:,.1f} oro"
    if monto > 0:
        return c_verde(txt)
    elif monto == 0:
        return c_amarillo(txt)
    else:
        return colorear(f"{txt} [! BANCARROTA]", f"{NEGRITA}{ROJO_B}")


def estilo_alerta_humano(texto: str) -> str:
    """Crea una caja destacada para eventos que afectan directamente al jugador."""
    borde = "=" * (len(texto) + 4)
    return (
        f"\n{MAGENTA_B}+{borde}+{RESET}\n"
        f"{MAGENTA_B}|  {NEGRITA}{texto}{RESET}{MAGENTA_B}  |{RESET}\n"
        f"{MAGENTA_B}+{borde}+{RESET}\n"
    )


def limpiar_consola() -> None:
    """Limpia la pantalla de la terminal de forma compatible en Windows y Unix."""
    # En entornos de testing o tuberias no interactivas, no limpiar
    if not sys.stdout.isatty():
        return
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")
