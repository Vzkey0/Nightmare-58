# Convenciones de código y estructura

Reglas de trabajo de Nightmare 58. Aplican a todo el código del grupo.

## 1. Principio

**Toda decisión sobre una estructura de datos o un algoritmo se justifica.** Hay
que poder responder tres preguntas:

1. ¿Qué operaciones hace el sistema y con qué frecuencia?
2. ¿Por qué esta estructura y no otra?
3. ¿Cómo sabemos que es buena para este caso?

"Más eficiente" significa la mejor opción para este tamaño de datos y este patrón
de uso, no la opción más avanzada. `heap_sort`, un árbol AVL o un `QuadTree` se usan
cuando ganan en el caso real. Si una lista de 8 enemigos casi ordenada va mejor con
`insertion_sort`, la decisión correcta es `insertion_sort`.

## 2. Qué se justifica

| Caso | Exigencia |
|---|---|
| Contenedor o algoritmo de un sistema del juego | Ficha completa |
| Código que corre cada frame o varias veces por frame | Ficha completa y medición |
| Cambiar una decisión ya registrada | Actualizar la ficha |
| Variable local pequeña, sin impacto en rendimiento | Nada |

**Crítico** significa que corre dentro de `_process` o `_physics_process`, o que
puede provocar un tirón visible, como cargar una zona o abrir un menú grande.

## 3. Dónde se justifica

La justificación va en dos lugares.

**En el código**, un comentario corto junto a la declaración, con su ID:

```cpp
// J-003: nearly sorted between frames; insertion_sort is O(n + d) and n is small.
Designar::DynArray<Target> targets;
```

**En [Justificaciones.md](Justificaciones.md)**, la ficha completa con el mismo ID.
Un ID nunca se reutiliza. Si una decisión se reemplaza, su ficha pasa a estado
`Reemplazada` e indica por cuál.

## 4. Cómo medir

Una medición solo se acepta si cumple todo esto:

- Compara la opción elegida con al menos una alternativa real.
- Usa datos realistas: tamaño esperado y 10 veces ese tamaño.
- Se compila en modo optimizado (`-DCMAKE_BUILD_TYPE=Release`). Medir en debug no
  sirve.
- Repite la operación suficientes veces y reporta la mediana.
- Anota en la ficha máquina, sistema, tamaños y resultado.

Para medir se usa `Designar::Now` (`now.hpp`). Los programas de medición van en
`benchmarks/`, carpeta que se crea con la primera medición.

**Presupuesto:** a 60 FPS, un frame dura 16,6 ms, y Godot usa parte de ese tiempo.
La lógica del juego debe consumir una parte pequeña y conocida.

Dentro de código crítico:

- No reservar memoria en cada frame: reutilizar contenedores.
- Preferir arreglos a listas enlazadas cuando se recorre mucho. Están contiguos en
  memoria y aprovechan mejor la caché; `O(n)` no cuesta lo mismo en ambos.
- Calcular la distancia al cuadrado si solo se comparan distancias.
- No optimizar sin medir: primero se localiza dónde se va el tiempo.

## 5. Guía para elegir

Es el punto de partida, no un sustituto de la justificación. Las complejidades son
las habituales de cada estructura.

### Secuencias

| Necesito | Opción | Costo y motivo |
|---|---|---|
| Recorrer mucho, acceso por índice | `FixedArray`, `DynArray` (`array.hpp`) | Índice `O(1)`, buena caché |
| Insertar y quitar conociendo el nodo | `SLList`, `DLList` (`list.hpp`) | `O(1)`, pero cada nodo reserva memoria |
| Último en entrar, primero en salir | `stack.hpp` | `O(1)` |
| Primero en entrar, primero en salir | `queue.hpp` | `O(1)` |
| Insertar por ambos extremos | `deque.hpp` | `O(1)` |

### Búsqueda por clave

| Necesito | Opción | Costo y motivo |
|---|---|---|
| Búsqueda exacta, sin orden | `HashMap`, `chainedhash.hpp`, `openhash.hpp` | `O(1)` promedio, `O(n)` en el peor caso |
| Datos fijos ya ordenados | `DynArray` + `binary_search` | `O(lg n)`, sin memoria extra |
| Mantener orden con cambios frecuentes | `AVLTree`, `RbTree`, `TreeMap` | `O(lg n)` garantizado |
| Consultar por posición en el orden | `RankedAVLTree` | `O(lg n)` por rango |
| Lecturas muy concentradas en pocas claves | `SplayTree` | `O(lg n)` amortizado |
| Prefijos de texto, autocompletado | `Trie` (`trie.hpp`) | Depende del largo de la palabra, no de `n` |
| Jerarquía real, como habilidades | `MTreeNode` (`mtreenode.hpp`) | Árbol n-ario: refleja padres e hijos |

AVL mantiene el árbol más bajo y favorece la lectura; rojo-negro hace menos
rotaciones y favorece la escritura. `BTree` y `BPlusTree` están pensados para muchos
datos por nodo: requieren una justificación especialmente sólida en este juego.

### Prioridad

| Necesito | Opción | Costo y motivo |
|---|---|---|
| Máximo o mínimo con capacidad conocida | `FixedHeap` (`heap.hpp`) | `O(lg n)`, sin reservar memoria |
| Máximo o mínimo, tamaño variable | `DynHeap` (`heap.hpp`) | `O(lg n)` |
| Unir colas con frecuencia | `binomialheap.hpp`, `leftistheap.hpp`, `pairingheap.hpp` | Unión eficiente |
| Muchas reducciones de clave | `fibonacciheap.hpp` | Amortizado; su constante suele ser alta |

