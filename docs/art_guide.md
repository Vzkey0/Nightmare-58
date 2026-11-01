# Guía de arte

Referencia visual y flujo de modelos para todo el juego. Las imágenes están en
[art_references/](art_references/) y solo se usan como inspiración: ninguna entra
al juego ni se copia tal cual.

## Estilo

- **Facetado:** caras planas y visibles, con *flat shading*. Pocos polígonos bien
  puestos, no un modelo detallado y simplificado después.
- **Color antes que textura:** color plano por material o paleta en una imagen
  pequeña. Sin texturas fotográficas.
- **Siluetas legibles:** cada personaje se reconoce solo por su contorno.
- **Contraste de escala:** el jugador se ve pequeño frente a jefes y edificios.
- **Luz y ambiente:** la luz, la niebla y el cielo dan la atmósfera, no el detalle.

## Referencias

| Imagen | Qué tomar |
|---|---|
| [01](art_references/01_giant_creature_scale.webp) | Jefe gigante contra el jugador, ojos brillantes, atardecer azul y morado |
| [02](art_references/02_face_construction.webp) | Construcción de la cara por pasos, rasgos con muy pocas caras |
| [03](art_references/03_stylized_human.png) | Proporciones y cara simple del personaje humano |
| [04](art_references/04_hooded_silhouette.png) | Silueta fuerte, ropa con pliegues facetados, paleta limitada |
| [05](art_references/05_hooded_skeleton.png) | Capas de ropa, accesorios y un punto de luz como acento |
| [06](art_references/06_clean_landscape.png) | Terreno facetado limpio, reflejos simples en el agua |
| [07](art_references/07_overgrown_city_dusk.webp) | **Escenario apocalíptico:** ciudad tomada por plantas, cielo cálido |
| [08](art_references/08_overgrown_city_storm.webp) | **Escenario apocalíptico:** tormenta, tranvía abandonado, animales, charcos |
| [09](art_references/09_colorful_house.webp) | Follaje hecho de triángulos sueltos, color saturado |
| [10](art_references/10_ruins_jungle.webp) | Ruinas con vegetación, punto de color rojo que destaca al personaje |
| [11](art_references/11_desert_chase.png) | Enemigo enorme y expresivo, composición dinámica |
| [12](art_references/12_stylized_floating_map.webp) | Caminos que guían al jugador por la zona, monumentos como puntos de referencia |

La 05 trae la marca de un paquete hecho con IA, y varias son de juegos o
paquetes comerciales: por eso no se reutilizan.

## Protagonista

Hay dos protagonistas con diseños distintos.

**Hombre:** venezolano, de contextura atlética y piel morena. Pelo corto y rizado con
puntas claras, cejas gruesas, barba corta, argolla en la nariz y expansores. Lleva la
chaqueta tricolor con ocho estrellas y un parche de la bandera, pantalón negro y
botines negros de una sola pieza, lisos por detrás, con costura amarilla, franja
gris con ojales, lengüeta y tirador. La cámara del juego va detrás de él, así que
la espalda lleva también estrellas y un 58 estilo camiseta, por el +58 del título. Es el
personaje con más detalle del juego.

**Mujer:** pelo negro con flequillo y dos trenzas facetadas con anillo de metal, cara
en sombra, camiseta negra corta con estampado de cara con colmillos, cinturón con
hebilla, pantalón cargo ancho y rasgado, y botas negras.

[build_protagonist.py](../art/characters/build_protagonist.py) genera ambos, guarda
`protagonist.blend` y exporta `protagonist_male.glb` y `protagonist_female.glb`.
Están en pose A y ya tienen esqueleto, con los mismos 27 huesos en ambos para poder
compartir animaciones. `root` va en el suelo y lleva el avance de esquivas y golpes;
`weapon` es el punto de agarre del arma. El hombre suma cuatro huesos `hem_*` para el borde de
la chaqueta, sin claves en los clips.

## Animaciones

