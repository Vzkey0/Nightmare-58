# Nightmare 58: Project Design & Development (PDD)

Estado: borrador. Las decisiones sin cerrar están en [Decisiones pendientes](#10-decisiones-pendientes).

## 1. Visión

Souls-like 3D low poly ambientado en una Venezuela distópica, 2015-2018. Un
emigrante vuelve a buscar a su madre y recorre un país golpeado por apagones,
escasez, hiperinflación y un terremoto que dejó las ciudades vacías, donde la pérdida
de la alegría despertó a las leyendas urbanas venezolanas. La historia completa está
en [lore.md](lore.md).

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

- Capítulo 1 pulido: apertura, avenida, selva y llano
- Siete tipos de enemigos con cuatro comportamientos, y minijefes
- Un jefe completo: El Silbón, en el llano
- Combate, loot, inventario, árbol de habilidades y moneda con inflación
- Modo de depuración del árbol de decisiones

La entrega de la materia es solo el capítulo 1. El juego no termina ahí: el proyecto
continúa después con los capítulos siguientes.

**Duración:** unos 25 minutos hasta El Silbón, y unos 7 de pelea si no se muere.

| Zona | Tiempo | Enemigos | Cierre |
|---|---|---|---|
| Avenida | 12 min | Esqueleto, rata gigante, perro | Minijefe: perro enorme, y capilla |
| Selva | 10 min | Perro, bruja, oso | Minijefe: oso grande |
| Llano | 3 min + 7 de pelea | Casi ninguno | El Silbón, en tres fases |

**Queda fuera de esta entrega, salvo que sobre tiempo:** más jefes (La Sayona y otras
leyendas), árbol de diálogo, doble machete, Florentino y el Diablo. El final es único:
no hay finales múltiples.

## 4. Mecánicas

### Combate

Ataque ligero y pesado, esquiva y fijado de objetivo, con barra de resistencia. Los botones presionados durante una animación se guardan y se
ejecutan al terminar. El arma principal es el machete.

### Enemigos

| Comportamiento | Enemigos | Esqueleto de animación |
|---|---|---|
| Cuerpo a cuerpo | Esqueleto | Humano |
| Jauría: rápidos y por los lados | Perro, perro esquelético, rata gigante | Cuadrúpedo |
| A distancia: mantiene lejanía | Bruja | Humano |
| Pesado: lento, golpes fuertes | Oso, demonio | Cuadrúpedo y humano |

El perro esquelético y el demonio solo salen durante los apagones. Un enemigo muerto
sigue muerto hasta que el jugador descanse o muera. El diseño de cada enemigo se
define al momento de hacerlo.

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

- **Lochas:** se obtienen al matar. Cada descanso en una capilla cuenta como un día y
  les quita valor; vencer a un jefe frena la inflación en esa zona.
- **Muerte:** se dejan las lochas donde se cayó, y hay que volver por ellas. Si se muere
  otra vez antes de recuperarlas, se pierden.
- **Capillas:** son los puntos de control. Permiten descansar y subir de nivel.
- **Curación:** café, en cantidad limitada. Se recarga en las capillas.
- **Bachaquero:** mercader que cambia lochas por objetos que no se devalúan. Sus
  precios suben cada vez que mueres.

### Estadísticas

Se suben en la capilla, con cinco niveles cada una, y se pagan con lochas. Los valores
son iniciales y se ajustan jugando.

| Mejora | Por nivel |
|---|---|
| Vida máxima | +10 % |
| Recuperación de stamina | +10 % |
| Regeneración de vida | +0,5 de vida por segundo |
| Velocidad al correr | +4 % |
| Cadencia de ataque | +5 % |
| Poder de ataque | +8 % |

### Machete

Se mejora con el bachaquero, sobre el árbol de habilidades:

```
Machete
├─ Filo → Filo II → Filo III
├─ Grasa → Fuego / Hielo
└─ Técnica → Lanzar machete / Modo Arrechera
```

- **Grasas:** duran 60 s. El fuego quema con el tiempo y el hielo frena al enemigo.
- **Lanzar machete:** va y vuelve; mientras tanto no se puede atacar.
- **Modo Arrechera:** el modo ira. Su barra se llena al pelear; al activarla se pega
  más fuerte unos 12 s, pero también se recibe más daño.

### Objetos

| Tipo | Objetos |
|---|---|
| Atuendos | Uniforme militar (más defensa), uniforme de Bolívar (más ataque), gorra (más fuerza) |
| Consumibles | Café, grasas, vela de retorno |
| Coleccionables | Vinilo de gaita, cromo de béisbol, ficha de dominó, foto familiar |

- **Atuendos:** se ven puestos en el personaje. Se empieza por la gorra, porque los
  uniformes hay que modelarlos sobre el cuerpo.
- **Coleccionables:** no se devalúan y el bachaquero los paga mejor con la inflación.
  Guardarlos es una decisión económica real.
- **Vela de retorno:** devuelve a la última capilla. Con 25 minutos de juego no hace
  falta otro teletransporte.

### Apagones

Se va la luz en la zona y los enemigos cambian de rama del árbol: más agresivos
o guiados por el sonido. Además salen enemigos especiales.

## 5. Estructuras de datos

Todas salen de DeSiGNAR. No se usan contenedores de la STL para esto.

| Sistema | Estructura o algoritmo | Header |
|---|---|---|
| IA de enemigos | Árbol de comportamiento | propio, sobre `mtreenode.hpp` |
| Rotación de ataques | Cola | `queue.hpp` |
| Habilidades y zonas | Árbol n-ario | `mtreenode.hpp` |
| Combos, estados alterados | Listas | `list.hpp` |
| Objeto rápido (cíclico) | Cola fija | `queue.hpp` |
| Persecución por rastro | Lista de posiciones | `list.hpp` |
| Objetos recogidos | Conjunto de bits | `bitset.hpp` |
| Búfer de inputs | Cola | `queue.hpp` |
| Menús anidados | Pila fija | `stack.hpp` |
| Elección de ataque del jefe | Heap | `heap.hpp` |
| Base de objetos por ID | Tabla hash y arreglo | `map.hpp`, `array.hpp` |
| Bestiario con autocompletado | Trie | `trie.hpp` |
| Lock-on por distancia | `insertion_sort` | `sort.hpp` |
| Inventario | `merge_sort` | `sort.hpp` |
| Récords por jefe | `quicksort` | `sort.hpp` |
| Botín | Pesos acumulados y recorrido lineal | `array.hpp` |
| Nivel, fase, tasa de cambio | `binary_search` | `sort.hpp` |

`insertion_sort` encaja en el lock-on porque hay pocos objetivos a la vez, y ordenarlos
permite comprobar la línea de vista empezando por el más cercano.
`merge_sort` se usa en el inventario porque conserva el orden previo: una prueba
comprueba que la versión de DeSiGNAR es estable.

Las fichas J-010 y J-013 explican por qué el botín y el objeto rápido cambiaron
respecto de la propuesta inicial.

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
| 3. Cierre del esqueleto | Prueba real, ajustes, malla de navegación | Se pelea bien y rodean carros |
| 4. Base de progreso | Objetos, inventario, loot, lochas, muerte, capillas, guardado | Mueres, recuperas lo tuyo y la partida se guarda |
| 5. Machete y bachaquero | Tienda, inflación, árbol, grasas, lanzar, Arrechera, atuendos | Una mejora cambia cómo peleas |
| 6. Apertura | Cinemática, tutorial, edificio, padre | Se juega desde el carro hasta la capilla |
| 7. Avenida completa | Rata, perro, minijefe, apagones, catedral | La zona dura 12 minutos |
| 8. Selva | Escenario, bruja, oso, minijefe, pistas | Se llega hasta el llano |
| 9. El Silbón | Llano, jefe, silbido, visor de depuración | Se le puede ganar y perder |
| 10. Cierre | Pulido, exportaciones, documento técnico, exposición | Ejecutables en cada plataforma |

De la fase 3 solo falta la malla de navegación: los esqueletos ya se probaron jugando.

El modelado y la programación se trabajan por separado: los sistemas se hacen con
bloques provisionales y el arte llega en su propia tarea.

Las fechas se asignan cuando esté el calendario de la materia.

## 10. Decisiones pendientes

1. **Integrantes y fecha exacta de entrega.** Quedan más de dos meses.
2. **Nombre del amigo que maneja el carro.** El del protagonista lo elige el jugador
   en el menú de inicio.
3. **Modelo de la protagonista:** queda fuera del juego.

Decidido: todas las estructuras de datos salen de DeSiGNAR, con Godot 4
(GDExtension) como motor y CMake para compilar.
