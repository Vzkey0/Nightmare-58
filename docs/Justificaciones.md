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
| Objeto rápido | Lista recorrida en círculo | J-013 |
| Rastro de enemigos | Lista de posiciones | Pendiente |
| Búfer de inputs | Cola | J-004 |
| Menús anidados | Pila | J-014 |
| Ataque del jefe | Heap | Pendiente |
| Base de objetos | Tabla hash | J-007 |
| Bestiario | Trie | Pendiente |
| Lock-on | `insertion_sort` | Pendiente |
| Rutas de enemigos | `NavigationAgent3D` de Godot | Pendiente: hoy caminan en línea recta |
| Inventario | `merge_sort` | J-008 y J-009 |
| Récords | `quicksort` | Pendiente |
| Botín | `binary_search` | J-010: gana el recorrido lineal |
| Nivel, fase, tasa de cambio | `binary_search` | Pendiente |

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

## J-007: Base de objetos con `HashMap` y `DynArray`

- **Estado:** Aceptada
- **Código:** `src/core/progression/item_catalog.hpp`, `ItemCatalog`
- **Crítico:** No. Se busca al recoger un objeto y al cargar la partida
- **Datos:** 6 objetos hoy y unos 30 al terminar el capítulo; se midió con 30 y 300
- **Operaciones:** traducir una clave de texto a un `ItemId` y leer un objeto por `ItemId`. Domina
  la lectura por `ItemId`
- **Elegida:** `HashMap` de clave a `ItemId`, `O(1)` promedio, y `DynArray` indexado por `ItemId`,
  `O(1)`. El texto solo se usa en los bordes: escenas y partidas guardadas
- **Descartadas:** `binary_search` sobre claves ordenadas y recorrido lineal perdieron en la medición.
  Guardar solo números en las escenas ahorra la tabla, pero una partida guardada dejaría de servir al
  reordenar el catálogo
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/progression_benchmark.cpp`. Mediana de 101 muestras de 200 operaciones, en tres
  ejecuciones, en nanosegundos por operación:

  | Claves | `HashMap` | `binary_search` | Lineal |
  |---|---|---|---|
  | 30 | 10 a 15,5 | 30 a 32,5 | 36,5 a 42,5 |
  | 300 | 12 a 16,5 | 64,5 a 66,5 | 258,5 a 343,5 |

- **Conclusión:** la tabla es unas 3 veces más rápida que la búsqueda binaria con 30 claves y casi no
  cambia con el tamaño

## J-008: Cantidades del inventario indexadas por `ItemId`

- **Estado:** Aceptada
- **Código:** `src/core/progression/inventory.hpp`, `Inventory::counts`
- **Crítico:** No. Cambia al recoger o usar un objeto
- **Datos:** un contador por objeto del catálogo; se midió con 30 y 300
- **Operaciones:** sumar, restar y consultar cantidades. Dominan esas tres
- **Elegida:** `DynArray` con una cantidad por `ItemId`. Todo es `O(1)` y sin búsqueda
- **Descartadas:** una lista de pilas obliga a buscar la pila en `O(n)` en cada cambio, y solo ahorraría
  unos enteros, porque el catálogo es pequeño
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/progression_benchmark.cpp`. Mediana de 101 muestras de 200 operaciones, en tres
  ejecuciones, en nanosegundos por operación:

  | Objetos | Por `ItemId` | Buscando la pila |
  |---|---|---|
  | 30 | 1,5 | 4,5 a 6 |
  | 300 | 1,5 | 41,5 a 50 |

- **Conclusión:** como un `ItemId` ya es un índice, buscar sería trabajo sin ninguna ganancia

## J-009: Orden del inventario con `merge_sort`

- **Estado:** Aceptada
- **Código:** `src/core/progression/inventory.cpp`, `Inventory::sorted`
- **Crítico:** No. Corre al abrir o cambiar el menú, nunca en cada frame
- **Datos:** hasta 30 filas; se midió también con 300
- **Operaciones:** ordenar por recientes y, encima, por tipo o por valor
- **Elegida:** `merge_sort`. `O(n lg n)` siempre y estable, algo que el orden en dos pasadas necesita.
  `test_inventory_sort_is_stable` comprueba la estabilidad de la versión de DeSiGNAR
- **Descartadas:** `insertion_sort` también es estable y ganó con 30 filas, pero es `O(n²)` y pierde por
  más del doble con 300. `heap_sort` y `quicksort` no son estables
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/progression_benchmark.cpp`. Mediana de 101 muestras de 200 operaciones, en tres
  ejecuciones, en nanosegundos por operación, incluida la copia del arreglo:

  | Filas | `merge_sort` | `insertion_sort` | Solo la copia |
  |---|---|---|---|
  | 30 | 153,5 a 189,5 | 126,5 a 166,5 | 29 a 40,5 |
  | 300 | 3705 a 5870,5 | 10090,5 a 10351,5 | 80 a 95 |

- **Conclusión:** con el tamaño esperado la diferencia es de unos 25 ns en un menú, sin efecto real. Se
  prefiere el peor caso garantizado, porque un inventario más grande no empeora

## J-010: Tabla de loot con recorrido lineal

- **Estado:** Aceptada. Cambia lo propuesto en el PDD (`binary_search`)
- **Código:** `src/core/progression/loot_table.hpp`, `LootTable::pick`
- **Crítico:** No. Corre una vez por enemigo muerto
- **Datos:** 8 entradas por tabla; se midió con 6 y 60
- **Operaciones:** elegir una entrada según un número al azar
- **Elegida:** pesos acumulados en un `DynArray` y recorrido lineal, `O(n)`
- **Descartadas:** `binary_search` es `O(lg n)`, pero fue más lento en los dos tamaños: sus saltos son
  impredecibles y la versión de DeSiGNAR es recursiva
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/progression_benchmark.cpp`. Mediana de 101 muestras de 200 operaciones, en tres
  ejecuciones, en nanosegundos por operación:

  | Entradas | Lineal | `binary_search` |
  |---|---|---|
  | 6 | 7,5 a 8,5 | 9 a 10 |
  | 60 | 18,5 a 20 | 23,5 a 24 |