[animate_protagonist.py](../art/characters/animate_protagonist.py) genera los clips y
exporta `protagonist_male.glb` con ellos. Hay que correrlo después de
`build_protagonist.py`, porque ese script exporta el modelo sin animaciones:

```bash
blender --background art/characters/protagonist.blend --python art/characters/animate_protagonist.py
```

Las poses clave definen pelvis, columna, pies y palo, y la cinemática inversa resuelve
piernas y brazos en cada cuadro. Así los pies no patinan y las dos manos siguen en el
palo. Se escriben en cuadros a 30 fps y se hornean a 60. El `.import` del modelo debe
quedar con `animation/fps=60`, o Godot las reduce a 30.

| Clip | Duración | Interrupción | Uso |
|---|---|---|---|
| `idle` | 5 s, en bucle | Siempre | Reposo a una mano, con el palo a un lado |
| `walk` | 0,8 s, en bucle | Siempre | Caminata a 1,9 m/s con el stick a media carrera |
| `run` | 0,6 s, en bucle | Siempre | Carrera a 4,6 m/s |
| `sprint` | 0,5 s, en bucle | Siempre | Esprint a 6,8 m/s al mantener Shift |
| `run_start` | 0,33 s | Soltar la dirección | Primeros dos pasos; termina donde `run` apoya el pie izquierdo |
| `run_stop` | 0,5 s | Volver a moverse | Frenada con el pie derecho clavado y el palo siguiendo de largo |
| `run_turn` | 0,43 s | Una acción | Giro brusco al invertir la dirección corriendo |
| `jump` | 0,33 s | Golpe aéreo 0,12 s | Despegue sin agacharse, para responder al instante |
| `fall` | 0,8 s, en bucle | Siempre | Caída |
| `land` | 0,4 s | Moverse o cualquier acción | Amortigua el aterrizaje |
| `attack_air` | 0,7 s | Termina el golpe aunque toque el suelo | Golpe por encima de la cabeza, con las rodillas recogidas |
| `dodge_forward` | 0,77 s, avanza 3,2 m | Acción 0,5 s, moverse 0,57 s | Voltereta hacia delante con el palo cruzado sobre el eje de giro |
| `attack_light_1` | 0,8 s, avanza 0,85 m | Esquiva 0,37 s, acción 0,45 s, moverse 0,55 s | Combo 1: corte diagonal rápido con zancada |
| `attack_light_2` | 0,87 s, avanza 0,75 m | Esquiva 0,36 s, acción 0,5 s, moverse 0,6 s | Combo 2: barrido a largo completo, la mano izquierda suelta y el palo corre por la derecha |
| `attack_light_3` | 1,33 s, avanza 1,15 m | Esquiva 0,55 s, acción 0,85 s, moverse 0,95 s | Combo 3: salto con giro completo y el palo girando sobre la cabeza, y clavado al suelo a dos manos |
| `attack_roll` | 0,8 s, avanza 1,1 m | Esquiva 0,33 s, acción 0,5 s, moverse 0,6 s | Estocada a una mano al salir de la voltereta |
| `attack_run` | 1 s, avanza 2,35 m | Esquiva 0,4 s, acción 0,62 s, moverse 0,72 s | Atacar esprintando: golpe ascendente a dos manos que aprovecha la velocidad |

**Giro de cuerpo:** los canales `tumble` y `spin` giran todo el cuerpo alrededor de un punto
sobre la raíz, y `lift` lo separa del suelo. Las poses se escriben como si no girara, y
`feet_free` decide si los pies giran con el cuerpo (1) o siguen en el suelo (0). El palo mide
1,6 m: en una voltereta solo cabe sobre el eje de giro, sin atravesar el suelo.

