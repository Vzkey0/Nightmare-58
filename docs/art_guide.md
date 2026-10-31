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
Están en pose A y ya tienen esqueleto, con los mismos 25 huesos en ambos para poder
compartir animaciones. Aún no tienen animaciones.

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
