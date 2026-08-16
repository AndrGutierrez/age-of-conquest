# Motor de Simulación — Age of Conquest

Motor lógico (back-end) del juego *Age of Conquest* implementado en Python
puro (solo biblioteca estándar, Python 3.9+). Implementa el modelo formal del
documento `parcial2_secciones_1_2.md` (Entregables 1 y 2 de la asignatura
SIMUSIST): economía, demografía, felicidad, rebelión y resolución de combate
con dados (estilo Risk).

## Ejecución

```bash
python main.py          # partida interactiva: 1 humano + 3 IA
python main.py --demo 5 # demo automática: 5 turnos con solo IA
python main.py --help
```

## Tests y validación

```bash
python -m unittest discover -s tests -v   # tests unitarios
python age_of_conquest/validacion.py      # Monte Carlo vs tabla esperada (§2.4.6)
```

## Arquitectura

| Módulo | Responsabilidad |
|---|---|
| `config.py`    | Parámetros fijos del modelo (§1.5 del documento) |
| `mapa.py`      | Mapa clásico de 42 territorios: adyacencias, continentes, terrenos |
| `estado.py`    | Estructuras de estado: `Province`, `Player`, `GameState` |
| `combate.py`   | Resolución estocástica de combate con dados (§2.4) |
| `economia.py`  | Recaudación, mantenimiento, población, felicidad y rebelión (§2.1–2.3, §2.8) |
| `motor.py`     | Motor de simulación con Lista de Eventos Futuros (LEF): fases del turno, eliminación y victoria |
| `ia.py`        | Perfiles estratégicos: Agresivo, Defensivo, Equilibrado (§2.5) |
| `cli.py`       | Interfaz de consola (REPL) y modo demo automático |
| `validacion.py`| Validación Monte Carlo contra los valores teóricos |

## Decisiones de diseño (para el informe técnico)

1. **κ (riesgo de rebelión):** la tabla §1.5.4 indica 0.10 pero los ejemplos
   numéricos de §2.8 usan κ = 0.01. Se adoptó **κ = 0.01** (consistente con los
   ejemplos) y es configurable vía `Config.kappa`.
2. **η_I y η_cap** (sensibilidades de impuestos y capacidad de carga a la
   infraestructura) no están tabuladas en el documento; se fijaron como valores
   de diseño: 0.10 y 0.15.
3. **Multiplicador de terreno θ_T y fortificación:** el documento los define
   (§1.5.1, §1.5.5) pero §2.4 no los integra. Se aplican escalando el valor de
   cada dado del defensor: `min(6, round(d · θ_T · (1 + 0.15·F)))`.
4. **Bancarrota:** si la tesorería queda negativa tras el cierre del turno, se
   produce deserción proporcional a la deuda y una penalización de felicidad.
5. **Provincia rebelde:** pasa a dueño 0 (neutral) con guarnición de 2 milicias;
   no ejecuta turnos y puede ser atacada.
6. **Población, felicidad y rebelión** se actualizan una vez por ronda global
   (turno completo), como indica §2.3.
7. **Calibración de felicidad:** con los parámetros literales del documento el
   sistema colapsa en ~3 rondas (impuestos + guerra erosionan H más rápido de
   lo que ε_vic la restaura). Se añadió un término de reversion a la media
   `ΔH += δ_eq·max(0, h_eq − H)` con δ_eq = 0.30 y h_eq = 0.70, y los impuestos
   de la IA se recalibraron (Agresivo 0.30, Equilibrado 0.25, Defensivo 0.15).
   Evidencia antes/después en la sección de Validación del informe.
8. **Tabla §2.4.6:** las filas (2,2) y (2,1) del documento contienen errores;
   los valores correctos por enumeración exhaustiva son (1.221, 0.779) y
   (0.421, 0.579). El simulador implementa las ecuaciones (2.4.2)-(2.4.3) y
   reproduce los valores teóricos exactos (ver `validacion.py`).
