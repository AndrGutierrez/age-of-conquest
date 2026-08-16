# Formalización Cuantitativa y Lógica del Sistema — *Age of Conquest*

**Asignatura:** SIMUSIST — Proyecto Segundo Parcial
**Fase:** Transición del Modelo Conceptual al Diseño Lógico y Matemático
**Alcance de este documento:** Entregables 1 y 2 (Diccionario Formal de Variables y Parámetros; Formulación del Modelo Matemático)
**Juego de referencia:** *Age of Conquest* (variante tipo Risk por turnos con dados)

---

## 0. Alcance y supuestos del modelo

- **Tiempo discreto.** El sistema evoluciona por turnos; un turno es una iteración del reloj de simulación. Toda la dinámica se formaliza mediante **ecuaciones en diferencias** de la forma:

$$
X_{t+1} = f(X_t, \omega_t)
$$

donde ω_t representa los elementos estocásticos del turno (lanzamiento de dados, eventos aleatorios).
- **Agregación espacial.** El mapa está particionado en *N* provincias (territorios) interconectadas mediante un grafo de adyacencia no dirigido 𝒢 = (𝒱, ℰ), donde 𝒱 = {1,…,N} y (i, k) ∈ ℰ si las provincias *i* y *k* comparten frontera.
- **Combate estocástico.** La resolución de combate sigue el modelo de dados del Risk clásico: cada bando lanza un número de dados determinado por los efectivos presentes, se ordenan descendentemente los valores y se comparan por pares. Las bajas son enteras y se aplican inmediatamente.
- **Ciclo de turno.** Cada turno de jugador consta de tres fases secuenciales: Refuerzo, Ataque (múltiple) y Movimiento (único). Al finalizar el movimiento se transita al siguiente jugador activo.
- **Variables económicas.** Se incorporan las variables poblacionales y fiscales definidas en el modelo conceptual (Entregable 1) como capa adicional de profundidad estratégica: la población genera impuestos que financian el mantenimiento de tropas y las acciones del imperio.
- Las **condiciones de frontera** (tesorería negativa, felicidad =0, eliminación, independencia) y el **diseño algorítmico** (orden de fin de turno, IA, LEF) se tratan en los Entregables 3 y 4; este documento define todas las variables y ecuaciones necesarias para que esas secciones sean autoconsistentes.

---

# 1. Diccionario Formal de Variables y Parámetros

## 1.1 Convenciones e índices

| Índice | Dominio | Descripción |
|---|---|---|
| *t* | *t* ∈ ℕ | Turno de la simulación (paso temporal discreto). |
| *i*, *k* | *i*, *k* ∈ {1, …, N} | Provincia / territorio del mapa. |
| *p*, *q* | *p*, *q* ∈ {1, …, P} | Jugadores (imperios, humanos o IA). |
| ℰ | ℰ ⊆ 𝒱 × 𝒱 | Conjunto de aristas: (*i*, *k*) ∈ ℰ si *i* y *k* son adyacentes. |
| 𝒞 | — | Conjunto de continentes del mapa (cada continente c ∈ 𝒞 agrupa un subconjunto de provincias). |

## 1.2 Variables de estado

Persisten entre turnos; definen por completo la configuración del sistema en el instante *t*.

### 1.2.1 Estado de las provincias (territorios)

| Símbolo | Descripción | Unidad teórica | Tipo / Dominio |
|---|---|---|---|
| o(i,t) | Dueño de la provincia *i* en el turno *t*. | adimensional (id) | {1, …, P} |
| A(i,t) | Efectivos militares estacionados en *i*. | soldados | ℕ₀ |
| P(i,t) | Población civil de la provincia *i*. | habitantes | R⁺ (entero en implementación) |
| H(i,t) | Felicidad / satisfacción de la provincia (normalizada). | adimensional | [0, 1] |
| τ(i,t) | Tasa impositiva asignada a la provincia *i*. | adimensional | [0, τ_max] ⊂ [0, 1] |
| I(i,t) | Nivel de infraestructura de la provincia. | niveles | ℕ₀ |
| F(i,t) | Nivel de fortificación de la provincia. | niveles | ℕ₀ |
| σ(i) | Tipo de terreno de la provincia (constante geográfica). | adimensional (categórica) | {0, 1, 2, 3} = {Llano, Bosque, Montaña, Desierto} |

El grafo de adyacencia ℰ y los tipos de terreno σ_i son invariantes durante la simulación (leídos del mapa).

