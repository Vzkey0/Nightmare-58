# Guía de arte

Referencia visual y flujo de modelos para todo el juego. Las imágenes están en
[art_references/](art_references/) y solo se usan como inspiración: ninguna entra
al juego ni se copia tal cual.

## Estilo

- **Facetado:** caras planas y visibles, con *flat shading*. Pocos polígonos bien
  puestos, no un modelo detallado y simplificado después. La excepción es el protagonista,
  con sombreado suave y textura pintada, para que destaque contra el mundo facetado.
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

Hay un protagonista

**Hombre:** venezolano, de contextura atlética y piel morena, con el nivel de acabado de Link
en Breath of the Wild. Pelo oscuro en mechones ondulados y puntas claras, cejas gruesas, ojos
grandes, barba corta, argolla en la nariz y expansores. Lleva abierta la chaqueta tricolor hasta
media pierna, con ocho estrellas y un parche de la bandera, franela blanca, cinturón, pantalón
negro y botines negros de una sola pieza, lisos por detrás, con costura amarilla, franja gris con
ojales, lengüeta y tirador. La cámara del juego va detrás de él, así que la espalda lleva
también estrellas y un 58 estilo camiseta, por el +58 del título. Es el personaje con más
detalle del juego.


[build_protagonist.py](../art/characters/build_protagonist.py) genera ambos, guarda
`protagonist.blend` y exporta `protagonist_male.glb` y `protagonist_female.glb`.
Están en pose A y ya tienen esqueleto, con los mismos 27 huesos en ambos para poder
compartir animaciones. `root` va en el suelo y lleva el avance de esquivas y golpes;
`weapon` es el punto de agarre del arma. El hombre suma 30 huesos sin claves en los clips:
`jacket_front`, `jacket_side` y `jacket_back` con tres por cadena, y `hair_front`, `hair_side` y
`hair_back` con dos, todos a cada lado.

[paint_protagonist.py](../art/characters/paint_protagonist.py) despliega las UV, hornea posición,
normales y oclusión, y pinta una sola textura de 2048 px por posición en el cuerpo, así las costuras
de la UV no se notan. Hay que correrlo después de `build_protagonist.py`:

```bash
blender --background art/characters/protagonist.blend --python art/characters/paint_protagonist.py
```

Las sombras van en bandas rotas con ruido, para que parezca gouache y no un render. La cara se
pinta completa, sin ojos ni cejas en la malla. La oclusión se hornea con los brazos abiertos, porque
en pose A dejaría una mancha en el pecho.

## Esqueleto

Enemigo común de la avenida. Cabeza grande, cuerpo fino y encorvado, brazos largos y un machete
gastado en la mano derecha, sin ropa ni armadura. Tomado de las proporciones de una figura estilizada, pero
con caras planas: ceño caído hacia la nariz, cuencas talladas de verdad, grieta en el cráneo,
dientes sueltos y una costilla rota. Los ojos son ámbar para no confundirse con la vida del HUD.

[build_skeleton.py](../art/characters/build_skeleton.py) genera el modelo en pose A, guarda
`skeleton.blend` y exporta `skeleton.glb`, con 3.923 triángulos. Usa los nombres de huesos de la
protagonista más `jaw`, sin `hem_*`. Cada pieza sigue a un solo hueso: nada se dobla, como en un
esqueleto real. El machete es el de [machete.py](../art/props/machete.py), va pesado al hueso
`weapon` y mide 0,72 m de hoja.

[animate_skeleton.py](../art/characters/animate_skeleton.py) genera los clips con el mismo
resolvedor que la protagonista, y hay que correrlo después de `build_skeleton.py`:

```bash
blender --background art/characters/skeleton.blend --python art/characters/animate_skeleton.py
```

| Clip | Duración | Golpe | Uso |
|---|---|---|---|
| `idle` | 4 s, en bucle | | Encorvado, con la mandíbula chasqueando de vez en cuando |
| `walk` | 1 s, en bucle | | Paso torpe a 1,4 m/s |
| `run` | 0,67 s, en bucle | | Persecución a 3,8 m/s: encorvado, zancadas largas y el machete en alto |
| `strafe_left`, `strafe_right`, `walk_back` | 0,8 s, en bucle | | Rodear al jugador a 1,1 m/s, mirándolo |
| `attack_chop` | 1,47 s, avanza 0,42 m | 0,63 a 0,77 s | Alza el machete tras el cráneo y corta en diagonal |
| `attack_sweep` | 1,33 s, avanza 0,34 m | 0,53 a 0,67 s | Revés abierto a la altura de la cintura |
| `attack_lunge` | 1,87 s, avanza 2,4 m | 0,9 a 1,03 s | Embestida: se encoge, salta y cae cortando |
| `hurt` | 0,5 s | | El cráneo salta hacia atrás y la mandíbula cuelga |
| `death` | 2,2 s | | Cada hueso se suelta y cae por su cuenta; el cráneo acaba junto al montón |