**Combo:** pulsar ataque durante un golpe guarda el siguiente, y tras el tercero vuelve al
primero. Dejar terminar el golpe o moverse después de su corte lo reinicia. Esquivar interrumpe
desde que termina el barrido y no espera a los ataques ya pulsados. La voltereta conserva el
sitio en el combo: un ataque pulsado durante ella es `attack_roll`, y el siguiente sigue con el
paso que tocaba. Cada golpe arranca en la pose donde el anterior permite encadenar (`AFTER_CUT`,
`AFTER_SWEEP` y `AFTER_ROLL` en `animate_protagonist.py`): si cambia esa pose o el tiempo de
`next_action`, hay que actualizarlas.

**Atracción al objetivo:** al empezar un golpe, el personaje se orienta hacia el objetivo más
cercano del grupo `targets` a menos de 4,5 m y 75° de la dirección pedida. También escala el
avance del clip entre 0,25 y 1,6 veces para terminar a 1,3 m. Todo enemigo debe entrar a ese grupo.

**Efectos:** `WeaponTrail` dibuja la estela del palo durante el barrido y el giro del tercer
golpe. El nodo `Dust` de `player.tscn` levanta polvo al rodar, aterrizar, frenar y clavar el palo.
El clavado añade temblor y un empujón de cámara.

**Chaqueta:** `HemSprings` en `player.tscn` mueve el borde con los resortes nativos de Godot.
Trabaja en el espacio del nodo `Model`: en coordenadas del mundo, cada giro del personaje arrastra
todo el borde. Rigidez 4 y arrastre 0,6 dan unos 30° de pico en carrera y hasta 70° un instante en la voltereta y el giro; `WaistCollision` evita que entre
al cuerpo, y con un radio mayor empuja el frente al inclinarse.

**Sonido:** los sonidos del jugador están en `Sounds` en `player.tscn`, con tono aleatorio. Solo
se usa audio CC0, con su origen en [CREDITS.md](../game/audio/CREDITS.md).

**Reglas tomadas de los souls-like y de animación de juegos:**