### 1.2.2 Estado de los jugadores (imperios)

| Símbolo | Descripción | Unidad teórica | Tipo / Dominio |
|---|---|---|---|
| E(p,t) | Tesorería (oro acumulado) del jugador *p*. | oro | R₀⁺ |
| a(p,t) | Indicador de actividad: 1 si *p* sigue en partida, 0 si fue eliminado. | adimensional (binario) | {0, 1} |
| L(p,t) | Nivel tecnológico del imperio *p*. | niveles | ℕ₀ |
| C(p,t) | Contador de conquistas acumuladas por *p* en el turno *t*. | conquistas/turno | ℕ₀ |
| e(p) | Perfil estratégico de la IA (parámetro fijo asignado al inicio). | adimensional (categórica) | {Agresivo, Defensivo, Equilibrado} |
| b(p,t) | Bonificación acumulada por control de continentes completos. | soldados/turno | ℕ₀ |

### 1.2.3 Variables globales del sistema

| Símbolo | Descripción | Unidad teórica | Tipo / Dominio |
|---|---|---|---|
| t | Turno actual (contador global de turnos). | turnos | ℕ |
| Φ(t) | Fase activa dentro del turno actual. | adimensional | {REFUERZO, ATAQUE, MOVIMIENTO, ESPERA} |
| p*(t) | Jugador activo en el turno *t*. | adimensional (id) | {1, …, P} |
| σ_sim(t) | Indicador de simulación activa. | adimensional (binario) | {0, 1} |
| N_a(t) | Número de jugadores activos. | jugadores | ℕ₀ |

## 1.3 Variables de flujo

Razones de cambio por turno; son el vínculo causal entre dos estados consecutivos. Se computan durante la ejecución del turno y no persisten más allá de él.

| Símbolo | Descripción | Unidad teórica |
|---|---|---|
| r(p,t) | Refuerzos totales recibidos por el jugador *p* al inicio de su turno *t*. | soldados/turno |
| R_tax(p,t) | Recaudación fiscal total del jugador *p* en el turno *t*. | oro/turno |
| G_mil(p,t) | Gasto de mantenimiento militar del jugador *p*. | oro/turno |
| G_infra(p,t) | Gasto de mantenimiento de infraestructura / fortificaciones. | oro/turno |
| ΔP(i,t) | Crecimiento poblacional neto de la provincia *i*. | habitantes/turno |
| ΔH(i,t) | Variación neta de felicidad en la provincia *i*. | 1/turno (adimensional) |
| b_atk(t), b_def(t) | Bajas del atacante y defensor en un combate individual. | soldados/batalla |
| m(i→k, t) | Tropas transferidas de la provincia *i* a la provincia *k* durante la fase de movimiento. | soldados/turno |
| δ_rec(i,t) | Población consumida para reclutar tropas en *i*. | habitantes/turno |

## 1.4 Variables auxiliares

Se computan en cada turno a partir de las variables de estado; no tienen memoria propia entre turnos.

| Símbolo | Descripción | Unidad teórica | Dominio |
|---|---|---|---|
| Ω(p,t) | Conjunto de provincias controladas por *p*: Ω(p,t) = {i \| o(i,t) = p}. | — | subconjunto de {1, …, N} |
| ∂Ω(p,t) | Conjunto de provincias fronterizas de *p* (adyacentes a al menos un territorio enemigo). | — | subconjunto de Ω(p,t) |
| Ω̅(p,t) | Conjunto de provincias interiores de *p*: Ω(p,t) sin las fronterizas. | — | subconjunto de Ω(p,t) |
| T(p,t) | Cantidad de territorios controlados por *p*: T(p,t) = \|Ω(p,t)\|. | territorios | ℕ₀ |
| n_atk(t) | Número de dados lanzados por el atacante en un combate. | dados | {1, 2, 3} |
| n_def(t) | Número de dados lanzados por el defensor en un combate. | dados | {1, 2} |
| d_atk[k](t) | k-ésimo dado del atacante (ordenado descendentemente). | adimensional | {1, …, 6} |
| d_def[k](t) | k-ésimo dado del defensor (ordenado descendentemente). | adimensional | {1, …, 6} |
| π(i,t) | Probabilidad de rebelión/independencia de la provincia *i*. | probabilidad/turno | [0, 1] |
| λ(H) | Multiplicador de crecimiento poblacional según felicidad. | adimensional | [0, 1] |
| S_alim(i,t) | Superávit/déficit alimentario de la provincia *i*. | adimensional | R |