Todos los ataques dejan más de 0,34 s entre la señal y el golpe, y los ojos brillan más durante esa
señal. En `death` los huesos caen sin seguir a su padre, por lo que el clip mueve todos los huesos; se
queda en el último cuadro, y el esqueleto queda así hasta que el jugador descansa o muere.

**IA:** [`MeleeEnemy`](../src/game/enemies/melee_enemy.cpp), con el perfil de [`SkeletonEnemy`](../src/game/enemies/skeleton_enemy.cpp), reúne lo que el enemigo sabe, el árbol elige
qué hacer y `EnemyActions` lo ejecuta. Un paseo se puede cambiar, un ataque no: un golpe solo lo
interrumpe antes del barrido, y un combo aturde una vez cada 2,5 s. Deja de girar poco antes del golpe,
para que esquivar tarde funcione.

**Varios a la vez:** se puede poner cualquier cantidad en una escena sin configurar nada. Solo comparten
`AttackTurns`, que está en el jugador: atacan dos como máximo, con 0,7 s entre ataques, y los demás
rodean al jugador, cada uno a su propia distancia. Al morir el jugador, todos vuelven a su sitio.

**Rutas:** al acercarse o buscar siguen la malla de `game/navigation/avenue.tres`, así que rodean los
carros. Si cambian las colisiones de la avenida, hay que volver a hornearla con el botón Bake del nodo
`Navigation`. Lee la geometría del grupo `navigation`. Al rodear a un jugador cercano caminan directo.

**Sin haber visto al jugador:** pasean alrededor de su sitio, a menos de 4 m, con pausas de 2 a 5 s, así
que miran hacia todos lados y pueden descubrirlo desde cualquier dirección. Al verlo corren hacia él
y caminan solo en los últimos 4 m. Corren más lento que el jugador, que todavía puede escapar.

### Rata gigante y perro

[build_rat.py](../art/characters/build_rat.py) y [build_dog.py](../art/characters/build_dog.py) generan
cada modelo ya con esqueleto. Los huesos son `root`, `hips`, `spine`, `chest`, `neck`, `head`, `jaw`,
`tail_*` y, por pata, `upper_`, `lower_`, `foot_` y `toes_`, más `front_l`, `front_r`, `hind_l` o
`hind_r`. Cada tramo de la malla se marca con los huesos que lo pueden mover, y cada vértice sigue a
los dos más cercanos de esa lista. Las ayudas compartidas están en
[beast_tools.py](../art/characters/beast_tools.py).

[animate_rat.py](../art/characters/animate_rat.py) y [animate_dog.py](../art/characters/animate_dog.py)
generan los clips y exportan `rat.glb` y `dog.glb`. Usan
[beast_anim.py](../art/characters/beast_anim.py), que resuelve las cuatro patas con cinemática inversa
y deja que el hombro se deslice un poco cuando la pata no alcanza, como la escápula. La cabeza
mantiene su dirección aunque el cuerpo se mueva, y la cola sigue al cuerpo con retraso:

```bash
blender --background art/characters/rat.blend --python art/characters/animate_rat.py
blender --background art/characters/dog.blend --python art/characters/animate_dog.py
```

| Rata | Duración | Golpe | Uso |
|---|---|---|---|
| `idle` | 4 s, en bucle | | Olfatea a ráfagas, cambia el peso y levanta una mano |
| `walk` | 0,53 s, en bucle | | Paso sigiloso a 0,9 m/s, culebreando |
| `run` | 0,27 s, en bucle | | A saltos a 4,8 m/s: más rápida que el trote del jugador, más lenta que su esprint |
| `strafe_left`, `strafe_right` | 0,4 s, en bucle | | Rodear a 1,2 m/s con los dientes fuera |
| `walk_back` | 0,53 s, en bucle | | Retroceder a 0,9 m/s |
| `attack_bite` | 1,13 s, avanza 0,35 m | 0,57 a 0,7 s | Echa la cabeza atrás y muerde corto |
| `attack_pounce` | 1,8 s, avanza 2,5 m | 0,9 a 1,03 s | Se agacha meneando la cadera, salta y cae mordiendo |
| `attack_rake` | 1,67 s, avanza 0,3 m | 0,63 a 0,73 s | Se para en dos patas y rasga con las dos manos |
| `threat` | 1,8 s | | Medio erguida, boca abierta y temblando: aviso al ver al jugador |
| `hurt` | 0,53 s | | |
| `death` | 2,33 s | | Rueda patas arriba y patalea; se queda en el último cuadro |

| Perro | Duración | Golpe | Uso |
|---|---|---|---|
| `idle` | 3 s, en bucle | | Agachado, jadeando y gruñendo |
| `walk` | 0,67 s, en bucle | | Acecho a 1,3 m/s con la cabeza baja |
| `run` | 0,4 s, en bucle | | Galope a 5,8 m/s |
| `strafe_left`, `strafe_right` | 0,53 s, en bucle | | Rodear a 1,3 m/s |
| `walk_back` | 0,6 s, en bucle | | Retroceder a 1 m/s |
| `attack_snap` | 1,47 s, avanza 0,55 m | 0,53 a 0,63 s y 0,77 a 0,87 s | Doble dentellada: muerde dos veces |
| `attack_lunge` | 1,93 s, avanza 3 m | 0,87 a 1 s | Salto con la boca abierta |
| `attack_thrash` | 2 s, avanza 0,3 m | Muerde a 0,53 s y sacude de 0,73 a 1,4 s | Muerde y sacude la cabeza; puede ser un agarre |
| `bark` | 1,53 s | | Tres ladridos para llamar a la jauría |
| `hurt` | 0,53 s | | Aullido de dolor |
| `death` | 2,47 s | | Cae de lado y patalea; se queda en el último cuadro |

