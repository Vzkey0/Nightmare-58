# Registro de justificaciones

Una ficha por decisión, según [Convenciones.md](Convenciones.md).

## Plantilla

```markdown
## J-000: Sistema y decisión

- **Estado:** Propuesta | Aceptada | Reemplazada por J-000
- **Código:** archivo y símbolo
- **Crítico:** Sí o No, y con qué frecuencia corre
- **Datos:** tamaño esperado y máximo
- **Operaciones:** cuáles hace y cuál domina
- **Elegida:** estructura o algoritmo y su complejidad
- **Descartadas:** cada alternativa y por qué perdió
- **Medición:** máquina, sistema, tamaños y resultados, o "No aplica"
- **Conclusión:** por qué esta opción gana en este caso
```

## Pendientes

Decisiones tomadas en el PDD que aún no tienen ficha. Cada una se justifica al
implementarse.

| Sistema | Propuesta del PDD | Ficha |
|---|---|---|
| Zonas | Árbol n-ario | Pendiente |
| Combos y estados alterados | Listas | Pendiente |
| Objeto rápido | Lista recorrida en círculo | Pendiente |
| Fantasma y rastro | Lista de posiciones | Pendiente |
| Búfer de inputs | Cola | J-004 |
| Menús anidados | Pila | Pendiente |
| Ataque del jefe | Heap | Pendiente |
| Base de objetos | Tabla hash | Pendiente |
| Bestiario | Trie | Pendiente |
| Lock-on | `insertion_sort` | Pendiente |
| Rutas de enemigos | `NavigationAgent3D` de Godot | Pendiente: hoy caminan en línea recta |
| Inventario | `merge_sort` | Pendiente |
| Récords | `quicksort` | Pendiente |
| Botín, nivel, fase, tasa de cambio | `binary_search` | Pendiente |

## Fichas

## J-001: Árbol de habilidades con `MTreeNode`

- **Estado:** Aceptada
- **Código:** `src/core/progression/skill_tree.hpp`, `SkillTree::root`
- **Crítico:** No. Corre al usar el menú de habilidades, no en cada frame
- **Datos:** alrededor de 20 habilidades; máximo por definir
- **Operaciones:** crear el árbol una vez, buscar por ID y consultar al padre. Domina
  la búsqueda
- **Elegida:** `MTreeNode`. Búsqueda `O(n)`, acceso al padre `O(1)`
- **Descartadas:** `Tree` (`tree.hpp`) es un árbol binario de búsqueda: ordena por
  clave y no representa una jerarquía con varios hijos. `DynArray` con índice al
  padre representa la jerarquía, pero obliga a mantener esa relación a mano
- **Medición:** No aplica
- **Conclusión:** `MTreeNode` refleja la jerarquía real, admite cualquier cantidad de
  hijos y es de DeSiGNAR. Con pocas habilidades, buscar en `O(n)` es suficiente

## J-002: Árbol de comportamiento con `MTreeNode`

- **Estado:** Aceptada
- **Código:** `src/core/ai/behavior_tree.hpp`, `BehaviorTree::root`
- **Crítico:** Sí. `decide` corre de forma constante: 10 veces por segundo y enemigo (J-005)
- **Datos:** 15 nodos en el árbol del PDD y 26 en el del esqueleto; máximo por definir
- **Operaciones:** crear el árbol una vez y recorrer los hijos en orden. Domina el
  recorrido