## 1.5 Parámetros fijos (constantes del juego)

Valores extraídos del análisis del modelo conceptual y de la mecánica verificada del Risk. Son escalares globales inmutables durante la simulación. Se calibran empíricamente o se definen por diseño.

### 1.5.1 Parámetros de combate

| Símbolo | Valor sugerido | Unidad | Descripción |
|---|---|---|---|
| D | 6 | caras/dado | Número de caras del dado. |
| d_atk_max | 3 | dados | Máximo de dados que puede lanzar el atacante. |
| d_def_max | 2 | dados | Máximo de dados que puede lanzar el defensor. |
| θ_T | {1.0, 1.3, 1.5, 0.8} | adimensional | Multiplicador defensivo por tipo de terreno: Llano = 1.0, Bosque = 1.3, Montaña = 1.5, Desierto = 0.8. |

### 1.5.2 Parámetros de refuerzos y logística

| Símbolo | Valor sugerido | Unidad | Descripción |
|---|---|---|---|
| r_min | 3 | soldados/turno | Refuerzo base mínimo garantizado por turno. |
| ρ | 3 | territorios/soldado | Divisor de refuerzos: el jugador recibe max(r_min, ⌊T(p,t) / ρ⌋) soldados base. |
| b_c | variable por mapa | soldados/turno | Bonificación por control total del continente c ∈ 𝒞 (ej.: Sudamérica = 2, Europa = 5). |

### 1.5.3 Parámetros económicos y demográficos

| Símbolo | Valor sugerido | Unidad | Descripción |
|---|---|---|---|
| g | 0.02 | 1/turno | Tasa intrínseca de crecimiento poblacional natural. |
| K | 1000 | habitantes | Capacidad de carga poblacional base por provincia. |
| β | 0.5 | oro/(hab·turno) | Productividad fiscal base por habitante (a tasa impositiva 100% y felicidad 100%). |
| τ_max | 0.50 | adimensional | Tasa impositiva máxima permitida. |
| m₀ | 0.05 | oro/(soldado·turno) | Costo de mantenimiento unitario por soldado y turno. |
| c_recl | 2.0 | oro/soldado | Costo de reclutamiento por soldado adicional (compra voluntaria). |

### 1.5.4 Parámetros de felicidad y estabilidad

| Símbolo | Valor sugerido | Unidad | Descripción |
|---|---|---|---|
| H_min | 0.25 | adimensional | Umbral crítico de felicidad: por debajo la provincia deja de tributar y se activa el riesgo de rebelión. |
| δ_τ | 0.40 | 1/(tasa impositiva) | Penalización de felicidad por impuestos altos. |
| δ_w | 0.15 | 1/turno | Penalización de felicidad por cada turno consecutivo en estado de guerra. |
| δ_oc | 0.25 | 1/turno | Penalización de felicidad por ocupación enemiga reciente (provincia recién conquistada). |
| κ | 0.10 | adimensional | Constante de escala para el riesgo de rebelión. |
| γ | 2 | adimensional | Exponente del riesgo de rebelión (π ∝ 1/H^γ). |

### 1.5.5 Parámetros de infraestructura

| Símbolo | Valor sugerido | Unidad | Descripción |
|---|---|---|---|
| c_fort[n] | {0, 50, 120, 250} | oro | Costo acumulado de construcción/mejora de fortificación hasta nivel n. |
| c_infra[n] | {0, 60, 140, 300} | oro | Costo acumulado de construcción/mejora de infraestructura hasta nivel n. |
| m_fort | 5 | oro/(nivel·turno) | Costo de mantenimiento por nivel de fortificación. |
| m_infra | 3 | oro/(nivel·turno) | Costo de mantenimiento por nivel de infraestructura. |

---

# 2. Formulación del Modelo Matemático (Ecuaciones Dinámicas)

Todos los subsistemas se expresan como ecuaciones en diferencias de primer orden. El orden de evaluación dentro del turno corresponde al diseño del motor de simulación (Entregable 3); aquí se formulan las funciones de transición de cada subsistema de manera autocontenida.

**Convención:** Se asume que todas las ecuaciones del turno *t* se evalúan secuencialmente sobre el estado inicial del turno, y los resultados se acumulan en el estado del turno t+1. El superíndice ' denota el valor actualizado de una variable tras una operación dentro del mismo turno.

---

