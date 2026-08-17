"""Punto de entrada del simulador Age of Conquest.

Uso:
    python main.py                        # partida interactiva (Ascenso de Roma)
    python main.py --escenario caida      # otro escenario historico
    python main.py --demo 5               # demo automatica de 5 turnos (solo IA)
    python main.py --seed 42              # semilla fija (reproducibilidad)
    python main.py --turnos 10            # limite de turnos de la partida

Escenarios disponibles:
    roma       Ascenso de Roma (264 a.C.)
    caida      Caida de Roma (452 d.C.)
    medieval   Edad Media (1066 d.C.)
"""

from __future__ import annotations

import argparse

from age_of_conquest.cli import partida_demo, partida_interactiva
from age_of_conquest.escenarios import ESCENARIOS


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor de simulacion Age of Conquest (SIMUSIST)"
    )
    parser.add_argument(
        "--escenario",
        choices=sorted(ESCENARIOS),
        default="roma",
        help="escenario historico de la partida (defecto: roma)",
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
        partida_demo(seed=args.seed, max_turnos=args.demo, escenario=args.escenario)
    else:
        partida_interactiva(
            seed=args.seed, max_turnos=args.turnos, escenario=args.escenario
        )


if __name__ == "__main__":
    main()
