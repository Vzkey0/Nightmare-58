# Nightmare 58: Cinemática de apertura

Estado: borrador del guion. Va del negro inicial hasta que el jugador toma el control con el machete.

## Idea

Una escena tranquila que se rompe de golpe. El jugador entra al carro sin saber nada y sale con
el país explicado y con su amigo muerto. Luis cuenta la crisis como la cuenta cualquiera: con
chistes amargos, sin discursos. Del Silbón casi no se habla: apenas una radio que se calla y un
silbido que nadie nombra.

- **Duración:** unos 3 a 4 minutos. El viaje dura 2,5; el choque y el despertar, menos de uno.
- **Tono:** de día gris a noche de tormenta. El cielo se oscurece mientras Luis habla.
- **Audio:** lluvia, motor, limpiaparabrisas y la radio. No hay música hasta el choque.
- **Texto:** solo subtítulos, sin voces grabadas. Se pueden agregar después.
- **El protagonista:** habla poco, y nadie dice su nombre porque lo elige el jugador. Luis le dice
  "pana", "mano" o "chamo".

## Estructura

| # | Parte | Dura | Qué pasa |
|---|---|---|---|
| 0 | Negro | 0:10 | Lluvia y una radio sintonizando. Aparece "Caracas, 19 de mayo de 2018" |
| 1 | Llegada | 0:30 | Dentro del carro. Luis lo recogió en el aeropuerto |
| 2 | La plata | 0:45 | Inflación, colas y bachaqueros, mientras pasan por un abasto vacío |
| 3 | La gente | 0:30 | Los que se fueron, la ciudad vacía y el machete en el asiento de atrás |
| 4 | El terremoto | 0:40 | Edificios partidos, la madre y la radio que se calla |
| 5 | La vía | 0:15 | Silbido lejano, esqueletos en la vía, volantazo y choque |
| 6 | Despertar | 0:40 | Luis en el suelo, el machete y la primera pelea |

**Fecha:** 18 de mayo de 2018 o por ahi

## Cámara

El carro está quieto en el origen y el mundo pasa por las ventanas. Hay cuatro planos fijos que se
alternan con cortes, nunca con movimientos largos:

| Plano | Dónde | Para qué |
|---|---|---|
| **A. Atrás, centro** | Asiento trasero, entre los dos | El plano base: los dos de espaldas y la vía por el parabrisas |
| **B. Atrás, sobre Luis** | Detrás del hombro del protagonista, mirando a Luis | Cuando habla Luis |
| **C. Atrás, sobre el protagonista** | Detrás del hombro de Luis | Cuando responde el protagonista, o cuando mira por la ventana |
| **D. Ventana** | Asiento trasero derecho, por la ventana de atrás | Lo que ve: el abasto, el edificio partido y la gente que no está |

Reglas:

- Cortar en el plano de quien habla y volver a A en los silencios.
- Un leve balanceo constante en todas las cámaras (0,5 cm, a ritmo del motor) para que no se vean
  pegadas al carro.
- En la parte 5 la cámara deja de cortar: plano A fijo mientras aparecen los esqueletos, y corte
  a negro en el impacto.

## El paisaje en las ventanas

El carro no se mueve. Lo que se mueve es el mundo, como en una cinta:

1. **La vía:** unos 6 tramos de calle de 40 m que avanzan hacia atrás. Cuando uno sale por detrás,
   pasa adelante. Cada tramo lleva fachadas, postes y carros a los lados, armados con las mismas
   funciones de `build_route.py`.
2. **El fondo:** el Ávila y los edificios lejanos en un plano que se mueve mucho más lento. Eso da
   la profundidad.
3. **Las piezas del guion:** el abasto con la cola, el edificio partido y los esqueletos son
   tramos especiales que entran a la cinta en el momento justo de la conversación.
4. **Lluvia en el vidrio:** gotas en el parabrisas y los limpiaparabrisas a un ritmo fijo.

La velocidad baja un poco en las partes 2 y 4, para que se lean los edificios mientras Luis habla.

