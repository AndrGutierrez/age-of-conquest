"""Punto de entrada del simulador Age of Conquest.

Uso:
    python main.py                 # partida interactiva: 1 humano + 3 IA
    python main.py --demo 5        # demo automatica de 5 turnos (solo IA)
    python main.py --seed 42       # semilla fija (reproducibilidad)
    python main.py --turnos 10     # limite de turnos de la partida
"""

from __future__ import annotations

import argparse

from age_of_conquest.cli import partida_demo, partida_interactiva


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor de simulacion Age of Conquest (SIMUSIST)"
    )
    parser.add_argument(
        "--demo",
        type=int,
        metavar="N",
        default=None,
        help="ejecuta una demo automatica de N turnos con solo IA",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="semilla del generador aleatorio (reproducibilidad)",
    )
    parser.add_argument(
        "--turnos",
        type=int,
        default=None,
        help="limite de turnos globales de la partida",
    )
    args = parser.parse_args()

    if args.demo is not None:
        partida_demo(seed=args.seed, max_turnos=args.demo)
    else:
        partida_interactiva(seed=args.seed, max_turnos=args.turnos)


if __name__ == "__main__":
    main()
