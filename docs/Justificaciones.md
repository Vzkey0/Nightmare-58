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
| Búfer de inputs | Cola | Pendiente |
| Menús anidados | Pila | Pendiente |
| Ataque del jefe | Heap | Pendiente |
| Base de objetos | Tabla hash | Pendiente |
| Bestiario | Trie | Pendiente |
| Lock-on | `insertion_sort` | Pendiente |
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
- **Crítico:** Sí. `decide` corre de forma constante, hasta una vez por frame y enemigo
- **Datos:** 15 nodos en el árbol del PDD; máximo por definir
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
