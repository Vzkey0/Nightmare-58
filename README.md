# Nightmare 58

## Resumen

Nightmare 58 es un souls-like 3D low poly ambientado en una Venezuela distópica
entre 2015 y 2018. El protagonista recorre un país golpeado por los apagones, la
escasez y la hiperinflación, y se enfrenta a leyendas urbanas venezolanas como
El Silbón. El nombre viene del +58, el código telefónico de Venezuela.

Es el proyecto de Programación 3 (Estructuras de Datos): las estructuras de
DeSiGNAR sostienen los sistemas del juego, como la IA de los enemigos, el árbol
de habilidades y el inventario. Está escrito en C++ con Godot 4 y apunta a Linux,
Windows y macOS.

El diseño completo está en [docs/PDD.md](docs/PDD.md).

## DeSiGNAR

Todas las estructuras de datos del proyecto salen de
[DeSiGNAR](https://r3mmurd.github.io/DeSiGNAR/) (C++17). Está incluida como
submódulo de git en `extern/DeSiGNAR`, así que no hay que instalarla aparte.

- Los headers se incluyen directo: `#include <list.hpp>`, `#include <avltree.hpp>`.
- Todo vive en el namespace `Designar`, por ejemplo `Designar::SLList<int>`.
- No usar contenedores de la STL (`std::vector`, `std::map`, ...) para las
  estructuras del proyecto: hay que usar su equivalente de DeSiGNAR.
- Para actualizarla a la última versión:
  `git submodule update --remote extern/DeSiGNAR`.

| Necesito | Header |
|---|---|
| Listas, pilas, colas | `list.hpp`, `stack.hpp`, `queue.hpp` |
| Arreglos | `array.hpp` |
| Mapas y conjuntos | `map.hpp`, `set.hpp` |
| Árboles balanceados | `avltree.hpp`, `rbtree.hpp` |
| Heaps | `heap.hpp`, `fibonacciheap.hpp` |
| Tablas hash | `chainedhash.hpp`, `openhash.hpp` |
| Grafos | `graph.hpp`, `graphalgorithms.hpp` |

## Requisitos

- Compilador C++17: GCC 9 o superior
- CMake 3.20 o superior
- Ninja (o make)
- Git
- Python 3 (lo usa `godot-cpp` al compilar)
- [Godot 4.7.2](https://godotengine.org/download/archive/4.7.2-stable/), la misma versión para todos

## Compilar en Windows

1. Instala [MSYS2](https://www.msys2.org/).
2. Abre la terminal **MSYS2 UCRT64** e instala las herramientas:

   ```bash
   pacman -S --needed git mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-python
   ```

3. En esa misma terminal, clona el repositorio **con** `--recursive` (sin eso
   no se descarga DeSiGNAR) y compila:

   ```bash
   git clone --recursive https://github.com/Vzkey0/Nightmare-58.git
   cd Nightmare-58
   cmake -S . -B build -G Ninja
   cmake --build build
   ./build/Nightmare58.exe
   ```

## Compilar en Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install build-essential cmake ninja-build git python3
git clone --recursive https://github.com/Vzkey0/Nightmare-58.git
cd Nightmare-58
cmake -S . -B build -G Ninja
cmake --build build
./build/Nightmare58
```

Si ya clonaste sin `--recursive`: `git submodule update --init --recursive`.

## Probar y abrir el juego

La primera compilación tarda varios minutos porque también compila `godot-cpp`.

```bash
ctest --test-dir build --output-on-failure
```

Después abre `game/project.godot` con Godot y pulsa F5. Cada cambio en C++ requiere
volver a compilar y reiniciar el editor.

## Estructura

| Carpeta | Contenido |
|---|---|
| `src/core/` | Lógica sin Godot: se prueba desde la terminal |
| `src/game/` | Clases C++ registradas en Godot |
| `tests/` | Pruebas de `src/core/` |
| `game/` | Proyecto de Godot: escenas, modelos y audio |
| `extern/` | DeSiGNAR y `godot-cpp` |
| `docs/` | PDD y documento técnico |

## Flujo de trabajo

`main` ← `development` ← `feature/*`. Cada característica se hace en su propia
rama `feature/nombre` salida de `development`. Nunca se hacen commits directos
sobre `main`: los cambios llegan por pull request, y GitHub Actions debe compilar y
pasar las pruebas. Al fusionar usen **Merge** o **Rebase**, no **Squash**, para
conservar los commits de cada integrante.

## Créditos

- Juan Daniel Mendoza Sanchez
- Juan Enrique Uzcategui Zambrano
- Jeison David Hernandez Peraza

Estructuras de datos: DeSiGNAR, de Alejandro J. Mujica (licencia MIT).