La IA es la del esqueleto: [`MeleeEnemy`](../src/game/enemies/melee_enemy.cpp) la comparte, y
[`RatEnemy`](../src/game/enemies/rat_enemy.cpp) y [`DogEnemy`](../src/game/enemies/dog_enemy.cpp) solo
dan su perfil: vida, rangos, ataques y velocidades. Esas velocidades deben coincidir con las de los
bucles, o las patas patinan. Al ver al jugador, la rata amenaza y el perro ladra antes de atacar; los
dos muerden con una cápsula en la cabeza.

### Güino, el minijefe

[build_guino.py](../art/characters/build_guino.py) lo arma con los mismos huesos que el perro, más
`chain`, que nunca se anima: los eslabones del suelo se arrastran con la raíz y los que cuelgan, con el
cuello. Mide 2,7 m a la cruz y la mandíbula está modelada abierta: en los clips, `jaw` 0 es la sonrisa
completa y -34 la cierra. [animate_guino.py](../art/characters/animate_guino.py) exporta `guino.glb`;
el canal `spin` de `beast_anim.py` gira el cuerpo entero, para el latigazo de cola:

```bash
blender --background --python art/characters/build_guino.py
blender --background art/characters/guino.blend --python art/characters/animate_guino.py
```

| Güino | Duración | Golpe | Uso |
|---|---|---|---|
| `idle` | 5 s, en bucle | | Respira pesado, ladea la cabeza como un perro curioso y raspa el asfalto |
| `walk` | 1,2 s, en bucle | | Acecho pesado a 1,6 m/s, los hombros rodando |
| `run` | 0,67 s, en bucle | | Galope a 7,5 m/s: el jugador no se le escapa corriendo |
| `strafe_left`, `strafe_right` | 0,93 s, en bucle | | Rodear a 1,5 m/s |
| `walk_back` | 1 s, en bucle | | Retroceder a 1,2 m/s |
| `howl` | 2,8 s | | Aúlla al cielo al ver al jugador y le gruñe |
| `attack_maul` | 2,4 s, avanza 1 m | 0,67 y 1,37 s | Zarpazo derecho y luego izquierdo, más rápido |
| `attack_crunch` | 1,87 s, avanza 1,6 m | 0,67 a 0,83 s | Echa la cabeza atrás con las fauces abiertas, se lanza y sacude |
| `attack_whirl` | 2 s | 0,63 a 0,9 s | Gira entero en un salto con la cola a la altura del pecho; solo se salva quien se pega a su costado |
| `attack_crash` | 2,4 s, avanza 6 m | 1,03 a 1,17 s | Menea la grupa como un gato, salta y cae con las dos patas: onda en el suelo |
| `enrage` | 3,2 s | | Fase 2: se sacude como perro mojado, se alza en dos patas y golpea el suelo rugiendo |
| `attack_frenzy` | 2,8 s, avanza 2,2 m | 0,43, 0,67, 0,9 y 1,5 s | Fase 2: tres zarpazos seguidos y una mordida tardía |
| `attack_quake` | 2,47 s, avanza 0,5 m | 0,93 a 1,07 s | Fase 2: se alza en dos patas y cae con todo su peso |
| `death` | 4 s | | Último aullido, cae de pecho y rueda de lado; se queda en el último cuadro |

[`GuinoEnemy`](../src/game/enemies/guino_enemy.cpp) usa la IA de `MeleeEnemy` con un perfil de jefe:
no se aturde, su barra va fija arriba al centro con su nombre y vencerlo congela la inflación de la
avenida para siempre. Bajo el 30 % de vida ruge una vez (`enrage`), las costillas se encienden como
brasas, todo su reloj corre un 20 % más rápido y ataca con su cola de furia. Golpea con cápsulas en la
cabeza, en cada antebrazo y en la cola, y con un cilindro en el suelo (`Slam`) en los impactos, que
levanta polvo. Entre los golpes de un combo sigue girando hacia el jugador, pero nunca durante uno.

## Animaciones

[animate_protagonist.py](../art/characters/animate_protagonist.py) genera los clips y
exporta `protagonist_male.glb` con ellos. Hay que correrlo de último, después de
`build_protagonist.py` y `paint_protagonist.py`, porque antes el modelo no tiene animaciones:

```bash
blender --background art/characters/protagonist.blend --python art/characters/animate_protagonist.py
```