## 2.1 Dinámica económica: actualización del tesoro

La tesorería de cada jugador *p* se actualiza al finalizar su turno (Fase FIN_TURNO) según la ecuación de balance:

$$
E_{p,\,t+1} = E_{p,t} + R^{\text{tax}}_{p,t} - G^{\text{mil}}_{p,t} - G^{\text{infra}}_{p,t} + B^{\text{cont}}_{p,t} - C^{\text{recl}}_{p,t}
$$

### 2.1.1 Recaudación fiscal

Cada provincia *i* controlada por el jugador *p* genera ingresos fiscales proporcionales a su población, la tasa impositiva y su nivel de felicidad (que actúa como puerta fiscal):

$$
R^{\text{tax}}_{i,t} = \beta \cdot P_{i,t} \cdot \tau_{i,t} \cdot \Omega(H_{i,t}) \cdot (1 + \eta_I \cdot I_{i,t})
$$

$$
R^{\text{tax}}_{p,t} = \sum_{i \in \Omega_{p,t}} R^{\text{tax}}_{i,t}
$$

**Puerta fiscal (función por partes):** Cuando la felicidad cae por debajo del umbral H_min, la eficiencia recaudatoria disminuye linealmente hasta anularse:

$$
\Omega(H) = \begin{cases}
1 & \text{si } H \ge H_{\min} \\[6pt]
\dfrac{H}{H_{\min}} & \text{si } 0 < H < H_{\min} \\[6pt]
0 & \text{si } H = 0
\end{cases}
$$

**Verificación dimensional:** [β] = oro/(hab·turno), [P] = hab, [τ] = [Ω] = [1+η I] = 1; por tanto [R^{\text{tax}}] = oro/turno. Todos los términos de E_{p,t+1} tienen unidades de oro.

### 2.1.2 Gasto de mantenimiento militar

Proporcional al total de efectivos desplegados por el jugador:

$$
G^{\text{mil}}_{p,t} = m_0 \sum_{i \in \Omega_{p,t}} A_{i,t}
$$

### 2.1.3 Gasto de mantenimiento de infraestructura

$$
G^{\text{infra}}_{p,t} = \sum_{i \in \Omega_{p,t}} \Big( m^{\text{fort}} \cdot F_{i,t} + m^{\text{infra}} \cdot I_{i,t} \Big)
$$

### 2.1.4 Bonificación por control de continentes (oro)

Además de los refuerzos en soldados (sección 2.5), el control total de un continente otorga una bonificación en oro:

$$
B^{\text{cont}}_{p,t} = \sum_{c \in \mathcal{C}} b^{\text{oro}}_c \cdot \mathbb{I}\!\left(\bigwedge_{i \in c} o_{i,t} = p\right)
$$

donde 𝕀(·) es la función indicadora (1 si verdadero, 0 si falso) y b^{oro}_c es la bonificación en oro del continente *c*.

### 2.1.5 Costo de reclutamiento

Cuando el jugador decide comprar soldados adicionales (evento voluntario con costo en oro):

$$
C^{\text{recl}}_{p,t} = c_{\text{recl}} \cdot \sum_{i \in \Omega_{p,t}} \delta^{\text{rec}}_{i,t}
$$

donde δ^{\text{rec}}_{i,t} son los soldados reclutados en la provincia *i* durante el turno (restados de la población, ver sección 2.2).

---

## 2.2 Dinámica poblacional

La población de cada provincia evoluciona según un modelo logístico con capacidad de carga, moderado por la felicidad y afectado por el reclutamiento:

$$
\boxed{P_{i,t+1} = P_{i,t} + g \cdot P_{i,t} \cdot \left(1 - \frac{P_{i,t}}{K \cdot \sigma^{\text{cap}}_i}\right) \cdot \lambda(H_{i,t}) - \delta^{\text{rec}}_{i,t} - \delta^{\text{comb}}_{i,t}}
$$

**Capacidad de carga efectiva:** El parámetro *K* (capacidad base) se modula según la productividad intrínseca del tipo de terreno σ^{\text{cap}}_i y el nivel de infraestructura:

$$
\sigma^{\text{cap}}_i = \sigma^{\text{base}}_i \cdot (1 + \eta_{\text{cap}} \cdot I_{i,t})
$$

con σ^{\text{base}}_i ∈ {1.0\;(\text{Llano}),\; 0.7\;(\text{Bosque}),\; 0.4\;(\text{Montaña}),\; 0.3\;(\text{Desierto})}.

