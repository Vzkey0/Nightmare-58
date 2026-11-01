# Guía del proyecto: de clonar a hacer push

Sigue esta guía en orden la primera vez. Después, para el trabajo diario, solo
necesitas la sección [Trabajo diario](#5-trabajo-diario).

Antes de empezar debes haber aceptado la invitación al repositorio
`Vzkey0/Nightmare-58` en GitHub. Sin eso podrás descargar el proyecto, pero no
subir cambios.

## 1. Qué hay que instalar

### Lo que instalas tú

| Herramienta | Para qué sirve | Qué te permite hacer |
|---|---|---|
| Godot 4.7.2 | Motor y editor del juego | Abrir el proyecto, editar escenas y ejecutar el juego |
| Git | Control de versiones | Descargar el proyecto, guardar cambios y subirlos |
| GCC o Clang | Compilador de C++ | Convertir nuestro código en la librería que carga Godot |
| CMake | Organiza la compilación | Saber qué compilar y con qué dependencias |
| Ninja | Ejecuta la compilación | Compilar rápido y solo lo que cambió |
| Python 3 | Lo usa `godot-cpp` al compilar | Generar el código que conecta C++ con Godot |
| GitHub CLI (`gh`) | Inicia sesión en GitHub | Hacer `git push` sin configurar tokens a mano |
| Editor de código, como VS Code | Escribir C++ | Editar `src/` y `tests/` |
| Blender (solo quien haga modelos) | Modelado y animación | Crear modelos low poly |

**Usa exactamente Godot 4.7.2.** La extensión se compila para esa API, y una versión
distinta puede fallar o modificar archivos del proyecto.

Descárgalo aquí: <https://godotengine.org/download/archive/4.7.2-stable/>

### Lo que llega solo al clonar

| Dependencia | Dónde queda | Qué aporta |
|---|---|---|
| DeSiGNAR | `extern/DeSiGNAR` | Listas, árboles, heaps, hash y algoritmos de ordenamiento |
| `godot-cpp` | `extern/godot-cpp` | Permite escribir clases de Godot en C++ |

Son **submódulos**: el repositorio guarda un enlace a una versión exacta y Git las
descarga con `--recursive`. No se instalan aparte y no se modifican.

### Windows

1. Instala [MSYS2](https://www.msys2.org/).
2. Abre **MSYS2 UCRT64** desde el menú Inicio. Debe ser esa, no otra de las
   terminales de MSYS2.
3. Instala las herramientas:

   ```bash
   pacman -S --needed git mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-github-cli
   ```

En Windows, todos los comandos de esta guía se ejecutan en **MSYS2 UCRT64**.

### Linux (Ubuntu o Debian)

```bash
sudo apt update
```

```bash
sudo apt install -y build-essential cmake ninja-build git python3 gh
```

### macOS

```bash
xcode-select --install
```

```bash
brew install cmake ninja git python gh
```

## 2. Configurar Git (una sola vez)

Pon tu nombre y tu correo de GitHub. Aparecerán en tus commits:

```bash
git config --global user.name "Tu Nombre"
```

```bash
git config --global user.email "tu-correo@ejemplo.com"
```

Inicia sesión en GitHub. Elige **GitHub.com**, **HTTPS** y **Login with a web browser**:

```bash
gh auth login
```

Haz que Git use esa sesión al subir cambios:

```bash
gh auth setup-git
```

## 3. Clonar y compilar (una sola vez)

Clonar se hace **una vez por computadora**. Después solo se actualiza.

**No pongas el proyecto en OneDrive, Dropbox ni similares.** La sincronización
bloquea archivos mientras compilas. En Windows, el Escritorio suele estar dentro de
OneDrive, así que tampoco uses esa carpeta. Usa `C:\Nightmare-58`.

### Clonar

En Windows:

```bash
cd /c/
```

En Linux o macOS:

```bash
cd ~
```

En todos los sistemas:

```bash
git clone --recursive https://github.com/Vzkey0/Nightmare-58.git
```

```bash
cd Nightmare-58
```

No olvides `--recursive`: sin él, `extern/` queda vacío y no compila. Si ya clonaste
sin esa opción, ejecuta esto dentro del proyecto:

```bash
git submodule update --init --recursive
```

### Compilar

```bash
cmake -S . -B build -G Ninja
```

```bash
cmake --build build
```

```bash
ctest --test-dir build --output-on-failure
```

Qué hace cada comando:

1. `cmake -S . -B build -G Ninja` prepara la compilación en la carpeta `build/`.
2. `cmake --build build` compila. La primera vez tarda varios minutos porque también
   compila `godot-cpp`.
3. `ctest ...` ejecuta las pruebas. Debe decir `100% tests passed`.

Al terminar tendrás la librería en `game/bin/`:

| Sistema | Archivo |
|---|---|
| Windows | `nightmare58.windows.template_debug.x86_64.dll` |
| Linux | `nightmare58.linux.template_debug.x86_64.so` |
| macOS | Archivo `.dylib` de `nightmare58` |

### Compilar con Make

Ninja es la opción oficial y la que usan los checks de GitHub. El proyecto también
compila con Make, sin cambiar nada en el repositorio. Si ya tienes `build/` creada
con Ninja, bórrala antes: CMake no permite cambiar de generador sobre la misma carpeta.

En Windows, instala Make y prepara la compilación en **MSYS2 UCRT64**:

```bash
pacman -S --needed make
```

```bash
cmake -S . -B build -G "MSYS Makefiles"
```

En Linux, Make ya viene con `build-essential`:

```bash
cmake -S . -B build -G "Unix Makefiles"
```

Después, en ambos sistemas:

```bash
cmake --build build -j "$(nproc)"
```

```bash
ctest --test-dir build --output-on-failure
```

Sin `-j`, Make compila un archivo a la vez y la primera compilación tarda mucho más.

En Windows, el archivo debe llamarse `nightmare58.windows.template_debug.x86_64.dll`.
Si le falta `x86_64`, Godot no lo cargará: abre la terminal desde el menú Inicio o
desde VS Code, no desde otro Bash.

Probado en Windows. En Linux falta probarlo.

### Abrir en Godot

1. Abre Godot 4.7.2.
2. Pulsa **Importar** y selecciona `game/project.godot`.
3. Pulsa **Importar y editar**.
4. Pulsa F5.

Si todo salió bien, la salida de Godot muestra:

```text
DeSiGNAR OK: 3 elements
Exception caught: List is empty
```

## 4. Cómo está organizado

| Carpeta | Qué va ahí | Con qué se edita |
|---|---|---|
| `src/core/` | Lógica sin Godot, como la IA y la economía | Editor de código |
| `src/game/` | Clases C++ que aparecen como nodos en Godot | Editor de código |
| `tests/` | Pruebas de `src/core/` | Editor de código |
| `game/` | Escenas, modelos, audio y configuración de Godot | Godot y Blender |
| `docs/` | Diseño, convenciones y justificaciones | Editor de código |
| `extern/` | DeSiGNAR y `godot-cpp` | No se toca |

Regla clave: `src/core/` no incluye nada de Godot. Todo el juego va en C++; no se usa
GDScript.

Lee [Convenciones.md](Convenciones.md) antes de programar. Toda decisión sobre una
estructura de datos o un algoritmo se justifica en
[Justificaciones.md](Justificaciones.md).

## 5. Trabajo diario

### Ramas

```text
main          versión estable
development   donde se une el trabajo del equipo
feature/...   una rama por tarea
```

Nunca se trabaja directamente en `main` ni en `development`. Tu rama es tu espacio:
nadie ve esos cambios hasta que los subes y se mergean.

### Paso 1: actualizar antes de empezar

```bash
git switch development
```

```bash
git pull
```

```bash
git submodule update --init --recursive
```

```bash
cmake --build build
```

### Paso 2: crear tu rama

Usa un nombre corto que describa la tarea:

```bash
git switch -c feature/bufer-inputs
```

Una rama por tarea. Las ramas pequeñas se revisan mejor y generan menos conflictos.

### Paso 3: hacer los cambios

**Si cambias C++:**

1. Cierra Godot, para que no bloquee la librería.
2. Edita el código.
3. Compila y ejecuta las pruebas:

   ```bash
   cmake --build build
   ```

   ```bash
   ctest --test-dir build --output-on-failure
   ```

4. Abre Godot y pulsa F5.

Godot no ve los cambios de C++ hasta que compilas y lo vuelves a abrir.

**Si creas una clase para Godot:**

1. Crea el `.hpp` y el `.cpp` en la subcarpeta de `src/game/` que le toque (`enemies/`, `player/`, `weapons/`, `ui/` o `debug/`).
2. Agrega el `.cpp` a `add_library(nightmare58_ext ...)` en `CMakeLists.txt`.
3. Regístrala con `GDREGISTER_CLASS(TuClase)` en `src/game/register_types.cpp`.
4. Compila y abre Godot. La clase aparece en **Añadir nodo**.

**Si cambias lógica en `src/core/`:** agrega o actualiza su prueba en `tests/`.

**Si cambias una escena:** avisa al equipo. Las escenas `.tscn` generan conflictos
difíciles de resolver, así que solo una persona edita cada una a la vez.

### Paso 4: revisar antes de hacer commit

- [ ] Compila sin errores.
- [ ] `ctest` pasa todas las pruebas.
- [ ] El juego abre y lo que cambiaste funciona en Godot.
- [ ] Las decisiones nuevas tienen su comentario `J-000` y su ficha.
- [ ] Lo que corre cada frame tiene medición.
- [ ] `src/core/` sigue sin incluir nada de Godot.

### Paso 5: hacer commit

Mira qué cambió:

```bash
git status
```

```bash
git diff
```

Agrega solo los archivos de tu tarea:

```bash
git add src/core/bufer_inputs.hpp tests/test_core.cpp
```

Guarda el cambio con un mensaje en español e imperativo:

```bash
git commit -m "Agregar bufer de inputs"
```

El commit queda **solo en tu PC**. Nadie lo ve hasta hacer push.

**Qué se sube:** código, documentos, escenas, modelos, audio y los archivos `.uid` e
`.import` que crea Godot.

**Qué no se sube:** `build/`, `game/.godot/` ni las librerías compiladas. Git ya los
ignora.

### Paso 6: incorporar lo último del equipo

Antes de subir, trae lo nuevo de `development` a tu rama:

```bash
git switch development
```

```bash
git pull
```

```bash
git switch feature/bufer-inputs
```

```bash
git merge development
```

Si hay conflictos, mira la [sección 7](#7-resolver-conflictos). Después vuelve a
compilar y ejecutar las pruebas.

### Paso 7: hacer push

La primera vez que subes una rama:

```bash
git push -u origin feature/bufer-inputs
```

Las siguientes veces, en esa misma rama:

```bash
git push
```

### Paso 8: abrir el pull request

1. Entra en <https://github.com/Vzkey0/Nightmare-58>.
2. Pulsa **Compare & pull request**.
3. Comprueba que diga `base: development` y `compare: feature/bufer-inputs`.
4. Explica qué cambiaste y cómo lo probaste.
5. Pulsa **Create pull request**.

GitHub compila en Windows, Linux y macOS y ejecuta las pruebas. Eso comprueba que
compila, no que el juego funcione bien.

- **Check en rojo:** abre el detalle, corrige en tu rama y haz push de nuevo. El pull
  request se actualiza solo.
- **Checks en verde:** pide a un compañero que lo revise.
- **Listo para unir:** pulsa **Merge pull request**. Usa **Merge** o **Rebase**, nunca
  **Squash**, para conservar los commits de cada integrante.

Mientras el pull request esté abierto, cada `git push` a esa rama se agrega a él.

### Paso 9: después del merge

Vuelve al paso 1 para tu siguiente tarea. Tu cambio ya está en `development`. Puedes
borrar tu rama local:

```bash
git branch -d feature/bufer-inputs
```

## 6. Cómo les llegan los cambios a los demás

Los cambios no llegan solos:

1. Una persona hace `commit` y `push`.
2. Se aprueba y se mergea el pull request a `development`.
3. Los demás ejecutan los comandos del paso 1 en su computadora.

Después de actualizar siempre hay que compilar, porque las librerías no se suben a
GitHub. Si un compañero actualizó DeSiGNAR o `godot-cpp`, `git pull` no basta:
por eso el paso 1 incluye `git submodule update`.

## 7. Resolver conflictos

Hay un conflicto cuando dos personas cambian las mismas líneas. Git detiene el merge
y marca el archivo:

```text
<<<<<<< HEAD
tu versión
=======
la versión de development
>>>>>>> development
```

1. Abre el archivo y deja el código correcto.
2. Borra las líneas `<<<<<<<`, `=======` y `>>>>>>>`.
3. Marca el archivo como resuelto y termina el merge:

   ```bash
   git add ruta/del/archivo
   ```

   ```bash
   git commit
   ```

4. Compila y ejecuta las pruebas.

Para cancelar el merge y volver a como estabas:

```bash
git merge --abort
```

En una escena `.tscn`, no resuelvas a mano si no entiendes el cambio. Quédate con una
versión y rehaz el otro cambio en Godot.

## 8. Problemas comunes

| Problema | Causa | Solución |
|---|---|---|
| `Falta DeSiGNAR` o `Falta godot-cpp` | Clonaste sin `--recursive` | `git submodule update --init --recursive` |
| `cmake: command not found` | Terminal equivocada o falta instalarlo | En Windows, abre **MSYS2 UCRT64** |
| Error de `CMakeCache` al mover la carpeta | `build/` guarda rutas absolutas | Borra `build/` y compila de nuevo |
| No se puede escribir el `.dll` | Godot lo tiene abierto | Cierra Godot y compila de nuevo |
| `Cannot get class ...` en Godot | Falta compilar o registrar la clase | Compila y revisa `register_types.cpp` y `CMakeLists.txt` |
| La clase nueva no aparece en Godot | Godot sigue con la versión anterior | Ciérralo y ábrelo otra vez |
| `src refspec ... does not match any` | No has hecho commit o el nombre de la rama no coincide | Revisa con `git status` |
| `rejected` al hacer push | Tu rama no tiene lo último del remoto | `git pull` y luego `git push` |
| `Permission denied` o error 403 al hacer push | Falta la invitación o la sesión | Acepta la invitación y repite `gh auth login` |
| Commit en la rama equivocada | Olvidaste crear tu rama | Pide ayuda antes de seguir; no fuerces nada |

La advertencia `LF will be replaced by CRLF` es normal y no es un error.

## 9. Reglas que no se rompen

- No usar `git push --force` en ramas compartidas.
- No hacer commits directos en `main` ni en `development`.
- No editar nada dentro de `extern/`.
- No subir código que no compile.
- No usar contenedores de la STL en la lógica del juego.
- No guardar contraseñas ni tokens en el repositorio.

## 10. Resumen rápido

```bash
git switch development
```

```bash
git pull
```

```bash
git submodule update --init --recursive
```

```bash
git switch -c feature/mi-tarea
```

Haz tus cambios y compila:

```bash
cmake --build build
```

```bash
ctest --test-dir build --output-on-failure
```

Guarda y sube:

```bash
git add archivos-de-tu-tarea
```

```bash
git commit -m "Agregar mi tarea"
```

```bash
git push -u origin feature/mi-tarea
```

Por último, abre el pull request hacia `development` y mergéalo cuando esté en verde
y revisado.
