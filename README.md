# Nightmare 58

## Resumen

Pendiente: describir el proyecto cuando la idea esté aprobada.

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

## Compilar en Windows

1. Instala [MSYS2](https://www.msys2.org/).
2. Abre la terminal **MSYS2 UCRT64** e instala las herramientas:

   ```bash
   pacman -S --needed git mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja
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
sudo apt install build-essential cmake ninja-build git
git clone --recursive https://github.com/Vzkey0/Nightmare-58.git
cd Nightmare-58
cmake -S . -B build -G Ninja
cmake --build build
./build/Nightmare58
```

Si ya clonaste sin `--recursive`: `git submodule update --init`.

## Flujo de trabajo

`main` ← `development` ← `feature/*`. Cada característica se hace en su propia
rama `feature/nombre` salida de `development`. Nunca se hacen commits directos
sobre `main`.

## Créditos

Pendiente: integrantes del grupo.

Estructuras de datos: DeSiGNAR, de Alejandro J. Mujica (licencia MIT).