## Guion

**L** es Luis y **P** es el protagonista. Entre corchetes van el plano y lo que se ve.

### 0. Negro

[Pantalla negra. Lluvia. Una radio busca estación entre la estática.]

En el centro, letra blanca simple, aparece y se desvanece:

> Caracas, 19 de mayo de 2018

[La radio encuentra una gaita a media canción. Corte al carro.]

### 1. Llegada

[A. Tarde gris. Luis maneja con una mano. Suena la gaita.]

**L:** Diez años, mano. Diez años y te vienes justo ahora.

**P:** Mi mamá no contesta desde diciembre.

[B]

**L:** Aquí nadie contesta desde diciembre. No te lo tomes personal.

**L:** Te iba a decir que pusieras el aire, pero se dañó en 2016 y el repuesto cuesta más que el
carro.

### 2. La plata

[D. Pasa un abasto con la santamaría a medio bajar y una cola larga en la acera bajo la lluvia.]

**L:** ¿Ves esa cola? No saben qué llega. Hacen la cola por si acaso.

**P:** ¿Y la gente cómo hace?

[B]

**L:** Los precios los cambian dos veces al día. En la mañana un kilo de harina, en la tarde lo
mismo cuesta el doble.

**L:** Ya nadie cuenta los billetes. Los pesan.

**L:** Lo que hay lo tienen los bachaqueros, y te lo venden a lo que les da la gana.

[C. El protagonista mira por la ventana.]

**L:** Mi abuelo guardaba lochas en una lata de galletas. Nos reíamos de él. Ahora valen más que
un sueldo.

### 3. La gente

[A. Las calles se ven más vacías: carros parados, un autobús abandonado.]

**L:** Mi hermana se fue a Bogotá. Mis primos a Lima. Los del edificio... ni sé.

**L:** Antes la gente se iba por el aeropuerto. Ahora se va caminando.

**P:** ¿Y tú por qué te quedaste?

[B. Luis se ríe sin ganas.]

**L:** Alguien tenía que buscarte en el aeropuerto, ¿no?

[B. Luis señala hacia atrás con el pulgar, sin quitar la vista de la vía.]

**L:** Ahí atrás hay un machete. No preguntes. Aquí ya nadie sale sin uno.

### 4. El terremoto

[D. La velocidad baja. Pasa un edificio partido por la mitad, con los cuartos a la vista: una cama,
una nevera, un cuadro todavía colgado.]

**L:** Y después vino el terremoto. Cuarenta segundos.

**L:** Cuarenta segundos y se cayó media ciudad. Lo que la crisis no tumbó, lo tumbó eso.

**P:** No salió casi nada afuera.

[B]

**L:** Porque no quedó nadie para contarlo. Se cayeron las antenas y la luz, y después ya nadie
volvió a levantarlas.

**L:** Del otro lado, donde vive tu mamá, no se sabe nada desde entonces.

[A. Silencio largo. Solo la lluvia y la gaita.]

**L:** Pero la vieja es dura, mano. Si alguien aguantó, fue ella.

[A. La gaita se corta en seco. Estática. La radio se queda muda. Luis le da dos golpes.]

**L:** Esta radio también se está muriendo.

### 5. La vía

[A. Ya es de noche. La lluvia arrecia. Por debajo de la lluvia, un silbido de unas pocas notas,
lejano.]

**P:** ¿Oíste eso?

**L:** ¿Qué cosa?

[A fijo. En los faros, figuras paradas en medio de la vía. Son esqueletos, y se voltean hacia
la luz.]

**L:** ¿Y eso qué...?

**L:** ¡Agárrate!

[A. Volantazo. El mundo gira en las ventanas, el carro se sube a la acera y va directo contra
la fachada de un edificio. Corte a negro en el impacto. Silencio total.]

### 6. Despertar

[Negro. Un pito en los oídos. La imagen vuelve borrosa y de lado: el protagonista tiene la
cabeza contra la ventana rota. El parabrisas está roto y la lluvia entra.]

