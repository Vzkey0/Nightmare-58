# Nightmare 58: Project Design & Development (PDD)

Estado: borrador. Las decisiones sin cerrar están en [Decisiones pendientes](#10-decisiones-pendientes).

## 1. Visión

Souls-like 3D low poly ambientado en una Venezuela distópica, 2015-2018. Un
emigrante vuelve a buscar a su madre y recorre un país golpeado por apagones,
escasez e hiperinflación, donde la pérdida de la alegría despertó a las leyendas
urbanas venezolanas. La historia completa está en [lore.md](lore.md).

El nombre viene del +58, el código telefónico de Venezuela.

**Objetivo académico (Programación 3):** que las estructuras de datos sean lo
que hace funcionar el juego, no un añadido.

**Plataformas:** Linux, Windows y macOS.

## 2. Pilares de diseño

1. **Combate exigente:** pocos enemigos, patrones legibles, castigo por errores.
2. **La crisis es una mecánica:** apagones, inflación y escasez cambian cómo se juega.
3. **Las estructuras se pueden ver:** el modo de depuración las muestra en vivo.

## 3. Alcance

**Entra (versión a entregar):**

- Capítulo 1: la avenida, con refugio y minijefes, y el llano
- Dos tipos de enemigos comunes
- Un jefe completo: El Silbón, en el llano
- Combate, loot, inventario, árbol de habilidades y moneda con inflación
- Modo de depuración del árbol de decisiones

**Queda fuera, salvo que sobre tiempo:** más jefes (La Sayona y otras leyendas),
árbol de diálogo, Florentino y el Diablo. El final es único: no hay finales múltiples.

## 4. Mecánicas

### Combate

Ataque ligero y pesado, esquiva y fijado de objetivo, con barra de resistencia. Los botones presionados durante una animación se guardan y se
ejecutan al terminar.

### Decisiones de enemigos

El árbol de comportamiento se evalúa de forma constante con la posición del jugador:

```
Selector
├─ Secuencia: ¿vida < 30%?  → fase furiosa
├─ Secuencia: ¿cerca?       → ataque cuerpo a cuerpo
├─ Secuencia: ¿media?       → Selector(ataque a distancia | acercarse lento)
└─ Secuencia: ¿lejos?       → embestida para cortar distancia
```

### El Silbón

Su silbido suena cerca cuando está lejos y lejos cuando está cerca: el audio le
miente al jugador sobre la misma distancia que usa el árbol.

### Economía y progreso

- **Lochas:** se obtienen al matar. Cada descanso en un refugio cuenta como un día y
  les quita valor; vencer a un jefe frena la inflación en esa zona.
- **Muerte:** se dejan las lochas donde se cayó; un fantasma repite tus últimos pasos.
- **Refugios:** altares. Permiten subir de nivel.
- **Curación:** café, en cantidad limitada.
- **Bachaquero:** mercader que cambia lochas por objetos que no se devalúan. Sus
  precios suben cada vez que mueres.

### Apagones

Se va la luz en la zona y los enemigos cambian de rama del árbol: más agresivos
o guiados por el sonido.

## 5. Estructuras de datos

Todas salen de DeSiGNAR. No se usan contenedores de la STL para esto.

| Sistema | Estructura o algoritmo | Header |
|---|---|---|
| IA de enemigos | Árbol de comportamiento | propio, sobre `mtreenode.hpp` |
| Rotación de ataques | Cola | `queue.hpp` |
| Habilidades y zonas | Árbol n-ario | `mtreenode.hpp` |
| Combos, estados alterados | Listas | `list.hpp` |
| Objeto rápido (cíclico) | Lista recorrida en círculo | `list.hpp` |
| Fantasma, persecución por rastro | Lista de posiciones | `list.hpp` |
| Búfer de inputs | Cola | `queue.hpp` |
| Menús anidados | Pila | `stack.hpp` |
| Elección de ataque del jefe | Heap | `heap.hpp` |
| Base de objetos por ID | Tabla hash | `chainedhash.hpp` |
| Bestiario con autocompletado | Trie | `trie.hpp` |
| Lock-on por distancia | `insertion_sort` | `sort.hpp` |
| Inventario | `merge_sort` | `sort.hpp` |
| Récords por jefe | `quicksort` | `sort.hpp` |
| Botín, nivel, fase, tasa de cambio | `binary_search` | `sort.hpp` |

`insertion_sort` encaja en el lock-on porque hay pocos objetivos a la vez, y ordenarlos
permite comprobar la línea de vista empezando por el más cercano.
`merge_sort` se usa en el inventario si conserva el orden previo: **hay que
comprobar que la versión de DeSiGNAR sea estable.**

DeSiGNAR no trae árbol de comportamiento: el grupo programa sus nodos y su
lógica de decisión, pero los guarda en estructuras de DeSiGNAR.

## 6. Arquitectura

```
Godot (gráficos, físicas, sonido, escenas)
        │ GDExtension
Capa de juego (C++): Jugador, Jefe, Inventario, Menús
        │
Núcleo (C++ sin Godot): árbol de comportamiento, economía, botín
        │
DeSiGNAR (submódulo extern/DeSiGNAR)
```

Regla: el núcleo no incluye nada de Godot. Así se compila y prueba desde la
terminal con el ejecutable actual.

Estructura propuesta:

```
src/core/      lógica sin motor
src/game/      clases registradas en Godot
tests/         pruebas del núcleo
game/          proyecto Godot: escenas, modelos, audio
extern/        DeSiGNAR y godot-cpp
docs/
```

## 7. Herramientas

| Herramienta | Uso |
|---|---|
| C++17 | Toda la lógica |
| Godot 4 + GDExtension (`godot-cpp`) | Motor |
| DeSiGNAR | Estructuras de datos |
| CMake + Ninja | Compilación (ya configurada en el repo) |
| GCC (MSYS2 UCRT64 en Windows) | Compilador |
| Blender | Modelado y animación low poly |
| Git + GitHub | Versiones y compilación por plataforma |

Versiones: Godot 4.7.2 y `godot-cpp` 10.0.0, con la API 4.7.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Integrar DeSiGNAR con `godot-cpp` | Hacer una prueba mínima antes de nada más (fase 0) |
| DeSiGNAR lanza excepciones y `godot-cpp` las desactiva por defecto | Resuelto: activadas en CMake |
| Mezclar compiladores entre plataformas | Compilar en CI para cada sistema |
| Alcance demasiado grande | Jefe primero; todo lo demás es recortable |
| Animaciones 3D consumen más tiempo que el código | Modelos simples, recursos libres si hace falta |
| Un puntero mal manejado cierra el editor | Probar la lógica en el núcleo antes de llevarla a Godot |

## 9. Plan de desarrollo

Flujo: `main` ← `development` ← `feature/*`.

| Fase | Entregable | Hecho cuando |
|---|---|---|
| 0. Integración | Nodo C++ en Godot que usa una lista de DeSiGNAR | Corre en Linux y Windows |
| 1. Núcleo | Árbol de comportamiento y economía con pruebas | Las pruebas pasan en terminal |
| 2. Jugador | Movimiento, combate, búfer de inputs | Se pelea contra un muñeco |
| 3. El Silbón | Jefe con árbol y visor de depuración | Se le puede ganar y perder |
| 4. Sistemas | Inventario, habilidades, moneda, muerte | Se guardan y cambian la partida |
| 5. Contenido | Avenida, llano, dos enemigos, minijefes, apagones, audio | Se juega de principio a fin |
| 6. Cierre | Exportaciones, documento técnico, exposición | Ejecutables en cada plataforma |

Las fechas se asignan cuando esté el calendario de la materia.

## 10. Decisiones pendientes

1. **Integrantes y fechas de entrega.**
2. **Nombre del protagonista y minijefes de la avenida.**
3. **Modelo de la protagonista:** queda fuera del juego.

Decidido: todas las estructuras de datos salen de DeSiGNAR, con Godot 4
(GDExtension) como motor y CMake para compilar.