Las poses clave definen pelvis, columna, pies y machete, y la cinemática inversa resuelve
piernas y brazos en cada cuadro. Así los pies no patinan y las dos manos siguen en el
machete. Se escriben en cuadros a 30 fps y se hornean a 60. El `.import` del modelo debe
quedar con `animation/fps=60`, o Godot las reduce a 30.

| Clip | Duración | Interrupción | Uso |
|---|---|---|---|
| `idle` | 5 s, en bucle | Siempre | Reposo a una mano, con el machete a un lado |
| `walk` | 0,8 s, en bucle | Siempre | Caminata a 1,9 m/s con el stick a media carrera |
| `run` | 0,6 s, en bucle | Siempre | Carrera a 4,6 m/s |
| `sprint` | 0,5 s, en bucle | Siempre | Esprint a 6,8 m/s al mantener Shift |
| `run_start` | 0,33 s | Soltar la dirección | Primeros dos pasos; termina donde `run` apoya el pie izquierdo |
| `run_stop` | 0,5 s | Volver a moverse | Frenada con el pie derecho clavado y el machete siguiendo de largo |
| `run_turn` | 0,43 s | Una acción | Giro brusco al invertir la dirección corriendo |
| `jump` | 0,33 s | Golpe aéreo 0,12 s | Despegue sin agacharse, para responder al instante |
| `fall` | 0,8 s, en bucle | Siempre | Caída |
| `land` | 0,4 s | Moverse o cualquier acción | Amortigua el aterrizaje |
| `attack_air` | 0,7 s | Termina el golpe aunque toque el suelo | Golpe por encima de la cabeza, con las rodillas recogidas |
| `dodge_forward` | 0,77 s, avanza 3,2 m | Acción 0,5 s, moverse 0,57 s | Voltereta hacia delante con el machete cruzado sobre el eje de giro |
| `attack_light_1` | 0,8 s, avanza 0,85 m | Esquiva 0,37 s, acción 0,45 s, moverse 0,55 s | Combo 1: corte diagonal rápido con zancada |
| `attack_light_2` | 0,87 s, avanza 0,75 m | Esquiva 0,36 s, acción 0,5 s, moverse 0,6 s | Combo 2: barrido amplio, la mano izquierda suelta y el machete sigue con el brazo derecho |
| `attack_light_3` | 1,33 s, avanza 1,15 m | Esquiva 0,55 s, acción 0,85 s, moverse 0,95 s | Combo 3: salto con giro completo y el machete girando sobre la cabeza, y clavado al suelo a dos manos |
| `attack_roll` | 0,8 s, avanza 1,1 m | Esquiva 0,33 s, acción 0,5 s, moverse 0,6 s | Estocada a una mano al salir de la voltereta |
| `attack_run` | 1 s, avanza 2,35 m | Esquiva 0,4 s, acción 0,62 s, moverse 0,72 s | Atacar esprintando: golpe ascendente a dos manos que aprovecha la velocidad |
| `attack_heavy` | 1,2 s, avanza 0,9 m | Esquiva 0,6 s, acción 0,85 s, moverse 0,95 s | Golpe pesado: alza el machete a dos manos, lo sostiene para que se lea y lo clava en el suelo |
| `hurt` | 0,5 s | Acción 0,35 s, moverse 0,45 s | Recibir un golpe |
| `death` | 0,9 s | Ninguna | Cae de espaldas y se queda en el último cuadro |
| `drink` | 0,9 s | Ninguna; un golpe la corta | Sorbo de café con la mano libre; cura a los 0,45 s, a mitad del sorbo |
| `use_candle` | 0,9 s | Ninguna; un golpe la corta | Alza la vela ante la cara; a los 0,45 s lleva a la última capilla |
| `throw` | 0,7 s | Ninguna; la hace el machete en el aire | Lleva el machete tras el hombro derecho y lo suelta plano a los 0,3 s, con el brazo izquierdo señalando |
| `catch` | 0,4 s | Ninguna | La mano sube abierta a recibir el machete que vuelve y regresa a la guardia |
| `apply_grease` | 0,9 s | Ninguna; un golpe la corta | Cruza la hoja ante el pecho y la mano libre la unta hasta la punta; a los 0,45 s queda engrasada |
| `walk_back`, `strafe_left`, `strafe_right` | 0,4 s, en bucle | Siempre | Moverse a 2,2 m/s con el objetivo fijado; hacia delante usa `walk` |

**Giro de cuerpo:** los canales `tumble` y `spin` giran todo el cuerpo alrededor de un punto
sobre la raíz, y `lift` lo separa del suelo. Las poses se escriben como si no girara, y
`feet_free` decide si los pies giran con el cuerpo (1) o siguen en el suelo (0). En la voltereta la
hoja va sobre el eje de giro, sin atravesar el suelo.