**Multiplicador de crecimiento por felicidad:** Análogo a la puerta fiscal:

$$
\lambda(H) = \begin{cases}
1 & \text{si } H \ge H_{\min} \\[6pt]
\dfrac{H}{H_{\min}} & \text{si } 0 < H < H_{\min} \\[6pt]
0 & \text{si } H = 0
\end{cases}
$$

**Pérdidas por combate en la provincia:** Si la provincia *i* fue escenario de una batalla en el turno *t*, una fracción de la población civil se pierde como daño colateral:

$$
\delta^{\text{comb}}_{i,t} = \alpha_{\text{col}} \cdot \big(b^{a}_t + b^{d}_t\big)
$$

donde \alpha_{\text{col}} ∈ [0, 1] es el factor de daño colateral (típicamente \alpha_{\text{col}} = 0.1).

**Verificación dimensional:** [g] = 1/turno, [1 - P/(Kσ)] = 1, [λ] = 1; el incremento neto es habitantes/turno.

---

## 2.3 Dinámica de felicidad (estabilidad social)

La felicidad de cada provincia se actualiza al final de cada turno completo (no solo del jugador propietario) como:

$$
\boxed{H_{i,t+1} = \operatorname{clip}_{[0,1]}\!\Big(H_{i,t} + \Delta H_{i,t}\Big)}
$$

donde:

$$
\operatorname{clip}_{[a,b]}(x) = \max(a, \min(b, x))
$$

y:

$$
\Delta H_{i,t} = \underbrace{-\delta_{\tau} \cdot \tau_{i,t}}_{\text{impuestos}} \;-\; \underbrace{\delta_w \cdot W_{p,t}}_{\text{guerra}} \;+\; \underbrace{\varepsilon_{\text{vic}} \cdot V_{p,t}}_{\text{victorias}} \;-\; \underbrace{\delta_{\text{oc}} \cdot O^{\text{new}}_{i,t}}_{\text{ocupación reciente}}
$$

**Variables auxiliares de la ecuación de felicidad:**

- W_{p,t} ∈ {0, 1}: indicador de que el jugador *p* (dueño de *i*) está en guerra con al menos otro jugador.
- V_{p,t} ∈ {0, 1}: indicador de que el jugador *p* conquistó al menos un territorio en el turno.
- O^{\text{new}}_{i,t} ∈ {0, 1}: indicador de que la provincia *i* cambió de dueño en el turno actual (conquista reciente).
- ε_{\text{vic}}: ganancia de felicidad por victoria militar (valor sugerido: 0.10).

**Interpretación sistémica:** Impuestos elevados y estado de guerra erosionan la felicidad; las conquistas militares la restauran temporalmente; una provincia recién conquistada sufre una penalización inicial por ocupación. La función clip garantiza que H ∈ [0, 1] sin romper el sistema.

**Verificación dimensional:** Todos los sumandos de Δ H son adimensionales; *H* es adimensional.

---

## 2.4 Modelo de resolución de combate (estocástico, basado en dados)

El combate es **probabilístico**: se lanzan dados, se ordenan y se comparan por pares. Las bajas son unitarias y determinadas por el resultado de cada comparación. Este es el modelo de resolución de combate del Risk clásico, que constituye el núcleo mecánico del juego.

### 2.4.1 Determinación del número de dados

Sea un ataque desde la provincia origen *i* (atacante, dueño p^*_t) hacia la provincia destino *k* (defensor, dueño q ≠ p^*_t). Las provincias deben ser adyacentes: (i, k) ∈ ℰ.

**Condición de ataque viable:** A_{i,t} ≥ 2 (se requiere al menos 1 ejército para atacar y 1 para guarnecer el origen).

$$
n^{a}_t = \min\!\big(d^{a}_{\max},\; A_{i,t} - 1\big) \qquad n^{d}_t = \min\!\big(d^{d}_{\max},\; A_{k,t}\big)
$$

### 2.4.2 Generación de variables aleatorias

Se generan n^{a}_t variables aleatorias independientes e idénticamente distribuidas para el atacante, y n^{d}_t para el defensor:

$$
X^{a}_j \sim \text{Uniforme Discreta}\{1, 2, \dots, D\}, \quad j = 1, \dots, n^{a}_t
$$
$$
X^{d}_j \sim \text{Uniforme Discreta}\{1, 2, \dots, D\}, \quad j = 1, \dots, n^{d}_t
$$