- **Conclusión:** la opción con mejor complejidad no es la mejor con este tamaño. El recorrido es más
  corto y más rápido

## J-011: Rastro del fantasma con `FixedQueue`

- **Estado:** Retirada. El fantasma se quitó del juego, así que esta estructura ya no existe. La
  medición se hizo antes de quitarlo
- **Código:** ninguno
- **Crítico:** Sí. Corría durante la partida, 5 veces por segundo
- **Datos:** 100 puntos, que son 20 s; se midió también con 1000
- **Operaciones:** agregar un punto y soltar el más viejo. Al morir se copia a un `DynArray`, que el
  fantasma lee por índice en `O(1)` en cada tick
- **Elegida:** `FixedQueue`. Todo es `O(1)` y nunca reserva memoria
- **Descartadas:** `SLList` reserva un nodo en cada punto y fue unas 10 veces más lenta. `DynQueue` rindió
  parecido, pero puede reservar memoria, algo innecesario con una capacidad fija
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/progression_benchmark.cpp`. Mediana de 101 muestras de 200 operaciones, en tres
  ejecuciones, en nanosegundos por operación. El programa ya no incluye esta prueba:

  | Capacidad | `FixedQueue` | `SLList` | `DynQueue` |
  |---|---|---|---|
  | 100 | 3 | 29 a 34,5 | 4,5 |
  | 1000 | 3 | 26,5 a 39 | 4,5 |

- **Conclusión:** el rastro es una ventana de tamaño fijo, justo lo que hace una cola circular. El fantasma
  gasta lo mismo por tick sea cual sea el largo del camino

## J-012: Objetos recogidos con `DynBitSet`

- **Estado:** Aceptada
- **Código:** `src/core/progression/player_progress.hpp`, `PlayerProgress::taken`
- **Crítico:** No. Se consulta al cargar una escena y cambia al recoger
- **Datos:** hasta 256 objetos colocados en los niveles; se midió con 40 y 400
- **Operaciones:** marcar un id y consultar si está marcado. Domina la consulta
- **Elegida:** `DynBitSet`. Las dos operaciones son `O(1)` y gasta un bit por objeto
- **Descartadas:** `HashSet` fue unas 3 veces más lento y gasta memoria por nodo; un `DynArray` de ids
  recorrido en cada consulta es `O(n)` y crece mal
- **Medición:** Intel Core i5-13420H, Windows 11, GCC UCRT64, modo Release, con
  `benchmarks/progression_benchmark.cpp`. Mediana de 101 muestras de 200 operaciones, en tres
  ejecuciones, en nanosegundos por operación:

  | Objetos | `DynBitSet` | `HashSet` | Recorrer una lista |
  |---|---|---|---|
  | 40 | 1,5 a 2 | 5 a 7 | 7,5 a 9,5 |
  | 400 | 1,5 a 2 | 5 a 9 | 78 a 120,5 |

- **Conclusión:** los ids son enteros pequeños y densos, el mejor caso para un conjunto de bits

## J-013: Objeto rápido con `FixedQueue`

- **Estado:** Aceptada. Cambia lo propuesto en el PDD (lista recorrida en círculo)
- **Código:** `src/core/progression/quick_slots.hpp`, `QuickSlots::slots`
- **Crítico:** No. Corre al pulsar el botón
- **Datos:** 4 espacios como máximo
- **Operaciones:** leer el objeto actual y pasar al siguiente
- **Elegida:** `FixedQueue`. El frente es el objeto en la mano, y pasar al siguiente es sacarlo y volverlo
  a poner. Ambos pasos son `O(1)` y no reservan memoria
- **Descartadas:** una lista circular da lo mismo, pero reserva nodos y hay que mantener los enlaces. Un
  arreglo con índice obliga a mantener ese índice a mano
- **Medición:** No aplica
- **Conclusión:** la rotación ya existe en una cola, igual que en J-003

## J-014: Menús anidados con `FixedStack`

- **Estado:** Aceptada
- **Código:** `src/core/menu_stack.hpp`, `MenuStack::screens`
- **Crítico:** No. Corre con la entrada del jugador
- **Datos:** 2 niveles hoy; 4 como máximo
- **Operaciones:** abrir una pantalla, volver y leer la actual
- **Elegida:** `FixedStack`. Todo es `O(1)`, y cada entrada guarda su cursor, así que al volver se regresa
  a la fila que se dejó
- **Descartadas:** una sola variable con la pantalla actual obliga a saber a mano a dónde volver y pierde
  el cursor. `DynStack` puede reservar memoria sin necesidad
- **Medición:** No aplica
- **Conclusión:** los menús se cierran en orden inverso al que se abren, que es exactamente una pila