**Combo:** pulsar ataque durante un golpe guarda el siguiente, y tras el tercero vuelve al
primero. Dejar terminar el golpe o moverse después de su corte lo reinicia. Esquivar interrumpe
desde que termina el barrido y no espera a los ataques ya pulsados. La voltereta conserva el
sitio en el combo: un ataque pulsado durante ella es `attack_roll`, y el siguiente sigue con el
paso que tocaba. Cada golpe arranca en la pose donde el anterior permite encadenar (`AFTER_CUT`,
`AFTER_SWEEP` y `AFTER_ROLL` en `animate_protagonist.py`): si cambia esa pose o el tiempo de
`next_action`, hay que actualizarlas.

**Atracción al objetivo:** al empezar un golpe, el personaje se orienta hacia el objetivo más
cercano del grupo `targets` a menos de 4,5 m y 75° de la dirección pedida. También escala el
avance del clip entre 0,25 y 1,6 veces para terminar a 1,1 m. Así el golpe ligero alcanza hasta unos
2,4 m y el pesado algo más. Todo enemigo debe entrar a ese grupo.

**Fijado:** Q, rueda del mouse o R3; la misma tecla lo suelta. Fija el objetivo visible más cercano a 12 m y se suelta a 16 m, si
cae o si pasa 1 s sin verse. Mover el mouse o el stick hacia un lado cambia de objetivo. La cámara
sigue al objetivo y el personaje lo mira mientras camina; al esprintar o rodar corre libre, y la
voltereta usa el mismo clip girado hacia donde se pide.

**Resistencia:** cada acción gasta `stamina_cost`, y el esprint la gasta por segundo. Se recupera
tras 0,5 s sin actuar. Una acción sale si queda algo; al llegar a 0 no se puede esprintar hasta
recuperar el 25 %.

**Recibir daño:** el golpe cancela lo que se esté haciendo. La voltereta es invulnerable durante
0,43 s, y `hurt` también, para que dos golpes seguidos no encierren al jugador. Al morir reaparece
donde empezó tras 3 s, hasta que existan los altares.

**Dummy:** se arma 0,9 s brillando en rojo y gira los brazos estirados. Pega a 1,95 m, lo que
alcanzan los brazos más el ancho del jugador.

**Efectos:** `WeaponTrail` dibuja la estela del machete durante el barrido y el giro del tercer
golpe. El nodo `Dust` de `player.tscn` levanta polvo al rodar, aterrizar, frenar y clavar el machete.
El clavado añade temblor y un empujón de cámara.

**Chaqueta y pelo:** `ClothSprings` en `player.tscn` los mueve con los resortes nativos de Godot,
en 12 cadenas. Trabaja en el espacio del nodo `Model`: en coordenadas del mundo, cada giro del
personaje arrastra toda la tela. La chaqueta usa rigidez 3 y arrastre 0,55, y el pelo rigidez 6 y
arrastre 0,5. Las solapas cuelgan del pecho, y los lados y la espalda de la cadera; no tienen
peso en las piernas. `WaistCollision`, `ThighLeft` y `ThighRight` apartan la tela del cuerpo, y
`HeadCollision` evita que el pelo entre al cráneo.

**Sonido:** los sonidos del jugador están en `Sounds` en `player.tscn`, con varias tomas y tono
aleatorio. Los de los menús están en el autoload `UiSounds`, para que suenen con la pausa y al
cambiar de escena: metal y papel, como las placas de bronce, nunca pitidos. Solo se usa audio CC0,
con su origen en [CREDITS.md](../game/audio/CREDITS.md). Cada sonido se arma en
[build_sfx.py](../art/audio/build_sfx.py), que recibe la carpeta con los packs descomprimidos.

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

**Objetos en la mano:** los canales `cup_on` y `cup` hacen que la mano izquierda mantenga el objeto
en la dirección pedida, en vez de seguir al antebrazo. La taza y la vela son nodos bajo `HandItem`
en `player.tscn`, y `PlayerController` solo muestra el que se está usando.

**Agarre:** el hueso `weapon` queda en la mano derecha y la izquierda cierra 0,1 m detrás, en el mango.
Con el filo hacia donde cierran los dedos, el arma corta con el filo en los barridos.

## Interfaz

Abajo a la izquierda van vida y resistencia, junto a un rombo con el objeto en mano y su cantidad.
Arriba al centro irá la barra del jefe y abajo a la derecha las lochas. No hay minimapa, brújula ni mira.

- **Inicio:** `title.tscn` es la primera escena: primer plano del protagonista bajo la lluvia, con
  logo y menú a la derecha. Abre, carga, crea y borra las 5 partidas.
- **Pausa:** Esc o Start detienen el juego; el inventario no.
- **Metal:** `MetalPlate` dibuja metal cepillado con degradados, vetas finas, biseles y sombras
  escalonadas, sin texturas. Su patrón es fijo para que no parpadee al redibujar.
- **Fuentes:** Cinzel en títulos e Inter en el resto, ambas con licencia OFL en `game/fonts`.
- **Paleta:** azul acero, en `ui_palette.hpp`, para combinar con la lluvia del Inicio.
- **Selección:** la fila o casilla elegida hace un pequeño pop con un tween. Las filas no se
  reconstruyen al cambiar de selección, para que la animación pueda verse. Vida y resistencia conservan sus colores para
  leerse en combate.
