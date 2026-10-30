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
| Habilidades y zonas | Árbol n-ario | Pendiente |
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
