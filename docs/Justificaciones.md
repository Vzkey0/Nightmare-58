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
| IA de enemigos | Árbol de comportamiento propio sobre `list.hpp` | Pendiente |
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