- **Menús:** un panel oscuro a la derecha deja ver el mundo. El inventario tiene tres pestañas que se
  recorren con `Z` y `C` (consumibles, coleccionables y armas), cuadrícula de 5 columnas, detalle del
  objeto y orden con `R`.
- **Mouse:** el cursor aparece mientras hay un menú abierto. Pasar por encima selecciona, el clic
  izquierdo acepta y el derecho vuelve.
- **Íconos:** son renders de los mismos modelos, en `game/ui/icons/<clave>.png`, con contorno azul para
  separarse del fondo oscuro. `ItemSlot` carga el de cada objeto, también en el rombo del HUD. Las
  lochas llevan el suyo junto al contador y la capilla en el título de su menú. Se importan con
  mipmaps, porque se dibujan mucho más pequeños que el render.
- **Sin imágenes:** `StatBar` dibuja el marco y el relleno con polígonos de caras planas, así no
  pierden nitidez. El relleno repite la punta del marco, por lo que encaja a cualquier valor.
- **Lochas:** solo la cantidad y la moneda, en una placa pequeña abajo a la derecha.
- **Vida:** verde sobre 60 %, ámbar sobre 35 %, naranja sobre 15 % y rojo por debajo. El color cambia
  de golpe, y una franja pálida marca lo que quitó el último golpe.
- **Resistencia:** cian, para no confundirse con la vida a medias ni perderse en el asfalto. Se
  vuelve gris al agotarse.
- **Contraste:** todo lleva contorno oscuro y una sombra escalonada hacia abajo y a la derecha, para
  separarse del mundo 3D. El borde donde termina el relleno va más claro que el resto.
- **Tamaño:** las medidas de `player.tscn` son para 1080 de alto, y el panel se escala a la ventana.

## Armas

**Regla para todas las armas: pega el arma entera.** Si se ve que el arma toca al enemigo
durante el golpe, el golpe cuenta, sea con la punta, el centro o el mango.

- **Forma de golpe:** el nodo `Hitbox` de `player.tscn` cubre la malla del arma de punta a
  punta. Va en el hueso `weapon`, así sigue la animación. Se mide contra la malla real,
  no a ojo: el machete va de -0,13 a 0,8 m sobre el eje Y del hueso, así que su cápsula mide
  0,95 m y está centrada en 0,335 m. Su radio de 0,09 m cubre el ancho de la hoja y perdona un poco.
- **Ventana de golpe:** `hit_start` y `hit_end` en `player_actions.cpp` cubren todo el
  barrido, desde que el arma deja la pose alzada hasta que se detiene. No cuentan la
  preparación ni la pose final sostenida.
- **Un golpe por objetivo:** cada acción daña una vez a cada objetivo. Una acción nueva
  vuelve a dañar.
- **Al cambiar un arma o agregar un ataque:** hay que actualizar la cápsula o la ventana, y
  comprobar con el dummy en varias posiciones que cada contacto del barrido registra daño.
- **Límite conocido:** la forma se consulta 60 veces por segundo sin barrer entre ticks, y
  la punta del machete avanza hasta unos 0,4 m por tick. Un objetivo más delgado que eso
  podría saltarse; en ese caso hay que comprobar posiciones intermedias.

## Objetos

[build_loot.py](../art/props/build_loot.py) genera todos los objetos, guarda `loot.blend`, exporta
`game/models/props/<clave>.glb` y renderiza los íconos con Cycles desde la misma malla. El `.glb`
y el ícono usan la clave del objeto en el catálogo, así que uno nuevo no necesita código:

```bash
blender --background --python art/props/build_loot.py
```

Si cambia el machete, hay que correr además `build_skeleton.py`, `animate_skeleton.py` y
`animate_protagonist.py`. Texturas
pintadas con ruido y figuras simples en [prop_tools.py](../art/props/prop_tools.py), sin fotos.

| Objeto | Diseño | Triángulos |
|---|---|---|
| Café | Taza de peltre blanco con borde azul y desconchones de óxido | 316 |
| Vela de retorno | Vela de iglesia con cera corrida, collar de papel rojo y llama propia | 312 |
| Vinilo de gaita | Disco saliendo de una carátula de los setenta con maracas y sol | 534 |
| Cromo de béisbol | Bateador con marco rojo, doblado por una esquina | 48 |
| Ficha de dominó | Doble seis de marfil con reverso oscuro y remache de latón | 364 |
| Foto familiar | Sepia, doblada al medio y con una esquina rota; una de las figuras casi se borró | 94 |
| Machete | Lomo recto, panza hacia la punta, bisel limado, dos muescas, cachas con tres remaches y óxido en bandas | 521 |
| Capilla | Capilla de carretera: arco azul, techo de zinc, Virgen, velas, placas y hiedra | 1.766 |
| Mancha de lochas | Charco de brea con borde pálido y monedas sueltas | Cerca de 900 |

**En el suelo:** `LootPickup` carga el modelo por su clave, lo gira y lo agranda hasta 0,42 m, para
que una ficha de 5 cm se vea desde la cámara. Los que ya miden más quedan a su tamaño real.