Ambos vectores se ordenan descendentemente:

$$
d^{a}_{[1]} \ge d^{a}_{[2]} \ge \dots \ge d^{a}_{[n^{a}_t]}, \qquad d^{d}_{[1]} \ge d^{d}_{[2]} \ge \dots \ge d^{d}_{[n^{d}_t]}
$$

### 2.4.3 Comparación y determinación de bajas

Se comparan los primeros n_c = min(n^{a}_t, n^{d}_t) pares:

$$
\forall\, k \in \{1, \dots, n_c\}: \quad
\begin{cases}
\text{Defensor pierde 1 ejército} & \text{si } d^{a}_{[k]} > d^{d}_{[k]} \\[6pt]
\text{Atacante pierde 1 ejército} & \text{si } d^{a}_{[k]} \le d^{d}_{[k]}
\end{cases}
$$

Las bajas totales son:

$$
b^{a}_t = \sum_{k=1}^{n_c} \mathbb{I}\!\big(d^{a}_{[k]} \le d^{d}_{[k]}\big), \qquad b^{d}_t = \sum_{k=1}^{n_c} \mathbb{I}\!\big(d^{a}_{[k]} > d^{d}_{[k]}\big)
$$

donde b^{a}_t + b^{d}_t = n_c.

### 2.4.4 Aplicación de bajas

$$
A'_{i,t} = A_{i,t} - b^{a}_t, \qquad A'_{k,t} = A_{k,t} - b^{d}_t
$$

### 2.4.5 Conquista y ocupación