- **Ataques por fases:** pose de apertura legible, golpe más rápido de lo físico, pose
  final sostenida y regreso lento, como
  [el análisis de ataques de Dark Souls 3](https://www.gamedeveloper.com/game-platforms/anatomy-of-an-enemy-attack-in-dark-souls-3).
  Ese análisis pide al menos 340 ms entre la señal y el golpe en ataques de enemigos: es
  la regla a seguir en los jefes.
- **Esquiva:** responde casi al instante y su costo está en la recuperación, no en el
  arranque. Se empieza a mover en menos de 0,1 s. El giro dura como los 14 cuadros a 30 fps
  que [da la wiki de Elden Ring](https://eldenring.wiki.gg/wiki/Invincibility_Frames).
- **Carrera:** contacto, bajada, impulso y vuelo, según
  [las poses clave de AnimSchool](https://blog.animschool.edu/?p=634). El pie apoyado
  retrocede a la velocidad exacta de la carrera; si se cambia `RUN_SPEED` o la velocidad
  del esprint, hay que cambiar `run_speed` o `SPRINT_SPEED` en `PlayerController`.
- **Seguimiento:** el pecho, la cabeza y las manos llegan unos cuadros después de la
  pelvis, y las curvas no se pasan de largo para que un pie fijo siga fijo.
- **Cámara detrás:** el arma debe verse desde atrás en reposo.

**Pendiente:** esquivas hacia atrás y a los lados, que hacen falta con el fijado de objetivo,
e invulnerabilidad de la voltereta, cuando algo ataque al jugador. La mujer aún no tiene clips,
y el palo es provisional: cambiar su malla no afecta a los clips.

## Armas

**Regla para todas las armas: pega el arma entera.** Si se ve que el arma toca al enemigo
durante el golpe, el golpe cuenta, sea con la punta, el centro o el mango.

- **Forma de golpe:** el nodo `Hitbox` de `player.tscn` cubre la malla del arma de punta a
  punta. Va en el hueso `weapon`, así sigue la animación. Se mide contra la malla real,
  no a ojo: el palo va de -0,55 a 1,05 m sobre el eje Y del hueso, así que su cápsula mide
  1,6 m y está centrada en 0,25 m. Su radio de 0,06 m es mayor que el del palo a propósito,
  para perdonar un poco.
- **Ventana de golpe:** `hit_start` y `hit_end` en `player_actions.cpp` cubren todo el
  barrido, desde que el arma deja la pose alzada hasta que se detiene. No cuentan la
  preparación ni la pose final sostenida.
- **Un golpe por objetivo:** cada acción daña una vez a cada objetivo. Una acción nueva
  vuelve a dañar.
- **Al cambiar un arma o agregar un ataque:** hay que actualizar la cápsula o la ventana, y
  comprobar con el dummy en varias posiciones que cada contacto del barrido registra daño.
- **Límite conocido:** la forma se consulta 60 veces por segundo sin barrer entre ticks, y
  la punta del palo avanza hasta unos 0,4 m por tick. Un objetivo más delgado que eso
  podría saltarse; en ese caso hay que comprobar posiciones intermedias.

## Escenario 1: avenida de Caracas

Avenida abandonada bajo tormenta, basada en las referencias 07 y 08: bloques de losas
con balcones, casas de ladrillo con escaleras, comercios cerrados, hiedra densa,
autobús y carros abandonados, postes con cables caídos, charcos, escombros en ambos
extremos, torre escalonada y el Ávila al fondo.

[build_avenue.py](../art/environments/build_avenue.py) la genera, guarda
`avenue.blend` y exporta `avenue.glb`. Los objetos terminados en `-colonly` son las
colisiones. La escena [avenue.tscn](../game/scenes/avenue.tscn) añade cielo, niebla,
luz de tormenta, reflejos y lluvia.

**Optimización de escenarios:**

- El color va en los vértices, con cinco materiales para todo el mapa.
- La vegetación se hace con láminas continuas y domos, no con objetos sueltos.
- Se borran las caras que quedan dentro de sólidos o de espaldas a toda la zona
  jugable. Por eso el mapa se ve incompleto desde fuera o desde arriba: es a propósito.
  Si el jugador va a poder subir a un sitio, hay que ampliar `PLAY_CORNERS`.
- Las capas largas se parten por tramos para que Godot omita lo que no está en cámara.

## Presupuesto inicial

Son valores de partida; se ajustan si el juego los necesita.

| Tipo | Triángulos |
|---|---|
| Personaje principal | 3.000 a 6.000 |
| Enemigo común | 2.000 a 4.000 |
| Jefe | 5.000 a 10.000 |
| Objeto pequeño | 50 a 500 |
| Edificio | 200 a 2.000 |

## Flujo Blender → Godot

Se usa Blender 5.2 y glTF binario (`.glb`), el formato mejor soportado por Godot.
Quien vaya a modelar aplica la configuración del proyecto una vez:

```bash
blender --background --python art/setup_blender.py
```

Deja metros como unidad, colores sin AgX para que coincidan con Godot, el contador
de triángulos visible, autoguardado cada 5 minutos, escena inicial vacía y la GPU
activa en Cycles. Reemplaza la escena inicial que tengas guardada.

1. El archivo editable va en `art/<tipo>/<nombre>.blend`.
2. Se exporta a `game/models/<tipo>/<nombre>.glb` con *File > Export > glTF 2.0*,
   formato GLB y *Apply Modifiers* activo.
3. Godot importa el `.glb` solo y se usa desde las escenas.

Los `.blend` quedan fuera de `game/` para que Godot no intente importarlos y nadie
del grupo necesite Blender solo para abrir el proyecto.

**Reglas:**

- Escala real: 1 unidad de Blender es 1 metro; el personaje mide cerca de 1,75 m.
- Aplicar escala y rotación antes de exportar (`Ctrl+A`).
- El personaje mira hacia `-Y` en Blender y sus pies quedan en el origen.
- Nombres en inglés y `snake_case`, también objetos, materiales y huesos.