### Espacio

| Necesito | Opción | Costo y motivo |
|---|---|---|
| Consultas por zona con puntos agrupados | `QuadTree` (`quadtree.hpp`) | Subdivide solo donde hay puntos; trabaja en 2D (plano XZ) |
| Pocos objetos | Recorrido lineal | Con `n` pequeño, suele ganar a un árbol |

### Ordenamiento

Todos están en `sort.hpp`.

| Algoritmo | Tiempo | Memoria extra | Estable | Cuándo usarlo |
|---|---|---|---|---|
| `insertion_sort` | `O(n²)`, casi `O(n)` si está casi ordenado | `O(1)` | Sí | Pocos datos o casi ordenados |
| `merge_sort` | `O(n lg n)` siempre | `O(n)` | Sí | Hay que conservar el orden entre iguales |
| `heap_sort` | `O(n lg n)` siempre | `O(1)` | No | Peor caso garantizado sin memoria extra |
| `quicksort` | `O(n lg n)` promedio, `O(n²)` peor | Pila de recursión | No | Promedio rápido, si el peor caso es tolerable |
| `shell_sort` | Depende de la secuencia de saltos | `O(1)` | No | Tamaño medio, código sin memoria extra |
| `counting_sort` | `O(n + k)` | `O(n + k)` | No aplica | Enteros no negativos de rango pequeño `k` |
| `radix_sort` | `O(d(n + k))` | `O(n + k)` | No aplica | Enteros no negativos con muchos datos |

`counting_sort` y `radix_sort` ordenan solo enteros, no objetos con una clave. Por
eso la estabilidad no aplica y no sirven para ordenar enemigos u objetos del
inventario directamente.

Si solo hacen falta los `k` primeros, se usa un heap: no se ordena todo.

Antes de depender de la estabilidad de un algoritmo, se agrega una prueba que la
compruebe.

## 6. Reglas sobre DeSiGNAR

- Toda estructura del juego sale de DeSiGNAR.
- No se usan contenedores de la STL (`std::vector`, `std::map`...) ni `Array` o
  `Dictionary` de Godot para la lógica del juego.
- Sí se permiten utilidades que no son contenedores, como `<cassert>` o `<exception>`.
- En `src/game/` se usan los tipos propios de Godot (`Vector3`, `String`, `Ref<>`)
  al hablar con el motor.
- Si DeSiGNAR no tiene lo necesario, se implementa sobre sus estructuras y se
  justifica, como el árbol de comportamiento.

## 7. Estructura del proyecto

```
src/core/      Lógica sin Godot. Se prueba desde la terminal.
src/game/      Clases C++ registradas en Godot.
tests/         Pruebas de src/core/.
benchmarks/    Mediciones de rendimiento.
game/          Proyecto Godot: escenas, modelos y audio.
art/           Archivos .blend editables (ver art_guide.md).
extern/        DeSiGNAR y godot-cpp (no se modifican).
docs/          PDD, convenciones y justificaciones.
```

- `src/core/` no incluye nada de Godot.
- `src/game/` traduce entre Godot y el núcleo; las decisiones del juego van en
  `src/core/`.
- Toda lógica nueva de `src/core/` lleva pruebas en `tests/`.
- Las clases nuevas de `src/game/` se agregan a `CMakeLists.txt` y a
  `src/game/register_types.cpp`.
- Los `.cpp` nuevos de `src/core/` se agregan a `nightmare58_core` en `CMakeLists.txt`.
- Una clase normal se separa en `.hpp` y `.cpp`. Las plantillas (`template`) y las
  funciones `inline` cortas quedan en el `.hpp`.

## 8. Estilo de código

**Todo el código va en inglés, siempre:** carpetas, archivos, clases, funciones,
variables, comentarios y nombres de escenas y recursos. La documentación de `docs/`,
el `README.md` y los commits siguen en español.

| Elemento | Convención | Ejemplo |
|---|---|---|
| Idioma | Inglés | `classify_distance` |
| Archivos | `snake_case` | `skill_tree.cpp` |
| Clases y enums | `PascalCase` | `DistanceRange` |
| Funciones y variables | `snake_case` | `max_health` |
| Enumeraciones | `enum class` | `DistanceRange::Near` |
| Headers | `#pragma once` | |
| Sangría | 2 espacios, llaves en línea propia | |

Los comentarios explican el porqué, no lo que el código ya dice.

## 9. Errores y memoria

- Las excepciones de DeSiGNAR se atrapan en `src/game/`. Ninguna debe llegar a Godot.
- Los nodos de Godot se liberan con `queue_free()`, nunca con `delete`.
- Cada puntero tiene un dueño claro.
- La lógica con punteros se prueba en `src/core/` antes de llevarla a Godot.

## 10. Git y revisión

- Flujo: `main` ← `development` ← `feature/nombre`.
- Commits en español e imperativo: `Agregar búfer de inputs`.
- Se fusiona con **Merge** o **Rebase**, no con **Squash**.
- Cada escena `.tscn` la edita una sola persona a la vez.

Antes de aprobar un pull request:

- [ ] Compila en las tres plataformas y pasan las pruebas.
- [ ] Las decisiones nuevas tienen comentario con ID y ficha.
- [ ] El código crítico tiene medición registrada.
- [ ] `src/core/` sigue sin depender de Godot.