- **Elegida:** `MTreeNode`. Evaluar es `O(n)` en el peor caso y no reserva memoria
- **Descartadas:** `DynArray` con índices al primer hijo y al hermano derecho obliga a
  mantener esos índices a mano y fue más lento en esta medición. `SLList` de hijos,
  propuesta inicial del PDD, no se midió: exige una lista por nodo y `MTreeNode` ya da
  los hijos enlazados y en orden
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/behavior_tree_benchmark.cpp`. Peor caso, visitando todas las ramas. Mediana
  de 101 muestras de 20 000 evaluaciones, en tres ejecuciones:

  | Nodos | `MTreeNode` | `DynArray` |
  |---|---|---|
  | 16 | 10,08 a 10,23 ns | 12,84 a 13,12 ns |
  | 151 | 109,45 a 112,15 ns | 144,62 a 164,03 ns |

- **Conclusión:** `MTreeNode` fue más rápido y refleja la jerarquía real. Con el tamaño
  esperado, una evaluación usa alrededor del 0,00006 % de un frame de 16,6 ms

## J-003: Rotación de ataques con `DynQueue`

- **Estado:** Aceptada
- **Código:** `src/core/ai/behavior_tree.hpp`, colas de ataques de `BehaviorTree`
- **Crítico:** No. `decide` solo lee el frente; la cola cambia al ejecutar un ataque
- **Datos:** pocos ataques por acción; máximo por definir
- **Operaciones:** leer el frente y mover el primero al final. Domina la lectura
- **Elegida:** `DynQueue`. Ambas operaciones son `O(1)`
- **Descartadas:** `DynArray` con un índice circular logra lo mismo, pero hay que
  mantener el índice a mano. Un heap no aplica: los ataques rotan, no compiten por
  prioridad
- **Medición:** No aplica
- **Conclusión:** la cola expresa directamente la rotación y sus operaciones cuestan
  `O(1)`

## J-004: Búfer de inputs con `FixedQueue`

- **Estado:** Aceptada
- **Código:** `src/core/player/player_actions.hpp`, `PlayerActions::buffer`
- **Crítico:** Sí. `update` lee el frente en cada tick físico
- **Datos:** 2 pulsaciones como máximo; se midió también con 20
- **Operaciones:** leer el frente en cada tick, y poner o quitar al pulsar o caducar
  una entrada. Domina la lectura
- **Elegida:** `FixedQueue`. Todas las operaciones son `O(1)` y nunca reserva memoria
- **Descartadas:** `DynQueue` rindió igual, pero puede reservar memoria durante el
  juego, algo que no hace falta porque la capacidad es fija y pequeña. Recorrer la cola
  para envejecer entradas tampoco: se guarda la hora de cada pulsación y solo se mira
  el frente
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/input_buffer_benchmark.cpp`. Mediana de 101 muestras de 20 000 frames, con
  una pulsación cada 16 frames, en tres ejecuciones:

  | Capacidad | `FixedQueue` | `DynQueue` |
  |---|---|---|
  | 2 | 0,445 a 0,45 ns | 0,455 a 0,46 ns |
  | 20 | 0,455 ns | 0,455 ns |

- **Conclusión:** en tiempo es un empate. `FixedQueue` gana por no reservar memoria en
  código crítico, y su costo es despreciable frente a un frame de 16,6 ms

## J-005: Decisiones de enemigos 10 veces por segundo

- **Estado:** Aceptada
- **Código:** `src/game/enemies/skeleton_enemy.cpp`, `THINK_TIME`, y `src/core/ai/enemy_actions.hpp`
- **Crítico:** Sí. `EnemyActions::update` corre en cada tick físico, y `decide` 10 veces por segundo
- **Datos:** hasta 8 enemigos activos; se midió también con 80
- **Operaciones:** avanzar la acción en cada tick y recorrer el árbol al pensar. Domina el avance
- **Elegida:** pensar cada 0,1 s, desfasado entre enemigos, sin reservar memoria. El rayo de línea
  de vista se limita a 5 veces por segundo
- **Descartadas:** pensar en cada tick costó unas 4,8 veces más y se siente peor: el enemigo reacciona
  en el mismo frame. Reevaluar solo ante eventos ahorraría aún menos y agrega estado
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/enemy_ai_benchmark.cpp`. Camino más largo del árbol del esqueleto. Mediana de 101
  muestras de 6000 ticks, en tres ejecuciones, en nanosegundos por tick para todos los enemigos:

  | Enemigos | En cada tick | 10 veces por segundo |
  |---|---|---|
  | 8 | 212 a 228 ns | 44 a 49 ns |
  | 80 | 2288 a 4381 ns | 479 a 992 ns |

- **Conclusión:** con 8 enemigos, decidir usa cerca del 0,0003 % de un frame de 16,6 ms. La frecuencia
  se eligió por naturalidad; el rendimiento no la limita. No se midió el costo de los rayos ni de la
  animación, que quedan fuera de esta prueba porque dependen de Godot

## J-006: Turnos de ataque con un contador

- **Estado:** Aceptada
- **Código:** `src/core/ai/attack_turns.hpp`, `AttackTurns`
- **Crítico:** Sí. Cada enemigo consulta `available` al pensar
- **Datos:** 2 turnos a la vez, para hasta 8 enemigos; se midió también con 80
- **Operaciones:** consultar si hay turno, tomarlo y devolverlo. Domina la consulta
- **Elegida:** un contador y un temporizador en el jugador. Todo es `O(1)` y no guarda ninguna lista.
  El primero en pensar con turno libre lo toma, y solo lo pide quien ya está a su alcance
- **Descartadas:** recorrer una `DynArray` de enemigos para contar turnos es `O(n)` por consulta, lo
  que da `O(n²)` por tick con todos consultando, y obliga a mantener esa lista al crear y borrar enemigos.
  Elegir siempre al más cercano con un heap da un reparto poco mejor: la espera tras cada ataque ya rota
  a los atacantes
- **Medición:** misma máquina, programa y método que J-005, en nanosegundos por tick:

  | Enemigos | Contador | Recorrer la lista |
  |---|---|---|
  | 8 | 0,05 a 0,07 ns | 25 a 27 ns |
  | 80 | 0,05 a 0,07 ns | 2167 a 3037 ns |

  El valor del contador es tan bajo porque el compilador simplifica el ciclo; indica que no pesa, no
  su costo exacto.
- **Conclusión:** el contador es más corto y soporta cualquier cantidad de enemigos sin que se conozcan