**Machete:** la textura de 1024 × 512 guarda las dos caras de la hoja y la madera. El óxido se
concentra junto al guardamano, en el lomo, en la punta y alrededor de las muescas, y va en bandas
duras para verse pintado. La cara izquierda lleva un 58 estampado cerca de la cacha. El jugador puede
empieza con él en la mano y lo ve en la pestaña Armas.

**Provisionales:** las grasas de fuego y de hielo no tienen modelo todavía. Sus íconos son una lata
plana de su color, y en la hoja se ven como un brillo del mismo color que late y parpadea al acabarse.
Cuando se modelen, van en `build_loot.py` con sus claves `fire_grease` e `ice_grease`, y el ícono
provisional se reemplaza solo.

**Gorra provisional:** un casquete rojo de media esfera y una visera plana, en `player.tscn` bajo
`HeadItem`, un `BoneAttachment3D` del hueso `head`. `PlayerController` deshace el giro de reposo del
hueso para que la gorra se arme en los ejes del cuerpo: arriba es +Y y el frente +Z. Su ícono es una
silueta plana. El modelo final va en su propia tarea, con la misma clave `cap`.

**Capilla:** su parte sólida no pasa de 1,15 m hacia el frente, porque el jugador reaparece a 1,6 m.

**Luces:** las de los objetos usan `light_specular = 0`; si no, el asfalto mojado las refleja como
manchas blancas.

## Escenario 1: avenida de Caracas

Avenida abandonada bajo tormenta, basada en las referencias 07 y 08: bloques de losas
con balcones, casas de ladrillo con escaleras, comercios cerrados, hiedra densa,
autobús y carros abandonados, postes con cables caídos, charcos, escombros detrás del
inicio, torre escalonada y el Ávila al fondo.

**Recorrido:** toda la zona tiene arte. Lo que todavía no existe (la radio, las pintadas legibles, el
padre y el modelo del bachaquero) queda marcado con cápsulas y letreros en
[avenue_markers.tscn](../game/scenes/avenue_markers.tscn).

| Tramo | Dónde (x, z en Godot) | Qué hay |
|---|---|---|
| Avenida | 0, de 46 a -46 | Inicio, un esqueleto solo y luego una pareja |
| Plaza de la torre | -30 a 30, de -50 a -125 | Tres esqueletos afuera, la radio y el abasto saqueado al noreste, con tres ratas, el vinilo y la ficha |
| Callejón del terremoto | 30 a 130, de -99 a -125 | Zigzag entre edificios agrietados, la casa partida, tres esqueletos y pintadas |
| Plazoleta de la capilla | 130 a 160, de -94 a -140 | Capilla y padre: aquí se descansa por primera vez. El portón abre la callejuela hacia la plaza |
| Calle a la catedral | 160 a 260, de -105 a -140 | Bachaquero, mercado de lonas con dos ratas, cancha con dos perros, una rata entre los carros, dos esqueletos y el café antes del jefe |
| Plaza de la catedral | 260 a 312, de -85 a -145 | Güino frente a su guarida, y la puerta trancada de la catedral, salida a la selva |

Al otro lado de la torre, el Ávila empieza en z = -170, así que el recorrido gira al este antes de
llegar. La lluvia va con el jugador para cubrir toda la zona.

[build_avenue.py](../art/environments/build_avenue.py) genera la avenida, guarda
`avenue.blend` y exporta `avenue.glb`; su suelo termina en z = -50 y su fondo de edificios no pasa de
ahí. [build_route.py](../art/environments/build_route.py) genera el resto con las mismas funciones y
los mismos cinco materiales, guarda `route.blend` y exporta `route.glb` y `shortcut_gate.glb`:

```bash
blender --background --python art/environments/build_avenue.py
blender --background --python art/environments/build_route.py
```

Los objetos terminados en `-colonly` son las colisiones: una malla por tramo. La escena
[avenue.tscn](../game/scenes/avenue.tscn) añade cielo, niebla, luz de tormenta, reflejos y lluvia.
`route.glb` usa el mismo `avenue_import.gd` que la avenida, así que su fondo (`backdrop_square`) no
proyecta sombra y el resto la proyecta por las dos caras.

**Fachadas en cualquier dirección:** `building(a, b, ...)` levanta una manzana cuya fachada va de `a` a
`b` con la zona jugable a su izquierda. Por dentro usa un marco local (`frame`), así que reutiliza
`window`, `shop_front` e `ivy_curtain` de la avenida tal cual. `collide` guarda colisiones giradas
con el mismo marco, y `holed_wall` y `holed_slab` arman paredes y losas con huecos.

**Plaza de la torre:** la torre tapa el frente al salir de la avenida y obliga a rodearla. El
abasto y farmacia ocupa x 10 a 30, z -99 a -113, en dos pisos de 3,6 y 3,5 m:

- Abajo: mostrador de farmacia con estantería, tres góndolas (una volcada) que forman pasillos de
  2,8 m, neveras abiertas (una de cara al piso) y el depósito con su cocinita.
