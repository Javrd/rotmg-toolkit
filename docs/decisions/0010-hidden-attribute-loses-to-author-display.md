# 0010 — El atributo `hidden` pierde contra `display:flex`, y jsdom no lo detecta

## Contexto

El buscador rápido de la Fame Checklist ([[0009-fame-collection-dungeon-aliases]])
se entregó con el filtrado roto: al escribir, la lista seguía mostrando
las 65 mazmorras. Lo reportó Javi.

Causa raíz: `fameFilter()` ocultaba las filas con `row.hidden = !hit`, y
la fila es un `<label class="fame-result">` con esta regla de autor:

```css
.fame-result { display:flex; align-items:center; ... }
```

El `[hidden] { display:none }` que hace que ese atributo funcione vive en
la **hoja del user-agent**, y en la cascada de CSS cualquier regla de
autor gana a la del UA. Es decir, `.fame-result { display:flex }` anulaba
el `display:none` del atributo: el atributo se ponía en el DOM (el HTML
resultante era correcto) pero no ocultaba nada. El estado vacío
(`.fame-empty`) sí funcionaba, porque su regla no declara `display`.

El fallo de verdad, sin embargo, es que **el test dijo que funcionaba**.
La suite era jsdom y comprobaba `row.hidden === true`, que es la
propiedad del DOM, no lo que ve el usuario. Peor: al reproducirlo,
`window.getComputedStyle(row).display` en jsdom devuelve `"none"` — jsdom
no modela la cascada UA-vs-autor, así que ni siquiera consultando el
estilo computado se detecta. Chromium, con la misma página, mostraba las
65 filas.

## Decisión

- Añadida la regla de autor `[hidden] { display:none !important; }` a la
  hoja de `build_html.py`, junto a la `.hidden` que ya existía. Arregla
  este caso y cualquier futuro uso del atributo en la página.
- **La suite de UI pasa a Chromium real** (`tests/fame.spec.mjs`,
  `npm test`, `playwright-core` como devDependency). Las asserts son
  sobre `:visible` / `isVisible()`, nunca sobre el atributo o la clase
  que *debería* ocultar algo.
- jsdom queda descartado para este proyecto: no es que le faltara una
  assert, es que da un resultado **activamente falso** sobre la cascada.
  Un test que no puede fallar cuando la página está rota no es un test.
- La suite incluye ahora un viewport de 400px, que tampoco era
  verificable antes.

## Consecuencias

- Verificado en Chromium: con el `index.html` publicado antes del
  arreglo, escribir "snake" dejaba 65 filas visibles; con el arreglo,
  deja 1. El test nuevo falla con el build viejo y pasa con el nuevo.
- Correr la suite necesita un binario de Chromium
  (`npx playwright install chromium`, ~110 MB). No se versiona.
- En este NUC, además, Chromium no arranca porque faltan `libnspr4` y
  `libnss3` y no hay sudo. Se resuelve sin root descargando los `.deb` y
  desempaquetándolos en un directorio propio:

  ```bash
  apt-get download libnspr4 libnss3
  dpkg -x libnspr4_*.deb libs && dpkg -x libnss3_*.deb libs
  export LD_LIBRARY_PATH=$PWD/libs/usr/lib/x86_64-linux-gnu
  export PW_EXE=.../chrome-linux64/chrome      # el que baja playwright
  npm test
  ```

- Regla general para esta página: **si una regla de autor fija `display`
  en un elemento, ese elemento no se puede ocultar con el atributo
  `hidden` a menos que exista una regla de autor que lo respalde.** Ante
  la duda, usar la clase `.hidden` del proyecto, que ya lleva
  `!important`.
