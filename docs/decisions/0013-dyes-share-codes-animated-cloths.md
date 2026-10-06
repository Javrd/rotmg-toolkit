# 0013 — Varios tintes comparten código; las telas animadas se pintan quietas

## Contexto

Javi echó en falta telas "dinámicas" (animadas). Al revisarlo:

- `outfit_scraper.py` creaba **una entrada por código** de `sheetOffsets`
  y le ponía el nombre del primer ítem de ese código. Pero un código
  puede llevar varios pares de ítems (ropa, accesorio): ocho telas
  animadas comparten código y textura con su versión quieta (Running
  Heart / Heart, Terminal / Futuristic, Falling Snowflakes / Snowy
  Night, Black Coin Rain / Black Coin, Falling Voodoo Skulls / Voodoo
  Skulls, Snowflake Vortex / Snowflake, Spinning Stars / Starry,
  Floating Clouds / Cloud), y Cyan y Magenta son Aqua y Fuchsia con otro
  nombre. Esos diez nombres no salían en el selector.
- Las animadas que tienen código propio (Migrating Birds, Tidal…) sí
  salían, pero quietas. Así las pinta también RealmEye. La hoja de
  `sheet.js` trae un único fotograma de cada tela, y las imágenes de
  `/wiki/cloths` son PNG estáticos: el movimiento no está en ninguna
  fuente que podamos leer.

## Decisión

- Una entrada por **nombre** de tinte, con sus ids de ítem de RealmEye
  (`items: [ropa, accesorio]`). El personaje guarda el código, que dice
  cómo pintarlo, y además el id de ítem (`dye1Item`/`dye2Item`), que es
  lo que distingue a dos tintes con el mismo código. Es lo que RealmEye
  da en `data-clothing-dye-id`/`data-accessory-dye-id`.
- Las 30 telas de la tabla "Animated" de `/wiki/cloths` se marcan
  `animated`. El nombre se toma de la leyenda de cada fila, porque los
  `alt` de las imágenes están mal en algunas (el de Running Heart dice
  "Heart Cloth").
- No se inventa la animación. Moverlas a ojo daría un resultado que no
  se parece al juego. Se pintan quietas, como en RealmEye, con una ▶ en
  el selector y "(animated)" en el resumen.

## Consecuencias

- 399 tintes en vez de 389. Spinning Stars y Floating Clouds no están
  en la tabla "Animated" de la wiki y no se marcan, aunque por el nombre
  probablemente lo sean.
- Un personaje guardado antes de este cambio solo tiene el código; si
  ese código es compartido, se muestra el primer nombre (la versión
  quieta) hasta que se vuelva a elegir.