- Escalera de concreto contra la pared norte, de 1,7 m de ancho: con menos, la navegación no sube.
  Una rampa de colisión de 27° la cubre y bloques escalonados llenan su vientre.
- Arriba: oficina con escritorio (la ficha de dominó), sala con tocadiscos (el vinilo), chinchorro y
  sofá, y un cuarto abierto donde alguien durmió. El hueco del piso (x 18,9 a 21,4, z -105 a -108)
  deja ver los pasillos y deja un paso de 1,6 m junto a él.
- Luz: ventanas tapiadas con rendijas entre las tablas, por donde entra la luz de tormenta. El
  `ReflectionProbe` `StoreInterior` baja la luz ambiente dentro.
- Atajo de un solo sentido: la pared este rota del primer piso da a la losa caída de la casa vecina,
  que baja de 3,5 a 2,3 m. Al final se salta al bolsillo del callejón (x 44 a 50), detrás del primer
  zigzag y de su esqueleto. Con 1,1 m de salto no se vuelve a subir.

**Callejón del terremoto:** las fachadas del norte avanzan y retroceden (z -121, -125, -116, -123,2,
-115, -125) y el camino zigzaguea entre ellas y la fila sur (z -108). En la primera curva, una
fachada caída y escombros de 1,3 m obligan a pegarse al norte. Una losa cruza el callejón por
arriba, a más de 4 m. La casa partida (x 86 a 98) se cruza por dentro: entra por la puerta oeste,
pasa por la sala y la cocina y sale por la pared este rota. La grieta corre por el medio y deja el
techo abierto sobre el camino, para que la cámara tenga aire. La animita del norte, en x 56, es un
punto de botín.

**Callejuela del portón:** de 5 m de ancho (z -94 a -99), corre detrás de la fila sur del callejón,
con ropa tendida, tanques y la casita de un perro. Termina en el portón de la plazoleta de la
capilla, en x 130. [ShortcutGate](../src/game/world/shortcut_gate.cpp) solo se abre con E desde
el lado +X (la capilla); del otro lado avisa "Cerrado por el otro lado". La hoja gira hacia la
plazoleta y la apertura se guarda como el bit 200 de los pickups, así que ningún `pickup_id` debe
usar ese número.

**Plazoleta de la capilla:** casas coloniales pintadas de dos pisos, el mango con su banco
redondo, bancos, matas en materos y un farol con luz cálida (`ChapelLamp`). No hay enemigos.

**Calle a la catedral:** santamarías a ambos lados y el puesto del bachaquero (x 172). El mercado
(x 185 a 212) tiene lonas caídas sobre cajas donde duermen las ratas. La cancha (x 216 a 244,
z -125 a -140) tiene malla ciclón de 3,5 m con una rotura en el extremo oeste, por donde salen los
perros. En x 248 la calle se estrecha a 6 m con huesos, una cadena rota, un collar y tres zarpazos
en las paredes.

**Plaza de la catedral:** la arena despejada mide 40 × 50 m. La fuente central tiene 3,5 m de radio
y un borde de 0,45 m. La cobertura baja (bancos, materos, un taxi y los restos de la torre caída) va
solo junto a las paredes. La catedral tiene la torre sur entera, la norte partida, la fachada con
el rosetón y una viga caída que tranca la puerta. Bajo el pórtico de tres arcos está la guarida, con
colchones, huesos, platos oxidados y una cadena.

**Botín:** se colocan pocos de los objetos actuales: el vinilo y la ficha en el abasto, y el
segundo café antes del jefe. Los nodos `Marker3D` de `LootSpots` en `avenue.tscn` marcan superficies
listas para el botín nuevo: cocina, caja registradora, estante y sofá del abasto, colchón, bañera,
animita, mesa y cocina de la casa partida, casita del perro, banco de la capilla, puesto del mercado,
colchón de la cancha, guarida y fuente. Un `LootPickup` nuevo va en la posición de uno de ellos.

**Navegación:** después de cambiar colisiones, hay que hornear de nuevo con el botón Bake del nodo
`Navigation`. Hay que comprobar que la escalera, la oficina y el depósito sigan dentro: las puertas
interiores miden 2 m porque la malla pierde 0,5 m de cada lado.

**Optimización de escenarios:**

- El color va en los vértices, con cinco materiales para todo el mapa.
- La vegetación se hace con láminas continuas y domos, no con objetos sueltos.
- Se borran las caras que quedan dentro de sólidos o de espaldas a toda la zona
  jugable. Por eso el mapa se ve incompleto desde fuera o desde arriba: es a propósito.
  Si el jugador va a poder subir a un sitio, hay que ampliar `PLAY_CORNERS`. El de `build_route.py`
  llega a 8,6 m por el primer piso del abasto y por la losa del atajo.
- Las capas largas se parten por tramos para que Godot omita lo que no está en cámara.

## Presupuesto inicial

Son valores de partida; se ajustan si el juego los necesita.

| Tipo | Triángulos |
|---|---|
| Personaje principal | Hasta 15.000 |
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