[Plano desde el asiento, bajo. A través del vidrio roto: Luis está en el suelo, afuera, y los
esqueletos se agachan sobre él. Solo se ven siluetas contra los faros y la mano de Luis, que se
arrastra por el asfalto y luego se queda quieta. No se muestra nada más.]

**L:** (débil) Vete...

[C. El protagonista se voltea hacia el asiento de atrás. El machete está ahí, como dijo Luis.]

[Corte al exterior. La puerta se abre de una patada. El protagonista sale con las manos
vacías; el machete aparece en su mano cuando el jugador toma el control. Uno de los esqueletos levanta la cabeza y se pone de pie.]

[La cámara se mueve hasta la posición de juego detrás del protagonista. Aparece el HUD.
El jugador toma el control: primera pelea.]

## Ideas para que pegue más

- **La gaita es la alegría.** Suena todo el viaje y se corta de golpe en la parte 4. Es la única
  pista del Silbón en toda la escena (él se llevó la música), y no hay que explicarla.
- **El machete se plantea antes de usarse.** Luis lo menciona en la parte 3 y el jugador lo
  encuentra en la parte 6. Así el arma tiene historia y no aparece de la nada.
- **Las lochas también.** El comentario del abuelo explica sin decirlo por qué el juego usa esa
  moneda.
- **El edificio partido de la parte 4** puede ser el mismo del callejón del terremoto. Si el jugador
  lo reconoce después, la ciudad se siente conectada.
- **El cielo como reloj:** tarde gris al inicio, noche al llegar a la vía. Se puede hacer con una
  sola animación del `WorldEnvironment` y de la luz.
- **El último plano:** antes de ver a Luis, mantener 2 segundos el pito en los oídos y la imagen
  borrosa. Es lo que hace que el corte duela.
- **Saltar la escena:** mantener presionado el botón de interactuar (E, o X en el mando) durante un
  segundo, con un círculo que se va llenando. Así nadie la salta por accidente la primera vez.

## Cómo se arma en Godot

Usa los modelos de la tabla de arte; solo los edificios genéricos y la ciudad lejana siguen siendo
bloques, porque pasan dentro de la niebla.

`opening.tscn` y `crashed_car.tscn` las escribe [build_opening.py](../art/scenes/build_opening.py)
(`py art/scenes/build_opening.py`): para cambiar algo se cambia el script y se vuelve a correr, porque
lo que se edite a mano en esas dos escenas se pierde.

- **Escena:** `game/scenes/opening.tscn`. El carro está quieto en el origen; la calle (`Road`, seis
  tramos de 40 m que se reciclan) y la ciudad lejana (`Skyline`, a un quinto de la velocidad) pasan
  por debajo: un carrusel, no un escenario. Cada tramo es `street.glb` con tres filas de bloques de edificios a
  cada lado: una baja junto a la acera, que se aparta cuando pasa una pieza del guion, y dos más
  altas detrás (`Behind*` y `Far*`), que se quedan siempre para que la calle nunca se vea vacía. El Ávila no se mueve.
- **Animación:** un solo `AnimationPlayer` (`opening`, 3:09) lleva todo el guion: cortes de cámara,
  subtítulos, velocidad de la cinta, cielo, faros, lluvia, el volante y la radio que se apaga. Llama
  a `play` en los `AnimationPlayer` de Luis (`drive`, `talk`, `laugh`, `point_back`, `let_go`,
  `hit_radio`, `swerve`; en el suelo `lying` y `reach`) y del protagonista (`sit`, `sit_window`,
  `sit_back`, `brace`). Los limpiaparabrisas tienen su propio `AnimationPlayer`.
- **Código:** `OpeningCutscene` (C++) mueve la cinta según `drive_speed`, recibe de la animación
  `cut`, `say`, `send` y `finish`, y maneja el botón de saltar. `say` pone el nombre que eligió el
  jugador; sin hablante, el texto sale en cursiva como subtítulo de sonido.