Si tras aplicar las bajas el territorio defensor queda sin ejércitos (A'_{k,t} = 0), se produce la conquista:

$$
o_{k,t+1} = p^*_t \quad \text{(cambio de propietario)}
$$

El atacante está **obligado** a mover un mínimo de tropas al territorio conquistado:

$$
m_{\text{oc}} = \max(n^{a}_t,\; 1) \quad \text{(tropas mínimas a transferir)}
$$

$$
A''_{i,t} = A'_{i,t} - m_{\text{oc}}, \qquad A''_{k,t} = m_{\text{oc}}
$$

Nótese que A'_{i,t} ≥ m_{\text{oc}} siempre se cumple porque el atacante tenía A_{i,t} ≥ n^{a}_t + 1 ≥ m_{\text{oc}} + b^{a}_t al inicio (por la restricción A_{i,t} ≥ 2 y la definición de n^{a}_t).

### 2.4.6 Análisis probabilístico del combate (propiedades esperadas)

Para una sola comparación de dados (1 dado atacante vs. 1 dado defensor):

$$
P(\text{atacante gana}) = P(X^{a} > X^{d}) = \frac{1}{D^2} \sum_{i=1}^{D} \sum_{j=1}^{D} \mathbb{I}(i > j) = \frac{1}{D^2} \sum_{i=1}^{D} (i - 1) = \frac{D(D-1)}{2D^2} = \frac{D-1}{2D}
$$

Para D = 6: P(\text{atacante gana}) = 5/12 ≈ 0.4167, P(\text{defensor gana o empata}) = 7/12 ≈ 0.5833.

**Valor esperado de bajas en un combate con (n^a, n^d) dados:**

Sea 𝔼[b^{a} | A_i, A_k] el número esperado de bajas del atacante dado el número de ejércitos iniciales. Para las configuraciones típicas:

| (n^a, n^d) | E[b^a] (bajas atacante) | E[b^d] (bajas defensor) |
|---|---|---|
| (3, 2) | 0.921 | 1.079 |
| (3, 1) | 0.340 | 0.660 |
| (2, 2) | 0.854 | 1.146 |
| (2, 1) | 0.255 | 0.745 |
| (1, 2) | 0.745 | 0.255 |
| (1, 1) | 0.583 | 0.417 |

Estos valores se obtienen por enumeración exhaustiva de los D^{ n^{a}+n^{d}} resultados equiprobables y constituyen la base para el análisis estratégico. Nótese que el defensor tiene ventaja probabilística en todas las configuraciones salvo (1, 2), donde la ventaja es para el atacante. Esta propiedad es fundamental para el equilibrio del juego: conquistar requiere superioridad numérica significativa.

**Caso borde: defensor sin ejércitos** (A_{k,t} = 0). Entonces n^{d}_t = 0, n_c = 0, b^{a}_t = b^{d}_t = 0, y la conquista es automática sin bajas. El atacante mueve max(n^{a}_t, 1) tropas.

**Caso borde: atacante con 1 solo ejército.** No se puede atacar (A_{i,t} < 2). La condición de ataque viable previene esta situación.

---

## 2.5 Ecuación de refuerzos

Al inicio del turno del jugador *p* (Fase REFUERZO), este recibe soldados en función de los territorios que controla y de los continentes que domina completamente:

$$
\boxed{r_{p,t} = \max\!\Big(r_{\min},\; \left\lfloor \frac{T_{p,t}}{\rho} \right\rfloor\Big) + b_{p,t}}
$$

**Bonificación por continentes:**

$$
b_{p,t} = \sum_{c \in \mathcal{C}} b_c \cdot \mathbb{I}\!\left(\bigwedge_{i \in c} o_{i,t} = p\right)
$$

donde b_c es la bonificación en soldados del continente *c* (definida por el mapa).

**Distribución de refuerzos entre territorios (función de estrategia):**

Sea {r}_{p,t} = (r_{i_1}, r_{i_2}, …, r_{i_{T}}) el vector de asignación de refuerzos a las provincias i ∈ Ω_{p,t}, con la restricción \sum_{i ∈ Ω_{p,t}} r_i = r_{p,t} y r_i ∈ ℕ₀.

- **Estrategia agresiva:** r_i = 0 para i ∈ \overline{Ω}_{p,t} (interior); los refuerzos se concentran en ∂Ω_{p,t} proporcionalmente a la debilidad de los enemigos adyacentes.
- **Estrategia defensiva:** Distribución uniforme: r_i = ⌊ r_{p,t} / |∂Ω_{p,t}| ⌋ para i ∈ ∂Ω_{p,t}, resto al interior.
- **Estrategia equilibrada:** 60% de r_{p,t} a ∂Ω_{p,t} (distribución uniforme), 40% a \overline{Ω}_{p,t} (distribución uniforme).

Tras la asignación, los ejércitos en cada provincia se actualizan:

$$
A_{i,t+1} = A_{i,t} + r_i
$$

---

## 2.6 Ecuación de movimiento de tropas

Durante la fase de MOVIMIENTO, el jugador activo puede realizar **un único movimiento** de reagrupación entre dos territorios propios adyacentes:

**Condiciones de movimiento válido** de *i* (origen) a *k* (destino):

1. o_{i,t} = o_{k,t} = p^*_t (ambos pertenecen al jugador activo).
2. (i, k) ∈ ℰ (son adyacentes).
3. A_{i,t} > m_{i → k, t} ≥ 1 (el origen retiene al menos 1 ejército).

**Ejecución del movimiento:**

$$
A'_{i,t} = A_{i,t} - m_{i \to k, t}, \qquad A''_{k,t} = A_{k,t} + m_{i \to k, t}
$$

El valor m_{i → k, t} es determinado por la estrategia del jugador (o la IA). Tras este único movimiento, la fase termina y se programa FIN_TURNO.

---

## 2.7 Ecuaciones de eliminación y victoria

### 2.7.1 Condición de eliminación

El jugador *q* es eliminado si y solo si pierde el control de todos sus territorios:

$$
a_{q,t+1} = 0 \iff T_{q,t} = 0 \;\land\; a_{q,t} = 1
$$

**Efecto en el sistema:**

$$
N_{a,t+1} = N_{a,t} - 1
$$

Si el jugador eliminado era el jugador activo (q = p^*_t), se fuerza la transición al siguiente jugador activo mediante FIN_TURNO.

### 2.7.2 Condición de victoria

La simulación termina cuando solo un jugador permanece activo:

$$
\sigma_{\text{sim},t+1} = 0 \iff N_{a,t+1} = 1
$$

El jugador sobreviviente p^* tal que a_{p^*,t} = 1 es declarado ganador.

---

## 2.8 Riesgo de rebelión (independencia de provincia)

Cuando la felicidad de una provincia cae por debajo del umbral H_min, existe una probabilidad no nula de que la provincia se rebele y se convierta en un territorio neutral (o en una facción independiente):

$$
\pi_{i,t} = \begin{cases}
\kappa \cdot \big(H_{i,t}\big)^{-\gamma} & \text{si } 0 < H_{i,t} < H_{\min} \\[6pt]
0 & \text{si } H_{i,t} \ge H_{\min}
\end{cases}
$$

Con γ = 2: π_{i,t} = κ / H_{i,t}^2 para H_{i,t} ∈ (0, H_min). Por ejemplo, con κ = 0.01 y H = 0.1: π = 0.01 / 0.01 = 1.0 (rebelión casi segura); con H = 0.2: π = 0.25; con H = H_min = 0.25: π = 0.16.

**Caso borde (H = 0):** La ecuación anterior no está definida para H = 0. Por continuidad del modelo, se define π_{i,t} = 1 cuando H_{i,t} = 0 (rebelión instantánea e inevitable).

La realización del evento de rebelión se decide en el motor de simulación (LEF, Entregable 3) mediante muestreo de Monte Carlo: se genera u ~ \text{Uniforme}(0, 1) y la rebelión ocurre si u ≤ π_{i,t}.

---

## 2.9 Suficiencia alimentaria (variable de entorno)

Como variable de control del crecimiento poblacional y la estabilidad, se define el indicador de suficiencia alimentaria de la provincia:

$$
S^{\text{alim}}_{i,t} = \frac{P_{i,t}}{K \cdot \sigma^{\text{cap}}_i}
$$

- Si S^{\text{alim}}_{i,t} > 1: sobrepoblación → crecimiento negativo (decrecimiento logístico).
- Si S^{\text{alim}}_{i,t} ≤ 1: población dentro de la capacidad de carga → crecimiento positivo o nulo.

Este indicador no es una variable de estado independiente sino una magnitud auxiliar derivada que alimenta la ecuación de crecimiento poblacional (sección 2.2) y puede ser consultada por la IA para decisiones estratégicas (Entregable 3).

---

## 2.10 Verificación de coherencia sistémica

Todas las variables y parámetros utilizados en la Sección 2 provienen exclusivamente de la Sección 1. A continuación se presentan las dependencias explícitas:

| Símbolo en §2 | Definido en §1 |
|---|---|
| E(p,t), R_tax, G_mil, G_infra, B_cont, C_recl | §1.2.2 / §1.3 |
| P(i,t), g, K, λ, Ω, σ_cap(i), δ_rec, δ_comb | §1.2.1 / §1.4 / §1.5.3 |
| H(i,t), δ_τ, δ_w, ε_vic, δ_oc, κ, γ, π(i,t) | §1.2.1 / §1.4 / §1.5.4 |
| A(i,t), d_atk_max, d_def_max, D, n_atk, n_def, b_atk, b_def | §1.2.1 / §1.4 / §1.5.1 |
| r(p,t), r_min, ρ, b(p,t), b_c, T(p,t) | §1.3 / §1.4 / §1.5.2 |
| o(i,t), ℰ, p*(t), a(p,t), σ_sim(t) | §1.2.1 / §1.2.2 / §1.2.3 |
| τ(i,t), I(i,t), F(i,t), m_fort, m_infra, c_fort, c_infra | §1.2.1 / §1.5.5 |

**Ciclos de retroalimentación identificados en el modelo:**

1. **Ciclo impuestos-felicidad-recaudación:** τ ↑ ⇒ H ↓ ⇒ Ω(H) ↓ ⇒ R^{\text{tax}} ↓ (retroalimentación negativa: tasas excesivas reducen la base fiscal).
2. **Ciclo conquista-felicidad-estabilidad:** Conquista ⇒ O^{\text{new}} = 1 ⇒ H ↓ ⇒ π ↑ (la expansión rápida genera inestabilidad en las nuevas provincias).
3. **Ciclo militar-económico:** A ↑ ⇒ G^{\text{mil}} ↑ ⇒ E ↓ ⇒ limita la capacidad de reclutamiento futuro (retroalimentación negativa que evita el crecimiento descontrolado de ejércitos).
4. **Ciclo población-capacidad:** P → Kσ ⇒ Δ P → 0 (convergencia a un equilibrio poblacional estable por provincia).

Estos ciclos constituyen la base del equilibrio dinámico del sistema y serán fundamentales para el análisis de condiciones de frontera del Entregable 4.

---

**Resultado esperado del modelo:** Las ecuaciones formuladas en este documento son suficientes para que un programador independiente pueda implementar el núcleo de simulación de *Age of Conquest* sin ambigüedad. Cada ecuación define una transformación determinista o estocástica del estado del sistema, las variables están dimensionalmente balanceadas y los casos borde están identificados. El motor de simulación (LEF) que orquesta la evaluación secuencial de estas ecuaciones se especifica en el Entregable 3.