- **Piezas del guion:** el abasto, el autobús, el edificio partido y los esqueletos esperan ocultos en
  `Props`. `send` los pone a 180 m, dentro de la niebla, y la cinta los trae. Mientras pasan, los
  edificios normales que se les cruzan se ocultan. Si se cambian los tiempos del guion, hay que mover
  la llave `send` para que la pieza siga llegando con su frase.
- **Despertar:** pasa en la avenida misma (`CrashSite`, una copia de `avenue.glb` lejos del viaje).
  El último plano termina donde arranca la cámara del jugador y de ahí se carga `avenue.tscn`.
- **Sin marca de guardado:** solo una partida nueva entra a la cinemática; continuar o cargar va
  directo a la avenida. Quien cierre el juego a mitad de la escena no la vuelve a ver.
- **Sangre:** `blood_pool.glb` (`art/props/build_blood.py`) va dentro de `crashed_car.tscn`, bajo
  Luis tirado. Se queda en la avenida cuando la cinemática termina y Luis ya no está.
- **Punto de llegada:** `crashed_car.tscn` (`car_crashed.glb` con la puerta derecha abierta y el machete
  oculto) está en las dos escenas, al inicio de la avenida contra la fachada izquierda
  (`-7.2, 0, 30`). Luis, en `lying`, solo está en `opening.tscn`, como hijo del coche: un juego
  exportado pierde los cambios hechos a nodos dentro de una escena instanciada, así que no se puede
  esconder desde la avenida. Cae hacia la calle, lejos de las plantas de la acera. El jugador
  aparece a dos metros, del lado de la calle, para no quedar encima de ellos, y `CrashSkeleton`
  es el que se levanta: la primera pelea.
- **Los esqueletos comiendo:** los tres de `CrashSite` tienen el clip `feed` (agachados sobre Luis:
  muerden, jalan sacudiendo el cráneo y mastican), desfasados para que no muerdan juntos. El que
  pelea se levanta con `feed_rise`. En la avenida solo queda ese esqueleto; Luis ya no está.
- **Lluvia:** tres emisores alrededor del carro (`RainLeft`, `RainRight`, `RainFront`), para que
  ninguna gota caiga dentro de la cabina.
- **Subtítulos:** cada frase se escribe letra por letra (38 por segundo) con un tecleo de máquina
  de escribir, para que se pueda ir leyendo. El nombre de quien habla sale completo desde el
  inicio. Los subtítulos de sonido, en cursiva, se escriben sin tecleo.
- **Audio:** los reproductores están en `Sound` (más `Car/Engine` y `Screen/Typewriter`), y la
  animación los arranca, los para y les baja el volumen. Lluvia todo el tiempo, más fuerte de noche;
  radio sintonizando en el negro; la música desde el primer plano hasta que se corta en estática,
  con los dos golpes de Luis; trueno al anochecer, el silbido, el frenazo con el choque y, en el
  impacto, silencio total. Al despertar: el pito, y debajo vuelven la lluvia y los esqueletos
  comiendo. Después, la patada a la puerta y los huesos del que se levanta. El motor sube de tono
  con `drive_speed`, y los limpiaparabrisas suenan en cada pasada. Pixabay no tiene gaitas, así que
  la radio pone un joropo; el origen de cada sonido está en `game/audio/CREDITS.md`.

## Arte

Cada modelo sale de un script de Blender; se describen en [art_guide.md](art_guide.md).

| Pieza | Script | Estado |
|---|---|---|
| Luis | `art/characters/build_luis.py` | Hecho, con sus 9 clips |
| Protagonista sentado | `animate_protagonist.py` | Hecho: `sit`, `sit_window`, `sit_back`, `brace` |
| Carro y carro chocado | `art/props/build_car.py` | Hecho |
| Tramo de calle, abasto con cola, autobús, edificio partido | `art/environments/build_drive.py` | Hecho |
| Esqueletos comiendo | `animate_skeleton.py` | Hecho: `feed`, `feed_rise` |
| Sonido | `art/audio/build_opening_sfx.py` | Hecho, con sonidos de Pixabay |
